using CandyJam.Core;

static class SolverTests
{
    public static void Run()
    {
        T.Check(Solver.Solve(TestLevels.Flat(0, 0, 0)), "solver solves a trivial level");
        T.Check(Solver.Solve(TestLevels.Flat(0, 1, 2, 0, 1, 2, 0, 1, 2)), "solver solves a flat three-colour level");
        T.Check(!Solver.Solve(TestLevels.Flat(0, 1, 2, 3, 4, 5)), "solver reports an unsolvable level as unsolvable");

        var trap = Trap();
        T.Check(!OldGreedy(trap), "setup: the old greedy bot loses the trap level");
        T.Check(Solver.Solve(trap), "lookahead solver wins the trap level");
    }

    // A colour-2 lid (layer 1) covers both jar colours (0, 1) and the other two colour-2 candies.
    // Free beside it: three colour-3 and three colour-4 candies. Rank weights {1,0,...} make the jar
    // spawn deterministic (most covered colour first, so jars 0 and 1). Greedy trays the frequent
    // colours 3,3,3,4,4 and loses with a full tray; tapping the lid first frees six jar candies.
    static LevelData Trap()
    {
        var s = new System.Collections.Generic.List<CandySpec> { new CandySpec(0, 0, 1, 2) };
        int[] under = { 0, 0, 0, 1, 1, 1, 2, 2 };
        for (int i = 0; i < under.Length; i++)
        {
            double a = i * System.Math.PI / 4;
            s.Add(new CandySpec(0.5f * (float)System.Math.Cos(a), 0.5f * (float)System.Math.Sin(a), 0, under[i]));
        }
        int[] side = { 3, 3, 3, 4, 4, 4 };
        for (int i = 0; i < side.Length; i++) s.Add(new CandySpec(3f + 1.5f * i, 0, 0, side[i]));
        return new LevelData
        {
            Number = 1,
            Diff = Difficulty.Normal,
            Candies = s.ToArray(),
            Rows = new[] { new ProgressRow(100, new[] { 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }) },
        };
    }

    // the pre-lookahead bot, kept verbatim as the baseline the trap must beat
    static bool OldGreedy(LevelData level)
    {
        var g = new Game(level, 1);
        for (int step = 0; step < level.Candies.Length * 2 && g.State == GameState.Playing; step++)
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
                int sc = j >= 0 ? 10000 + g.Jars[j].Count * 100 : trayBy[c.Color] * 100 + freeBy[c.Color] * 10 + c.Layer;
                if (sc > bestScore) { bestScore = sc; best = c; }
            }
            if (best == null) break;
            g.Tap(best, out _);
        }
        return g.State == GameState.Won;
    }
}
