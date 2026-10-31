using System;
using CandyJam.Core;

static class LevelMetricTests
{
    public static void Run()
    {
        var easy = LevelMetric.Of(TestLevels.Flat(0, 0, 0));
        T.Check(easy.GreedyLoss == 0 && easy.LookLoss == 0 && easy.LookPeak == 0 && easy.Score == 0, "one jar's worth of candies scores 0");

        var dead = LevelMetric.Of(TestLevels.Flat(0, 1, 2, 3, 4, 5));
        T.Check(dead.GreedyLoss == 1 && dead.LookLoss == 1 && dead.LookPeak == Rules.TrayInit && Math.Abs(dead.Score - 100) < 1e-9,
            "a level no bot can win scores 100 (" + dead.Score.ToString("F1") + ")");

        // same level twice: same numbers
        var lv = TestLevels.Gen(30);
        T.Check(LevelMetric.Of(lv).Score == LevelMetric.Of(lv).Score, "metric is deterministic");

        // the early ramp must read as easier than a many-colour level, or the metric says nothing
        var early = LevelMetric.Of(TestLevels.Gen(5)).Score;
        var late = LevelMetric.Of(TestLevels.Gen(50)).Score;
        Console.WriteLine("difficulty score: L5=" + early.ToString("F0") + " L50=" + late.ToString("F0"));
        T.Check(early < 30, "level 5 score " + early.ToString("F0") + " < 30");
        T.Check(late > early + 20, "level 50 score " + late.ToString("F0") + " > level 5 + 20");
    }
}
