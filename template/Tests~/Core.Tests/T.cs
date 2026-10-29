using System;

static class T
{
    public static int Fails;
    public static void Check(bool ok, string msg)
    {
        if (ok) return;
        Fails++;
        Console.WriteLine("FAIL: " + msg);
    }
}
