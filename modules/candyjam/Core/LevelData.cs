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
    }
}
