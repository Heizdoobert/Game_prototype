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

        T.Check(LevelGen.TargetColors(1) == 3 && LevelGen.TargetColors(12) == 5 && LevelGen.TargetColors(54) == 12 && LevelGen.TargetColors(300) == Rules.MaxColors, "colour ramp min(12, 3 + n/6)");

        var sw = new Stopwatch();
        var colours = "";
        int many = 0, skewed = 0;
        for (int n = 1; n <= 60; n++)
        {
            sw.Start();
            var a = LevelGen.Generate(n);
            sw.Stop();
            var b = LevelGen.Generate(n);
            int len = a.Candies.Length;
            T.Check(len % 3 == 0 && len >= 54 && len <= 297, "level " + n + " candy count " + len);
            bool same = len == b.Candies.Length && a.Diff == b.Diff && a.Rows.Length == b.Rows.Length;
            for (int i = 0; same && i < len; i++)
            {
                var p = a.Candies[i];
                var q = b.Candies[i];
                same = p.X == q.X && p.Y == q.Y && p.Layer == q.Layer && p.Color == q.Color;
            }
            T.Check(same, "level " + n + " deterministic");
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
        T.Check(LevelGen.Generate(50).Colors >= 6, "level 50 has at least 6 colours");
        T.Check(many > 0 && skewed * 2 >= many, "colour weights: largest group >= 2x smallest in " + skewed + "/" + many + " levels 20-60 with >= 6 colours");
        T.Check(LevelGen.Generate(1).Candies.Length == 54, "level 1 has 54 candies");
        T.Check(LevelGen.Generate(50).Candies.Length >= 144, "level 50 is big");

        var spot = Stopwatch.StartNew();
        var times = "";
        foreach (int n in new[] { 60, 100, 123, 200 })
        {
            var t0 = spot.Elapsed.TotalSeconds;
            var lv = LevelGen.Generate(n);
            T.Check(lv.Candies.Length % 3 == 0, "level " + n + " candy count multiple of 3");
            T.Check(Solver.Solve(lv), "level " + n + " solvable by the bot");
            times += " L" + n + "=" + (spot.Elapsed.TotalSeconds - t0).ToString("F1") + "s";
        }
        Console.WriteLine("spot checks:" + times);
    }
}
