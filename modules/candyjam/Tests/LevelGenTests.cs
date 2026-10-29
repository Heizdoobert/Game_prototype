using System;
using System.Diagnostics;
using CandyJam.Core;

static class LevelGenTests
{
    public static void Run()
    {
        T.Check(LevelGen.DifficultyOf(1) == Difficulty.Normal, "level 1 normal");
        T.Check(LevelGen.DifficultyOf(8) == Difficulty.Hard, "level 8 hard");
        T.Check(LevelGen.DifficultyOf(15) == Difficulty.VeryHard, "level 15 very hard");
        T.Check(LevelGen.DifficultyOf(30) == Difficulty.VeryHard, "level 30 very hard");
        T.Check(LevelGen.DifficultyOf(120) == Difficulty.VeryHard, "level 120 very hard");
        T.Check(LevelGen.DifficultyOf(24) == Difficulty.Hard, "level 24 hard");

        T.Check(LevelGen.TargetColors(1) == 3 && LevelGen.TargetColors(12) == 5 && LevelGen.TargetColors(54) == 12 && LevelGen.TargetColors(301) == Rules.MaxColors, "Normal colour ramp min(12, 3 + n/6)");
        T.Check(LevelGen.TargetColors(16) == 5 && LevelGen.TargetColors(56) == 5 && LevelGen.TargetColors(200) == 5, "Hard target capped at 5");
        T.Check(LevelGen.TargetColors(15) == 4 && LevelGen.TargetColors(60) == 4 && LevelGen.TargetColors(300) == 4, "VeryHard target capped at 4");

        var sw = new Stopwatch();
        var colours = "";
        int many = 0, skewed = 0;
        for (int n = 1; n <= 60; n++)
        {
            sw.Start();
            var a = LevelGen.Generate(n);
            sw.Stop();
            int len = a.Candies.Length;
            T.Check(len % 3 == 0 && len >= 54 && len <= 297, "level " + n + " candy count " + len);
            T.Check(TestLevels.SameAsShared(n, a), "level " + n + " deterministic");
            var count = new int[Rules.Palette];
            foreach (var c in a.Candies)
            {
                T.Check(c.Color >= 0 && c.Color < Rules.Palette, "level " + n + " colour in palette");
                if (c.Color >= 0 && c.Color < Rules.Palette) count[c.Color]++;
            }
            int distinct = 0, most = 0, least = int.MaxValue;
            foreach (int k in count)
            {
                T.Check(k % 3 == 0, "level " + n + " colour count multiple of 3");
                if (k == 0) continue;
                distinct++;
                most = Math.Max(most, k);
                least = Math.Min(least, k);
            }
            T.Check(distinct >= 3 && distinct <= LevelGen.TargetColors(n), "level " + n + " distinct colours " + distinct);
            T.Check(a.Colors == distinct, "level " + n + " Colors counts distinct colours");
            T.Check(Solver.Solve(a), "level " + n + " solvable by the bot");
            if (n % 10 == 0) colours += " L" + n + "=" + distinct;
            if (n >= 20 && distinct >= 6) { many++; if (most >= 2 * least) skewed++; }
        }
        double mean = sw.Elapsed.TotalMilliseconds / 60;
        Console.WriteLine("levels 1-60: mean generation " + mean.ToString("F0") + " ms, colours" + colours);
        T.Check(mean <= 1500, "mean generation time over levels 1-60 is " + mean.ToString("F0") + " ms (<= 1500)");
        T.Check(TestLevels.Gen(50).Colors >= 6, "level 50 has at least 6 colours");
        T.Check(many > 0 && skewed * 2 >= many, "colour weights: largest group >= 2x smallest in " + skewed + "/" + many + " levels 20-60 with >= 6 colours");
        T.Check(TestLevels.Gen(1).Candies.Length == 54, "level 1 has 54 candies");
        T.Check(TestLevels.Gen(50).Candies.Length >= 144, "level 50 is big");

        // past level 60 the phone generates at level start: every sampled level <= 3 s, mean <= 1 s
        var spot = new Stopwatch();
        var times = "";
        double total = 0;
        int[] sample = { 61, 64, 72, 80, 90, 96, 112, 120, 150, 200 };
        foreach (int n in sample)
        {
            spot.Restart();
            var lv = LevelGen.Generate(n);
            double dt = spot.Elapsed.TotalSeconds;
            total += dt;
            T.Check(TestLevels.SameAsShared(n, lv), "level " + n + " deterministic");
            T.Check(dt <= 3.0, "level " + n + " generates in " + dt.ToString("F1") + " s (<= 3)");
            T.Check(lv.Candies.Length % 3 == 0, "level " + n + " candy count multiple of 3");
            T.Check(Solver.Solve(lv), "level " + n + " solvable by the bot");
            times += " L" + n + "=" + lv.Colors + "c/" + dt.ToString("F1") + "s";
        }
        Console.WriteLine("sampled levels:" + times);
        T.Check(total / sample.Length <= 1.0, "mean generation of sampled levels " + (total / sample.Length).ToString("F2") + " s (<= 1)");
        foreach (int n in new[] { 100, 123 })
            T.Check(Solver.Solve(TestLevels.Gen(n)), "level " + n + " solvable by the bot");
    }
}
