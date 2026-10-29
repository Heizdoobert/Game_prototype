using Proto.Shell;

static class ProfileUnlockTests
{
    public static void Run()
    {
        var unlock = new[] { 1, 2, 5, 2 };
        var free = new[] { 0, 3, 3, 3 };

        var p = new Profile { Level = 2, Boosters = new[] { 1, 1, 1, 1 } };
        var got = p.GrantUnlocks(unlock, free);
        T.Check(got.Count == 2 && got[0] == 1 && got[1] == 3, "grants exactly the boosters unlocking at this level");
        T.Check(p.Boosters[0] == 1 && p.Boosters[1] == 4 && p.Boosters[2] == 1 && p.Boosters[3] == 4, "adds the free counts only to those");

        p.Level = 3;
        T.Check(p.GrantUnlocks(unlock, free).Count == 0 && p.Boosters[1] == 4, "nothing at a level with no unlock");

        var one = new Profile { Level = 1, Boosters = new[] { 0, 0, 0, 0 } };
        got = one.GrantUnlocks(unlock, free);
        T.Check(got.Count == 1 && got[0] == 0 && one.Boosters[0] == 0, "unlock level 1 matches level 1 but grants its free count (0)");

        var q = new Profile { Level = 5, Boosters = new[] { 0, 0, 0 } };
        got = q.GrantUnlocks(new[] { 5 }, new[] { 3 });
        T.Check(got.Count == 1 && q.Boosters[0] == 3, "short arrays: first entry still works");
        var r = new Profile { Level = 5, Boosters = new[] { 0, 0, 0 } };
        got = r.GrantUnlocks(new[] { 5, 5, 5 }, new[] { 3 });
        T.Check(got.Count == 1 && r.Boosters[1] == 0 && r.Boosters[2] == 0, "free array shorter than unlock: no exception, no grant for missing entries");
        var s = new Profile { Level = 5, Boosters = new[] { 0 } };
        got = s.GrantUnlocks(new[] { 5, 5 }, new[] { 3, 3 });
        T.Check(got.Count == 1 && s.Boosters[0] == 3, "arrays longer than Boosters: extra entries ignored");

        var pad = new Profile { Boosters = null };
        pad.PadBoosters(new[] { 3, 0, 3 });
        T.Check(pad.Boosters.Length == 3 && pad.Boosters[0] == 3 && pad.Boosters[1] == 0 && pad.Boosters[2] == 3, "null inventory padded with the start counts");
        pad.Boosters = new[] { 7, 9 };
        pad.PadBoosters(new[] { 3, 0, 3 });
        T.Check(pad.Boosters.Length == 3 && pad.Boosters[0] == 7 && pad.Boosters[1] == 9 && pad.Boosters[2] == 3, "shorter inventory keeps stored values, pads only missing slots");
        pad.Boosters = new[] { 1, 2, 3, 4 };
        pad.PadBoosters(new[] { 3, 0, 3 });
        T.Check(pad.Boosters.Length == 3 && pad.Boosters[2] == 3 && pad.Boosters[0] == 1, "longer inventory truncated");
    }
}
