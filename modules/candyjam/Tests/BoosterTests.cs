using System.Collections.Generic;
using CandyJam.Core;

static class BoosterTests
{
    public static void Run()
    {
        AddHole();
        Broom();
        AddJar();
        Vacuum();
        Rainbow();
    }

    static void AddHole()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0));
        T.Check(g.UseAddHole() == BoosterResult.Success && g.TraySlots == 6, "add hole -> 6 slots");
        T.Check(g.UseAddHole() == BoosterResult.Success && g.TraySlots == 7, "add hole -> 7 slots");
        T.Check(g.UseAddHole() == BoosterResult.LimitReached && g.TraySlots == 7, "add hole capped at 7");
    }

    static void Broom()
    {
        var g = new Game(TestLevels.Flat(0, 1, 2, 3, 4, 5));
        T.Check(g.UseBroom() == BoosterResult.Unusable, "broom on empty tray is unusable");
        g.Tap(g.Board.Candies[0], out _);
        g.Tap(g.Board.Candies[1], out _);
        T.Check(g.TrayCount == 2, "two in tray");
        T.Check(g.UseBroom() == BoosterResult.Success, "broom succeeds");
        T.Check(g.TrayCount == 0 && g.Board.Remaining == 4, "tray emptied, candies discarded not returned");

        // a discarded candy leaves its colour with 2 candies: no jar may spawn for it, and the level stays winnable
        var g2 = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        var jarColors = new System.Collections.Generic.HashSet<int> { g2.Jars[0].Color, g2.Jars[1].Color };
        Candy w = g2.Board.Candies.Find(c => !jarColors.Contains(c.Color));
        int waiting = w.Color;
        T.Check(g2.Tap(w, out _) == TapResult.ToTray, "waiting colour candy goes to the tray");
        T.Check(g2.UseBroom() == BoosterResult.Success, "broom discards it");
        foreach (var c in g2.Board.Candies.FindAll(c => !c.Removed && c.Color != waiting)) g2.Tap(c, out _);
        T.Check(g2.Jars[0] == null && g2.Jars[1] == null, "no jar spawns for a colour with only 2 candies left");
        foreach (var c in g2.Board.Candies.FindAll(c => !c.Removed)) g2.Tap(c, out _);
        T.Check(g2.State == GameState.Won, "level still winnable after a discard");
    }

    static void AddJar()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        T.Check(g.Jars[2] == null, "slot 2 starts locked/empty");
        T.Check(g.UseAddJar() == BoosterResult.Success, "add jar unlocks a slot");
        T.Check(g.JarUnlocked[2] && g.Jars[2] != null, "third jar unlocked and filled with the third colour");
        T.Check(g.UseAddJar() == BoosterResult.Unusable, "no jars left to spawn");
        T.Check(!g.JarUnlocked[3], "fourth slot stays locked when unusable");
    }

    static void Vacuum()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0));
        var r = g.UseVacuum(out var taken);
        T.Check(r == BoosterResult.Success && taken.Count == 3, "vacuum fills the front jar with 3 free candies");
        T.Check(g.State == GameState.Won, "level won after vacuum took all");
        var g2 = new Game(TestLevels.Flat(0, 1, 2));
        T.Check(g2.UseVacuum(out _) == BoosterResult.Unusable, "vacuum without a jar is unusable");
    }

    static void Rainbow()
    {
        var g = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        var inJar = new HashSet<int> { g.Jars[0].Color, g.Jars[1].Color };
        Candy target = g.Board.Candies.Find(c => !inJar.Contains(c.Color));
        T.Check(target != null, "a candy without a jar exists");
        T.Check(g.UseRainbow(target) == BoosterResult.Success, "rainbow swaps an untouched jar to the chosen colour");
        T.Check(g.FindJar(target.Color) >= 0, "jar of the chosen colour now exists");
        T.Check(g.UseRainbow(target) == BoosterResult.Unusable, "rainbow unusable when that colour already has a jar");
        // a started jar must not be swapped: start jar 0/1 and try again with a colour lacking a jar
        var g2 = new Game(TestLevels.Flat(0, 0, 0, 1, 1, 1, 2, 2, 2));
        var inJar2 = new HashSet<int> { g2.Jars[0].Color, g2.Jars[1].Color };
        foreach (var c in g2.Board.Candies) if (g2.Jars[0] != null && c.Color == g2.Jars[0].Color) { g2.Tap(c, out _); break; }
        foreach (var c in g2.Board.Candies) if (g2.Jars[1] != null && c.Color == g2.Jars[1].Color) { g2.Tap(c, out _); break; }
        Candy t2 = g2.Board.Candies.Find(c => !inJar2.Contains(c.Color));
        T.Check(g2.UseRainbow(t2) == BoosterResult.Unusable, "rainbow cannot replace jars that already hold candies");
    }
}
