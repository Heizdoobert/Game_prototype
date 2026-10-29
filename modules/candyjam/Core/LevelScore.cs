namespace CandyJam.Core
{
    public static class LevelScore
    {
        // difficulty proxy: 5 per candy already covered at the start [tuned]
        public static int Of(LevelData level)
        {
            var b = new Board(level.Candies);
            int s = 0;
            foreach (var c in b.Candies) if (!b.IsFree(c)) s += 5;
            return s;
        }
    }
}
