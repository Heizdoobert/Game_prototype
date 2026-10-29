using System.Collections.Generic;
using CandyJam.Core;

static class TestLevels
{
    // all candies on layer 0, spread far apart so every candy is free
    public static LevelData Flat(params int[] colors)
    {
        var specs = new CandySpec[colors.Length];
        for (int i = 0; i < colors.Length; i++) specs[i] = new CandySpec(i * 3f, 0, 0, colors[i]);
        return new LevelData
        {
            Number = 1,
            Diff = Difficulty.Normal,
            Candies = specs,
            Rows = new[] { new ProgressRow(100, new[] { 1 }) },
        };
    }
}

static class GameTests
{
    public static void Run()
    {
        OneColorWins();
        TrayRoutingAndLose();
        JarCompletionAndSpawn();
        ReviveAfterLose();
        BlockedTapRejected();
        FullTrayNotLostWhenJarMatches();
        RankingMostBlockedFirst();
        WinWithTrayCandies();
    }

    static void OneColorWins()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0));
        T.Check(g.Jars[0] != null && g.Jars[0].Color == 0, "first jar spawns the only colour");
        T.Check(g.Jars[1] == null, "second slot stays empty: no more colours");
        for (int i = 0; i < 3; i++)
        {
            var r = g.Tap(g.Board.Candies[i], out int dest);
            T.Check(r == TapResult.ToJar && dest == 0, "tap " + i + " goes to jar 0");
        }
        T.Check(g.State == GameState.Won, "three matching candies win");
        T.Check(g.JarsCompleted == 1, "one jar completed");
    }

    static void TrayRoutingAndLose()
    {
        // 6 colours, 1 candy each: jarsLeft = 0 for all, so no jar ever spawns
        var g = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5));
        T.Check(g.Jars[0] == null && g.Jars[1] == null, "no jars when no colour has 3 candies");
        for (int i = 0; i < 5; i++)
        {
            var r = g.Tap(g.Board.Candies[i], out int dest);
            T.Check(r == TapResult.ToTray && dest == i, "candy " + i + " goes to tray slot " + i);
        }
        T.Check(g.TrayCount == 5, "tray holds 5");
        T.Check(g.State == GameState.Lost, "tray full and nothing matches a jar = lost");
        T.Check(g.Tap(g.Board.Candies[5], out _) == TapResult.Rejected, "no taps after lose");
    }

    static void JarCompletionAndSpawn()
    {
        // colours 0 and 1, three each, then colour 2 three: only 2 jars, third colour waits
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        var inJar = new HashSet<int> { g.Jars[0].Color, g.Jars[1].Color };
        int waiting = -1;
        for (int c = 0; c < 3; c++) if (!inJar.Contains(c)) waiting = c;
        T.Check(waiting >= 0, "one colour has no jar yet");
        // tap a waiting-colour candy: goes to tray
        Candy w = g.Board.Candies.Find(c => c.Color == waiting);
        T.Check(g.Tap(w, out _) == TapResult.ToTray, "waiting colour goes to tray");
        // finish one jar colour -> jar leaves and the waiting colour's jar arrives, tray candy moves in
        int done = g.Jars[0].Color;
        foreach (var c in g.Board.Candies.FindAll(c => c.Color == done)) g.Tap(c, out _);
        T.Check(g.JarsCompleted == 1, "jar completed");
        T.Check(g.FindJar(waiting) >= 0, "waiting colour jar spawned after a slot freed");
        T.Check(g.TrayCount == 0, "tray candy moved into the new jar");
        int jar = g.FindJar(waiting);
        T.Check(g.Jars[jar].Count == 1, "that jar already holds the tray candy");
    }

    static void ReviveAfterLose()
    {
        var g = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5));
        for (int i = 0; i < 5; i++) g.Tap(g.Board.Candies[i], out _);
        T.Check(g.State == GameState.Lost, "precondition lost");
        int left = g.Board.Remaining;
        T.Check(g.Revive(), "revive works after lose");
        T.Check(g.State == GameState.Playing && g.TrayCount == 0, "revive clears the tray");
        T.Check(g.Board.Remaining == left, "revive leaves the board alone");
        bool allEmpty = true;
        for (int i = 0; i < g.Tray.Length; i++) if (g.Tray[i] != -1) allEmpty = false;
        T.Check(allEmpty, "every tray slot is -1 after revive");
        T.Check(!g.Revive(), "revive only when lost");
    }

    static void BlockedTapRejected()
    {
        var level = new LevelData
        {
            Number = 1, Diff = Difficulty.Normal,
            Candies = new[] { new CandySpec(0, 0, 0, 0), new CandySpec(0.2f, 0, 1, 0), new CandySpec(9, 0, 0, 0) },
            Rows = new[] { new ProgressRow(100, new[] { 1 }) },
        };
        var g = new Game(level);
        T.Check(g.Tap(g.Board.Candies[0], out int d) == TapResult.Rejected && d == -1, "covered candy is rejected");
        T.Check(g.Board.Remaining == 3, "rejected tap removes nothing");
    }

    static void FullTrayNotLostWhenJarMatches()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 2, 3, 4, 5));
        for (int i = 3; i < 8; i++) g.Tap(g.Board.Candies[i], out _);
        T.Check(g.TrayCount == 5, "tray is full");
        T.Check(g.State == GameState.Playing, "full tray but a free candy fits the jar: not lost");
        T.Check(g.Tap(g.Board.Candies[0], out _) == TapResult.ToJar, "jar-colour candy still goes to the jar");
    }

    static void RankingMostBlockedFirst()
    {
        var level = new LevelData
        {
            Number = 1, Diff = Difficulty.Normal,
            Candies = new[]
            {
                new CandySpec(0, 0, 0, 2), new CandySpec(3, 0, 0, 2), new CandySpec(6, 0, 0, 2),
                new CandySpec(0.2f, 0, 1, 0), new CandySpec(3.2f, 0, 1, 0), new CandySpec(6.2f, 0, 1, 0),
                new CandySpec(20, 0, 0, 1), new CandySpec(23, 0, 0, 1), new CandySpec(26, 0, 0, 1),
            },
            Rows = new[] { new ProgressRow(100, new[] { 1, 0, 0 }) },
        };
        var g = new Game(level);
        T.Check(g.Jars[0] != null && g.Jars[0].Color == 2, "most blocked colour gets the first jar");
        T.Check(g.Jars[1] != null && g.Jars[1].Color == 0, "tie broken by colour index");
    }

    static void WinWithTrayCandies()
    {
        var g = new Game(TestLevels.Flat(0, 1, 2));
        for (int i = 0; i < 3; i++) g.Tap(g.Board.Candies[i], out _);
        T.Check(g.TrayCount == 3, "candies wait in the tray");
        T.Check(g.State == GameState.Won, "empty board wins even with tray candies left");
    }
}
