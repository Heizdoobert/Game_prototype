using System;
using System.Collections.Generic;

namespace CandyJam.Core
{
    // lookahead bot (no boosters): scores the best few taps two moves deep on cloned games, plays the best first
    // move, repeats; plain greedy once the node budget is spent. Clones share the LCG future, so the bot foresees
    // jar spawns a player cannot: a level it solves is necessary, not sufficient, for a human to solve it.
    // [tuned] beam, macro-step and backtracking variants solved about as many generated levels at 1.1-2x the cost
    public static class Solver
    {
        const int Depth = 2, Branch = 6, NodeBudget = 20000; // [tuned]

        public static bool Solve(LevelData level, int seed = 1) { return Play(level, seed, true).Won; }

        public readonly struct Stats
        {
            public readonly bool Won;
            public readonly int PeakTray; // most candies waiting in the tray after any tap (a lost game peaks at the tray size)
            public Stats(bool won, int peak) { Won = won; PeakTray = peak; }
        }

        // one full game by the bot; lookahead=false is the plain greedy pick, with no foresight of the jar spawns
        public static Stats Play(LevelData level, int seed, bool lookahead)
        {
            var g = new Game(level, seed);
            int budget = NodeBudget, peak = 0;
            while (g.State == GameState.Playing)
            {
                var moves = Candidates(g);
                if (moves.Count == 0) break;
                var pick = moves[0];
                if (lookahead && moves.Count > 1 && budget > 0)
                {
                    double best = double.MinValue;
                    foreach (var m in moves)
                    {
                        double v = Search(Child(g, m, ref budget), Depth - 1, ref budget);
                        if (v > best) { best = v; pick = m; }
                    }
                }
                g.Tap(g.Board.Candies[pick.Id], out _);
                if (g.TrayCount > peak) peak = g.TrayCount;
            }
            return new Stats(g.State == GameState.Won, peak);
        }

        static Game Child(Game g, Candy m, ref int budget)
        {
            budget--;
            var k = g.Clone();
            k.Tap(k.Board.Candies[m.Id], out _);
            return k;
        }

        static double Search(Game g, int depth, ref int budget)
        {
            if (g.State != GameState.Playing || depth <= 0 || budget <= 0) return Eval(g);
            double best = double.MinValue;
            foreach (var m in Candidates(g)) best = Math.Max(best, Search(Child(g, m, ref budget), depth - 1, ref budget));
            return best == double.MinValue ? Eval(g) : best;
        }

        // leaf score: jars closed, tray room (a nearly full tray is close to a loss), candies the open jars can take now
        static double Eval(Game g)
        {
            if (g.State == GameState.Won) return 1e9;
            if (g.State == GameState.Lost) return -1e9;
            var free = g.Board.Free();
            var freeBy = Board.CountByColor(free);
            int match = 0;
            foreach (var j in g.Jars) if (j != null) match += Math.Min(Rules.JarCapacity - j.Count, freeBy[j.Color]);
            double s = 1000.0 * g.JarsCompleted - 200.0 * g.TrayCount + 50.0 * match + free.Count;
            if (g.TrayCount >= g.TraySlots - 1) s -= 2000;
            return s;
        }

        // legal taps ordered by the old greedy score (jar match first, closest jar first; else colours already in the
        // tray, then common on the surface, then higher layers), one per (colour, layer); [0] is the greedy pick
        static List<Candy> Candidates(Game g)
        {
            var free = g.Board.Free();
            var freeBy = Board.CountByColor(free);
            var trayBy = new int[Rules.Palette];
            for (int t = 0; t < g.TraySlots; t++) if (g.Tray[t] >= 0) trayBy[g.Tray[t]]++;
            bool trayFull = g.TrayCount >= g.TraySlots;
            var scored = new List<(int S, Candy C)>();
            foreach (var c in free)
            {
                int j = g.FindJar(c.Color);
                if (j < 0 && trayFull) continue;
                scored.Add((j >= 0 ? 10000 + g.Jars[j].Count * 100 : trayBy[c.Color] * 100 + freeBy[c.Color] * 10 + c.Layer, c));
            }
            scored.Sort((a, b) => a.S != b.S ? b.S - a.S : a.C.Id - b.C.Id);
            var seen = new HashSet<int>();
            var r = new List<Candy>();
            foreach (var x in scored)
            {
                if (r.Count >= Branch) break;
                if (seen.Add(x.C.Color * 16 + x.C.Layer)) r.Add(x.C);
            }
            return r;
        }
    }
}
