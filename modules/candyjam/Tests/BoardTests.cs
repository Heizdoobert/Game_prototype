using CandyJam.Core;

static class BoardTests
{
    public static void Run()
    {
        var b = new Board(new[]
        {
            new CandySpec(0, 0, 0, 1),    // lower, covered by the next one
            new CandySpec(0.3f, 0, 1, 2), // upper, overlaps (dist 0.3 < 0.9)
            new CandySpec(5, 5, 0, 3),    // far away, free
        });
        var low = b.Candies[0]; var up = b.Candies[1]; var far = b.Candies[2];
        T.Check(!b.IsFree(low), "lower candy under upper is blocked");
        T.Check(b.IsFree(up), "upper candy is free");
        T.Check(b.IsFree(far), "far candy is free");
        T.Check(b.Free().Count == 2, "two free candies");
        b.Remove(up);
        T.Check(b.IsFree(low), "lower becomes free after upper removed");
        T.Check(b.Remaining == 2, "remaining counts removals");
        T.Check(!b.IsFree(up), "removed candy is not free");
        b.Remove(up);
        T.Check(b.Remaining == 2, "double remove is a no-op");
    }
}
