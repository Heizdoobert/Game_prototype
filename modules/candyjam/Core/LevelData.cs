namespace CandyJam.Core
{
    public sealed class ProgressRow
    {
        public readonly int UpTo;
        public readonly int[] RankWeights;
        public ProgressRow(int upTo, int[] rankWeights) { UpTo = upTo; RankWeights = rankWeights; }
    }

    public sealed class LevelData
    {
        public int Number;
        public Difficulty Diff;
        public CandySpec[] Candies;
        public ProgressRow[] Rows;

        public int Colors
        {
            get
            {
                var seen = new bool[Rules.Palette];
                int n = 0;
                foreach (var c in Candies) if (!seen[c.Color]) { seen[c.Color] = true; n++; }
                return n;
            }
        }
    }
}
