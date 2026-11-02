using System;
using System.Collections.Generic;

namespace CandyJam.Core
{
    public sealed class JarState
    {
        public int Color;
        public int Count;
    }

    public sealed partial class Game
    {
        public readonly LevelData Level;
        public readonly Board Board;
        public readonly JarState[] Jars = new JarState[Rules.JarSlots];
        public readonly bool[] JarUnlocked = new bool[Rules.JarSlots];
        public readonly int[] Tray = new int[Rules.TrayMax];
        public int TraySlots { get; private set; } = Rules.TrayInit;
        public int TrayCount { get; private set; }
        public GameState State { get; private set; } = GameState.Playing;
        public int JarsCompleted { get; private set; }

        readonly int totalCandies;
        uint rngState;

        public Game(LevelData level, int seed = 1)
        {
            Level = level;
            Board = new Board(level.Candies);
            rngState = (uint)seed;
            totalCandies = level.Candies.Length;
            for (int i = 0; i < Rules.TrayMax; i++) Tray[i] = -1;
            for (int i = 0; i < Rules.JarsUnlocked; i++) JarUnlocked[i] = true;
            Settle();
        }

        // LCG so a Game can be cloned with its random future intact
        int Next(int n)
        {
            rngState = rngState * 1664525u + 1013904223u;
            return (int)((rngState >> 8) % (uint)n);
        }

        public bool TrayInDanger { get { return State == GameState.Playing && TrayCount == TraySlots - 1; } }

        Game(Game o)
        {
            Level = o.Level;
            Board = o.Board.Clone();
            for (int i = 0; i < Rules.JarSlots; i++)
            {
                if (o.Jars[i] != null) Jars[i] = new JarState { Color = o.Jars[i].Color, Count = o.Jars[i].Count };
                JarUnlocked[i] = o.JarUnlocked[i];
            }
            System.Array.Copy(o.Tray, Tray, Rules.TrayMax);
            TraySlots = o.TraySlots;
            TrayCount = o.TrayCount;
            State = o.State;
            JarsCompleted = o.JarsCompleted;
            totalCandies = o.totalCandies;
            rngState = o.rngState;
        }

        // Level is shared: immutable by convention
        public Game Clone() { return new Game(this); }

        public int FindJar(int color)
        {
            for (int s = 0; s < Rules.JarSlots; s++)
                if (Jars[s] != null && Jars[s].Color == color && Jars[s].Count < Rules.JarCapacity) return s;
            return -1;
        }

        public TapResult Tap(Candy c, out int dest)
        {
            dest = -1;
            if (State != GameState.Playing || !Board.IsFree(c)) return TapResult.Rejected;
            return TakeCandy(c, out dest);
        }

        // routes a candy to its jar, else the tray; Rejected when neither has room
        TapResult TakeCandy(Candy c, out int dest)
        {
            dest = -1;
            int j = FindJar(c.Color);
            int t = j >= 0 ? -1 : FirstEmptyTray();
            if (j < 0 && t < 0) return TapResult.Rejected;
            Board.Remove(c);
            TapResult r;
            if (j >= 0) { Jars[j].Count++; dest = j; r = TapResult.ToJar; }
            else { Tray[t] = c.Color; TrayCount++; dest = t; r = TapResult.ToTray; }
            Settle();
            return r;
        }

        public bool Revive()
        {
            if (State != GameState.Lost) return false;
            ClearTray();
            State = GameState.Playing;
            Settle();
            return true;
        }

        int FirstEmptyTray()
        {
            for (int t = 0; t < TraySlots; t++) if (Tray[t] < 0) return t;
            return -1;
        }

        void ClearTray()
        {
            for (int t = 0; t < Rules.TrayMax; t++) Tray[t] = -1;
            TrayCount = 0;
        }

        // candies of this colour not yet in a jar: still on the board or waiting in the tray
        int Outside(int color)
        {
            int n = 0;
            foreach (var c in Board.Candies) if (!c.Removed && c.Color == color) n++;
            for (int t = 0; t < Rules.TrayMax; t++) if (Tray[t] == color) n++;
            return n;
        }

        bool CanSpawn(int color)
        {
            foreach (var j in Jars) if (j != null && j.Color == color) return false;
            return Outside(color) >= Rules.JarCapacity;
        }

        bool AnyJarToSpawn()
        {
            for (int c = 0; c < Rules.Palette; c++) if (CanSpawn(c)) return true;
            return false;
        }

        // close full jars, spawn replacements, move tray candies into matching jars; repeat until stable
        void Settle()
        {
            bool changed;
            do
            {
                changed = false;
                for (int s = 0; s < Rules.JarSlots; s++)
                    if (Jars[s] != null && Jars[s].Count >= Rules.JarCapacity) { Jars[s] = null; JarsCompleted++; changed = true; }
                // release dead jars: not enough candies left outside to ever fill them
                for (int s = 0; s < Rules.JarSlots; s++)
                    if (Jars[s] != null && Jars[s].Count + Outside(Jars[s].Color) < Rules.JarCapacity) { Jars[s] = null; changed = true; }
                if (SpawnJars()) changed = true;
                for (int t = 0; t < Rules.TrayMax; t++)
                {
                    if (Tray[t] < 0) continue;
                    int j = FindJar(Tray[t]);
                    if (j < 0) continue;
                    Jars[j].Count++; Tray[t] = -1; TrayCount--; changed = true;
                }
            } while (changed);
            CheckEnd();
        }

        bool SpawnJars()
        {
            bool any = false;
            for (int s = 0; s < Rules.JarSlots; s++)
            {
                if (!JarUnlocked[s] || Jars[s] != null) continue;
                int col = PickJarColor();
                if (col < 0) break;
                Jars[s] = new JarState { Color = col };
                any = true;
            }
            return any;
        }

        // weighted random over colours that still can spawn (not in a jar slot, >= 3 candies outside jars);
        // candidates ranked hardest first (most blocked candies left), weight by progress row
        int PickJarColor()
        {
            var cand = new List<int>();
            for (int i = 0; i < Rules.Palette; i++) if (CanSpawn(i)) cand.Add(i);
            if (cand.Count == 0) return -1;
            var rem = Board.CountByColor(Board.Candies);
            var free = Board.CountByColor(Board.Free());
            cand.Sort((a, b) =>
            {
                int d = (rem[b] - free[b]) - (rem[a] - free[a]);
                return d != 0 ? d : a.CompareTo(b);
            });
            int pct = totalCandies == 0 ? 100 : 100 * (totalCandies - Board.Remaining) / totalCandies;
            var row = Level.Rows[Level.Rows.Length - 1];
            foreach (var r in Level.Rows) if (pct <= r.UpTo) { row = r; break; }
            var w = new int[cand.Count];
            int total = 0;
            for (int i = 0; i < w.Length; i++)
            {
                w[i] = i < row.RankWeights.Length ? row.RankWeights[i] : 1;
                total += w[i];
            }
            if (total <= 0) return cand[Next(cand.Count)];
            int roll = Next(total);
            for (int i = 0; i < w.Length; i++)
            {
                if (roll < w[i]) return cand[i];
                roll -= w[i];
            }
            return cand[0];
        }

        void CheckEnd()
        {
            if (State != GameState.Playing) return;
            if (Board.Remaining == 0) { State = GameState.Won; return; }
            if (TrayCount < TraySlots) return;
            foreach (var c in Board.Free()) if (FindJar(c.Color) >= 0) return;
            State = GameState.Lost;
        }
    }
}
