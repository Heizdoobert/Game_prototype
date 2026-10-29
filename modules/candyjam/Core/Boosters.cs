using System.Collections.Generic;

namespace CandyJam.Core
{
    public sealed partial class Game
    {
        public BoosterResult UseAddHole()
        {
            if (State != GameState.Playing) return BoosterResult.Unusable;
            if (TraySlots >= Rules.TrayMax) return BoosterResult.LimitReached;
            TraySlots++;
            return BoosterResult.Success;
        }

        // original: tray is cleared, candies are discarded (not returned to the board)
        public BoosterResult UseBroom()
        {
            if (State != GameState.Playing || TrayCount == 0) return BoosterResult.Unusable;
            ClearTray();
            Settle();
            return BoosterResult.Success;
        }

        public BoosterResult UseAddJar()
        {
            if (State != GameState.Playing) return BoosterResult.Unusable;
            int s = -1;
            for (int i = 0; i < Rules.JarSlots; i++) if (!JarUnlocked[i]) { s = i; break; }
            if (s < 0) return BoosterResult.LimitReached;
            if (!AnyJarToSpawn()) return BoosterResult.Unusable;
            JarUnlocked[s] = true;
            Settle();
            return BoosterResult.Success;
        }

        // pulls free candies of the front jar's colour from the board into that jar
        public BoosterResult UseVacuum(out List<Candy> taken)
        {
            taken = new List<Candy>();
            if (State != GameState.Playing) return BoosterResult.Unusable;
            int s = -1;
            for (int i = 0; i < Rules.JarSlots; i++) if (Jars[i] != null) { s = i; break; }
            if (s < 0) return BoosterResult.Unusable;
            var jar = Jars[s];
            var pick = Board.Free().FindAll(c => c.Color == jar.Color);
            pick.Sort((a, b) => b.Layer.CompareTo(a.Layer));
            foreach (var c in pick)
            {
                if (jar.Count >= Rules.JarCapacity) break;
                Board.Remove(c);
                jar.Count++;
                taken.Add(c);
            }
            if (taken.Count == 0) return BoosterResult.Unusable;
            Settle();
            return BoosterResult.Success;
        }

        // swaps an untouched (or empty) unlocked jar for one of the target candy's colour
        public BoosterResult UseRainbow(Candy target)
        {
            if (State != GameState.Playing || target == null || target.Removed) return BoosterResult.Unusable;
            int col = target.Color;
            if (Outside(col) < Rules.JarCapacity) return BoosterResult.Unusable;
            for (int s = 0; s < Rules.JarSlots; s++)
                if (Jars[s] != null && Jars[s].Color == col) return BoosterResult.Unusable;
            for (int s = 0; s < Rules.JarSlots; s++)
            {
                if (!JarUnlocked[s] || (Jars[s] != null && Jars[s].Count > 0)) continue;
                Jars[s] = new JarState { Color = col };
                Settle();
                return BoosterResult.Success;
            }
            return BoosterResult.Unusable;
        }
    }
}
