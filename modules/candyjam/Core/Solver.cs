namespace CandyJam.Core
{
    // greedy bot: takes any candy a jar wants, else the colour that is closest to completing
    public static class Solver
    {
        public static bool Solve(LevelData level, int seed = 1)
        {
            var g = new Game(level, seed);
            for (int step = 0; step < level.Candies.Length * 2 && g.State == GameState.Playing; step++)
            {
                var c = Pick(g);
                if (c == null) break;
                g.Tap(c, out _);
            }
            return g.State == GameState.Won;
        }

        static Candy Pick(Game g)
        {
            var free = g.Board.Free();
            var freeBy = new int[Rules.Palette];
            foreach (var c in free) freeBy[c.Color]++;
            var trayBy = new int[Rules.Palette];
            for (int t = 0; t < g.TraySlots; t++) if (g.Tray[t] >= 0) trayBy[g.Tray[t]]++;
            Candy best = null;
            int bestScore = int.MinValue;
            foreach (var c in free)
            {
                int j = g.FindJar(c.Color);
                int s = j >= 0 ? 10000 + g.Jars[j].Count * 100 : trayBy[c.Color] * 100 + freeBy[c.Color] * 10 + c.Layer;
                if (s > bestScore) { bestScore = s; best = c; }
            }
            return best;
        }
    }
}
