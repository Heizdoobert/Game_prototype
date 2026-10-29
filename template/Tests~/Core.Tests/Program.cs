using System;

static class Program
{
    static int Main()
    {
        foreach (var t in typeof(Program).Assembly.GetTypes())
        {
            if (!t.Name.EndsWith("Tests")) continue;
            var run = t.GetMethod("Run", Type.EmptyTypes);
            if (run != null && run.IsStatic) run.Invoke(null, null);
        }
        Console.WriteLine(T.Fails == 0 ? "ALL PASS" : "FAILURES " + T.Fails);
        return T.Fails == 0 ? 0 : 1;
    }
}
