using System;
using System.Linq;
using CandyJam.Core;

static class GateTests
{
    static bool Throws(Action a) { try { a(); return false; } catch (FormatException) { return true; } }

    public static void Run()
    {
        var keys = PackKeys.All().ToList();
        T.Check(keys.Count == 4 + Rules.Palette + Enum.GetValues(typeof(Sfx)).Length, "pack key count " + keys.Count);
        T.Check(keys.Distinct().Count() == keys.Count, "pack keys are unique");
        T.Check(keys.Contains("candy_0") && keys.Contains("candy_11") && !keys.Contains("candy_12"), "one candy key per palette colour");
        T.Check(PackKeys.SfxName(Sfx.Win) == "sfx_win" && keys.Contains("sfx_booster"), "sfx names");

        var gen = new GeneratedLevels().Get(3);
        T.Check(TestLevels.SameAsShared(3, gen), "GeneratedLevels is LevelGen");

        const string text = "# tiny\ndiff Hard\n0 0 0 1\n3 0 0 1\n6 0 0 1\n0 3 0 2\n3 3 0 2\n6 3 0 2\n";
        var lv = AuthoredLevels.Parse(7, text);
        T.Check(lv.Number == 7 && lv.Diff == Difficulty.Hard && lv.Candies.Length == 6 && lv.Colors == 2, "authored level parsed");
        T.Check(lv.Candies[3].Y == 3f && lv.Candies[3].Color == 2, "authored candy fields");
        T.Check(lv.Rows.Length == LevelGen.RowsFor(Difficulty.Hard).Length && lv.Rows[0].UpTo == LevelGen.RowsFor(Difficulty.Hard)[0].UpTo, "authored rows follow the tier");
        T.Check(Solver.Solve(lv), "an authored flat level plays");

        var src = new AuthoredLevels(n => n == 7 ? text : null, new GeneratedLevels());
        T.Check(src.Get(7).Diff == Difficulty.Hard, "authored level wins over the fallback");
        T.Check(TestLevels.SameAsShared(3, src.Get(3)), "missing file falls back to the generator");

        T.Check(Throws(() => AuthoredLevels.Parse(1, "0 0 0 1\n3 0 0 1\n")), "colour count not a multiple of 3 is refused");
        T.Check(Throws(() => AuthoredLevels.Parse(1, "0 0 0 99\n")), "colour out of palette is refused");
        T.Check(Throws(() => AuthoredLevels.Parse(1, "0 0 x 1\n")), "garbled line is refused");
        T.Check(Throws(() => AuthoredLevels.Parse(1, "diff Nope\n")), "unknown difficulty is refused");
        T.Check(Throws(() => AuthoredLevels.Parse(1, "# nothing\n")), "empty level is refused");
        T.Check(Throws(() => AuthoredLevels.Parse(1, "0 0 -1 1\n")), "negative layer is refused");
    }
}
