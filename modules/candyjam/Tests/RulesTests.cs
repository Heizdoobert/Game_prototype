using CandyJam.Core;

static class RulesTests
{
    public static void Run()
    {
        Constants();
        Needle();
        TrayDanger();
        CloneIndependence();
        CloneSameFuture();
    }

    static void Constants()
    {
        T.Check(Rules.BoosterPrice.Length == 6 && Rules.BoosterPrice[(int)BoosterKind.Needle] == 500, "needle price 500 at index 5");
        T.Check(Rules.UnlockLevel.Length == 6 && Rules.UnlockLevel[(int)BoosterKind.Needle] == 12 && Rules.UnlockLevel[0] == 2, "unlock levels by booster index");
        T.Check(Rules.FreeOnUnlock == 3, "free grant 3");
    }

    // candy 0 (layer 0) sits under candy 1 (layer 1); candy 2 is far away
    static LevelData Covered(params int[] colors)
    {
        var specs = new CandySpec[colors.Length];
        for (int i = 0; i < colors.Length; i++) specs[i] = new CandySpec(i == 2 ? 9f : 0f, 0, i == 1 ? 1 : 0, colors[i]);
        return new LevelData { Number = 1, Diff = Difficulty.Normal, Candies = specs, Rows = new[] { new ProgressRow(100, new[] { 1 }) } };
    }

    static void Needle()
    {
        var g = new Game(Covered(0, 0, 0));
        var under = g.Board.Candies[0];
        T.Check(!g.Board.IsFree(under), "candy 0 is covered");
        T.Check(g.UseNeedle(under, out var r, out int dest) == BoosterResult.Success && r == TapResult.ToJar && dest == 0, "needle takes a covered candy into the open jar");
        T.Check(under.Removed && g.Board.Remaining == 2, "needle removed it from the board");
        T.Check(g.UseNeedle(under, out _, out _) == BoosterResult.Unusable, "removed candy is unusable");
        T.Check(g.UseNeedle(null, out _, out _) == BoosterResult.Unusable, "null target is unusable");

        // two jars take two of the four colours; a covered candy of another colour goes to the tray
        var g3 = new Game(TwoLayerColours());
        var jarColors = new System.Collections.Generic.HashSet<int> { g3.Jars[0].Color, g3.Jars[1].Color };
        var waiting = g3.Board.Candies.Find(c => !jarColors.Contains(c.Color) && !g3.Board.IsFree(c));
        T.Check(waiting != null, "a covered candy without a jar exists");
        T.Check(g3.UseNeedle(waiting, out r, out dest) == BoosterResult.Success && r == TapResult.ToTray && g3.TrayCount == 1, "needle sends a jarless candy to the tray");

        // full tray, no matching jar: unusable and the candy stays (colour 0 jar keeps the game alive)
        var g4 = new Game(TestLevels.Flat(1, 2, 3, 4, 5, 6, 0, 0, 0));
        for (int i = 0; i < 5; i++) g4.Tap(g4.Board.Candies[i], out _);
        T.Check(g4.TrayCount == g4.TraySlots && g4.State == GameState.Playing, "tray is full and the game is not over");
        var rest = g4.Board.Candies[5];
        T.Check(g4.UseNeedle(rest, out _, out _) == BoosterResult.Unusable, "needle unusable with a full tray and no jar");
        T.Check(!rest.Removed && g4.Board.Remaining == 4, "candy stays on the board");

        // eight single colours: no jars, tray fills, game is lost
        var lost = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5, 6, 7));
        for (int i = 0; i < 5; i++) lost.Tap(lost.Board.Candies[i], out _);
        T.Check(lost.State == GameState.Lost, "setup: game lost");
        T.Check(lost.UseNeedle(lost.Board.Candies[5], out _, out _) == BoosterResult.Unusable, "needle unusable when not playing");
    }

    // colours 0..3 as covered pairs: a candy on layer 1 sits on top of the layer 0 one
    static LevelData TwoLayerColours()
    {
        var specs = new CandySpec[12];
        for (int i = 0; i < 12; i++) specs[i] = new CandySpec((i % 6) * 3f, (i / 6) * 0f, i / 6, i % 4);
        return new LevelData { Number = 1, Diff = Difficulty.Normal, Candies = specs, Rows = new[] { new ProgressRow(100, new[] { 1 }) } };
    }

    static void TrayDanger()
    {
        var g = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5, 6, 7, 8, 9));
        T.Check(!g.TrayInDanger, "empty tray is not in danger");
        // fill only with candies that have no jar so they stay in the tray
        int n = 0;
        foreach (var c in g.Board.Candies)
        {
            if (g.FindJar(c.Color) >= 0 || g.TrayCount >= g.TraySlots) continue;
            g.Tap(c, out _);
            n++;
            bool expect = g.TrayCount == g.TraySlots - 1;
            T.Check(g.TrayInDanger == expect, "danger flag at tray count " + g.TrayCount);
        }
        T.Check(n > 0, "tapped something");
        T.Check(g.TrayCount == g.TraySlots || g.State != GameState.Playing, "tray reached capacity or the game ended");
        T.Check(!g.TrayInDanger, "full tray is not 'in danger' (lost or about to be)");

        var h = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5, 6, 7, 8, 9));
        for (int i = 0; i < 20 && h.TrayCount < 3; i++)
            foreach (var c in h.Board.Candies) if (!c.Removed && h.FindJar(c.Color) < 0 && h.TrayCount < 3) { h.Tap(c, out _); break; }
        T.Check(h.TrayCount == 3 && !h.TrayInDanger, "3 of 5 is safe");
        h.UseAddHole();
        T.Check(h.TraySlots == 6 && !h.TrayInDanger, "3 of 6 is safe");
        foreach (var c in h.Board.Candies) if (!c.Removed && h.FindJar(c.Color) < 0 && h.TrayCount < 5) { h.Tap(c, out _); }
        T.Check(h.TrayCount == 5 && h.TrayInDanger, "add hole moves the threshold: 5 of 6 is danger");

        var w = new Game(TestLevels.Flat(0, 0, 0));
        foreach (var c in w.Board.Candies) w.Tap(c, out _);
        T.Check(w.State == GameState.Won && !w.TrayInDanger, "won is never in danger");
    }

    static void CloneIndependence()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        var k = g.Clone();
        T.Check(!ReferenceEquals(g.Board, k.Board) && !ReferenceEquals(g.Board.Candies[0], k.Board.Candies[0]), "clone has its own board");
        T.Check(!ReferenceEquals(g.Tray, k.Tray) && !ReferenceEquals(g.Jars, k.Jars), "clone has its own tray and jars");
        k.Tap(k.Board.Candies[0], out _);
        T.Check(g.Board.Remaining == 9 && !g.Board.Candies[0].Removed, "mutating the clone leaves the original untouched");
        T.Check(k.Board.Remaining == 8 && k.Board.Candies[0].Removed, "clone changed");
    }

    static string Snap(Game g)
    {
        var s = new System.Text.StringBuilder();
        s.Append(g.State).Append('|').Append(g.JarsCompleted).Append('|').Append(g.TrayCount).Append('|').Append(g.TraySlots).Append('|');
        foreach (int t in g.Tray) s.Append(t).Append(',');
        s.Append('|');
        foreach (var j in g.Jars) s.Append(j == null ? "-" : j.Color + ":" + j.Count).Append(',');
        return s.ToString();
    }

    static void CloneSameFuture()
    {
        var level = LevelGen.Generate(7);
        var g = new Game(level, 5);
        for (int i = 0; i < 6; i++) { var f = g.Board.Free(); if (f.Count == 0 || g.State != GameState.Playing) break; g.Tap(f[0], out _); }
        var k = g.Clone();
        T.Check(Snap(g) == Snap(k), "clone starts identical");
        for (int i = 0; i < 80 && g.State == GameState.Playing; i++)
        {
            var fg = g.Board.Free();
            var fk = k.Board.Free();
            if (fg.Count == 0) break;
            T.Check(fg.Count == fk.Count, "same free count at step " + i);
            int pick = (i * 7) % fg.Count;
            g.Tap(fg[pick], out int d1);
            k.Tap(fk[pick], out int d2);
            T.Check(d1 == d2 && Snap(g) == Snap(k), "same state after step " + i);
        }
        T.Check(Snap(g) == Snap(k), "clone and original stay identical over a tap sequence");
    }
}
