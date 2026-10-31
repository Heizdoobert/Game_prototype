using System;

namespace CandyJam.Core
{
    // measured difficulty: how often bots lose the level over several jar-spawn futures, and how full the tray gets.
    // LevelGen validates one seed with a bot that foresees the spawns; a player does not, so seeds other than the
    // validated one are the fair test. Greedy = weak bot, lookahead = strong bot. Score is 0 (never loses, empty tray)
    // to 100 (every bot loses every seed). [tuned] weights; offline tool, a level costs about a second.
    public sealed class LevelMetric
    {
        public const int GreedySeeds = 12, LookSeeds = 6;

        public readonly double GreedyLoss, LookLoss; // share of seeds lost, 0..1
        public readonly double LookPeak;             // mean most-candies-waiting in the tray, lookahead bot

        LevelMetric(double greedyLoss, double lookLoss, double lookPeak)
        {
            GreedyLoss = greedyLoss; LookLoss = lookLoss; LookPeak = lookPeak;
        }

        public double Score { get { return 100.0 * (GreedyLoss + LookLoss + LookPeak / Rules.TrayInit) / 3.0; } }

        public static LevelMetric Of(LevelData level)
        {
            int gLost = 0, lLost = 0, peak = 0;
            for (int s = 1; s <= GreedySeeds; s++) if (!Solver.Play(level, s, false).Won) gLost++;
            for (int s = 1; s <= LookSeeds; s++)
            {
                var r = Solver.Play(level, s, true);
                if (!r.Won) lLost++;
                peak += r.PeakTray;
            }
            return new LevelMetric((double)gLost / GreedySeeds, (double)lLost / LookSeeds, (double)peak / LookSeeds);
        }
    }
}
