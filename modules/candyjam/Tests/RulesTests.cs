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
        string s0 = Snap(g);
        T.Check(g.UseNeedle(under, out _, out _) == BoosterResult.Unusable && Snap(g) == s0 && g.Board.Remaining == 2, "removed candy is unusable, nothing changes");
        T.Check(g.UseNeedle(null, out _, out _) == BoosterResult.Unusable && Snap(g) == s0, "null target is unusable, nothing changes");

        // two jars take two of the four colours; a covered candy of another colour goes to the tray
        var g3 = new Game(TwoLayerColours());
        var jarColors = new System.Collections.Generic.HashSet<int> { g3.Jars[0].Color, g3.Jars[1].Color };
        var waiting = g3.Board.Candies.Find(c => !jarColors.Contains(c.Color) && !g3.Board.IsFree(c));
        T.Check(waiting != null, "a covered candy without a jar exists");
        T.Check(g3.UseNeedle(waiting, out r, out dest) == BoosterResult.Success && r == TapResult.ToTray && g3.TrayCount == 1, "needle sends a jarless candy to the tray");

        // full tray, no matching jar: unusable and the candy stays (the colour 0 jar keeps the game alive)
        var g4 = new Game(TestLevels.Flat(1, 2, 3, 4, 5, 6, 0, 0, 0));
        for (int i = 0; i < 5; i++) g4.Tap(g4.Board.Candies[i], out _);
        T.Check(g4.TrayCount == g4.TraySlots && g4.State == GameState.Playing, "tray is full and the game is not over");
        var rest = g4.Board.Candies[5];
        string s4 = Snap(g4);
        T.Check(g4.UseNeedle(rest, out _, out _) == BoosterResult.Unusable, "needle unusable with a full tray and no jar");
        T.Check(!rest.Removed && g4.Board.Remaining == 4 && Snap(g4) == s4, "candy stays, tray and jars unchanged");

        // Lost game where the target's colour has an open jar: only the State guard can refuse
        var lost = LostGame();
        T.Check(lost.State == GameState.Lost && lost.Jars[0] != null && lost.Jars[0].Color == 0, "setup: lost with an open colour 0 jar");
        var hidden = lost.Board.Candies[0];
        string sl = Snap(lost);
        T.Check(lost.UseNeedle(hidden, out _, out _) == BoosterResult.Unusable, "needle unusable when not playing");
        T.Check(!hidden.Removed && lost.Board.Remaining == 4 && Snap(lost) == sl, "lost game unchanged");
    }

    // three colour 0 candies at layer 0 under six single-colour candies at layer 1; five singles fill the tray,
    // the sixth still covers colour 0, so no free candy matches the colour 0 jar: Lost
    static Game LostGame()
    {
        var specs = new CandySpec[9];
        for (int i = 0; i < 3; i++) specs[i] = new CandySpec(i * 0.1f, 0, 0, 0);
        for (int i = 0; i < 6; i++) specs[3 + i] = new CandySpec(0, 0, 1, 1 + i);
        var lvl = new LevelData { Number = 1, Diff = Difficulty.Normal, Candies = specs, Rows = new[] { new ProgressRow(100, new[] { 1 }) } };
        var g = new Game(lvl);
        for (int i = 3; i < 8; i++) g.Tap(g.Board.Candies[i], out _);
        return g;
    }

    // colours i%4; candy i+6 (layer 1) sits on top of candy i (layer 0), so candies 0..5 start covered
    static LevelData TwoLayerColours()
    {
        var specs = new CandySpec[12];
        for (int i = 0; i < 12; i++) specs[i] = new CandySpec((i % 6) * 3f, 0, i / 6, i % 4);
        return new LevelData { Number = 1, Diff = Difficulty.Normal, Candies = specs, Rows = new[] { new ProgressRow(100, new[] { 1 }) } };
    }

    static void TrayDanger()
    {
        // six single colours plus three of colour 0: the colour 0 jar keeps the game Playing with a full tray
        var g = new Game(TestLevels.Flat(1, 2, 3, 4, 5, 6, 0, 0, 0));
        T.Check(!g.TrayInDanger, "empty tray is safe");
        for (int i = 0; i < 3; i++) g.Tap(g.Board.Candies[i], out _);
        T.Check(g.TrayCount == 3 && !g.TrayInDanger, "3 of 5 is safe");
        g.Tap(g.Board.Candies[3], out _);
        T.Check(g.TrayCount == 4 && g.State == GameState.Playing && g.TrayInDanger == true, "4 of 5 is danger");
        g.Tap(g.Board.Candies[4], out _);
        T.Check(g.TrayCount == 5 && g.State == GameState.Playing, "setup: full tray, still playing (free candy matches the jar)");
        T.Check(g.TrayInDanger == false, "5 of 5 is not danger");

        var h = new Game(TestLevels.Flat(1, 2, 3, 4, 5, 6, 0, 0, 0));
        for (int i = 0; i < 3; i++) h.Tap(h.Board.Candies[i], out _);
        h.UseAddHole();
        T.Check(h.TraySlots == 6 && !h.TrayInDanger, "3 of 6 is safe");
        h.Tap(h.Board.Candies[3], out _);
        T.Check(h.TrayCount == 4 && !h.TrayInDanger, "4 of 6 is safe after add hole");
        h.Tap(h.Board.Candies[4], out _);
        T.Check(h.TrayCount == 5 && h.TrayInDanger == true, "add hole moves the threshold: 5 of 6 is danger");

        var lost = LostGame();
        T.Check(lost.State == GameState.Lost && !lost.TrayInDanger, "lost is never in danger");
        var w = new Game(TestLevels.Flat(0, 0, 0));
        foreach (var c in w.Board.Candies) w.Tap(c, out _);
        T.Check(w.State == GameState.Won && !w.TrayInDanger, "won is never in danger");
    }

    static void CloneIndependence()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        int c0 = g.Jars[0].Color;
        g.Tap(g.Board.Candies.Find(c => c.Color == c0), out _);
        T.Check(g.Jars[0].Count == 1, "setup: jar 0 started on the original");
        var k = g.Clone();
        T.Check(k.Jars[0].Color == c0 && k.Jars[0].Count == 1, "clone sees the started jar");

        k.Tap(k.Board.Candies.Find(c => !c.Removed && c.Color == c0), out int d);
        T.Check(d == 0 && k.Jars[0].Count == 2, "clone jar count incremented");
        T.Check(g.Jars[0].Count == 1, "original jar count unchanged (JarState not shared)");

        var jarColors = new System.Collections.Generic.HashSet<int> { g.Jars[0].Color, g.Jars[1].Color };
        var other = k.Board.Candies.Find(c => !jarColors.Contains(c.Color));
        T.Check(k.Tap(other, out _) == TapResult.ToTray && k.Tray[0] == other.Color && k.TrayCount == 1, "clone tray took a candy");
        T.Check(g.Tray[0] == -1 && g.TrayCount == 0, "original tray untouched");
        T.Check(g.Board.Remaining == 8 && k.Board.Remaining == 6, "board counts diverge independently");
        T.Check(!g.Board.Candies[other.Id].Removed, "original candy not removed");
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
