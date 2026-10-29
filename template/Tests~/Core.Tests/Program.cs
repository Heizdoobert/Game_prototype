using System;

static class Program
{
    static int Main()
    {
        int ran = 0;
        foreach (var t in typeof(Program).Assembly.GetTypes())
        {
            if (!t.Name.EndsWith("Tests")) continue;
            var run = t.GetMethod("Run", Type.EmptyTypes);
            if (run != null && run.IsStatic) { run.Invoke(null, null); ran++; }
        }
#if HAS_GAME
        // ProfileTests is always one; a game module must bring at least one more
        if (ran <= 1)
        {
            Console.WriteLine("FAIL: Game/ exists but no module test class ran (need at least one static class named *Tests with public static void Run())");
            return 1;
        }
#endif
        Console.WriteLine(T.Fails == 0 ? "ALL PASS" : "FAILURES " + T.Fails);
        return T.Fails == 0 ? 0 : 1;
    }
}
