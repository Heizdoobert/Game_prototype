using System;
using Proto.Shell;

static class ProfileTests
{
    public static void Run()
    {
        Profile.Cfg = new ShellConfig();
        var t0 = new DateTime(2026, 10, 29, 12, 0, 0, DateTimeKind.Utc);
        var p = new Profile { Boosters = new[] { 3, 3, 3 } };
        T.Check(p.Hearts == 5 && p.Level == 1 && p.Coins == 1500, "defaults");

        T.Check(p.SpendHeart(t0) && p.Hearts == 4, "spend one heart");
        T.Check(p.UntilNextHeart(t0) == TimeSpan.FromMinutes(20), "regen timer starts at 20 min");
        p.TickHearts(t0.AddMinutes(19));
        T.Check(p.Hearts == 4, "no regen before 20 min");
        p.TickHearts(t0.AddMinutes(20));
        T.Check(p.Hearts == 5, "regen after 20 min");
        T.Check(p.UntilNextHeart(t0.AddMinutes(20)) == TimeSpan.Zero, "no timer when full");

        for (int i = 0; i < 5; i++) p.SpendHeart(t0);
        T.Check(p.Hearts == 0 && !p.SpendHeart(t0), "cannot spend at 0");
        p.TickHearts(t0.AddMinutes(65));
        T.Check(p.Hearts == 3, "three hearts after 65 min");

        var q = new Profile { Boosters = new[] { 3, 3, 3 } };
        T.Check(q.CanPay(2, 700), "inventory pays first");
        q.Pay(2, 700);
        T.Check(q.Boosters[2] == 2 && q.Coins == 1500, "inventory used, coins untouched");
        q.Boosters[2] = 0;
        q.Pay(2, 700);
        T.Check(q.Coins == 800, "coins pay when inventory empty");
        q.Coins = 10;
        T.Check(!q.CanPay(2, 700), "cannot pay without coins or inventory");

        var w = new Profile();
        w.Win(60);
        T.Check(w.Level == 2 && w.Coins == 1560, "win advances level and pays");
        T.Check(w.PayRevive() && w.Coins == 660, "revive costs 900");
        w.Coins = 100;
        T.Check(!w.PayRevive() && w.Coins == 100, "revive refused when poor");

        Profile.Cfg = new ShellConfig { MaxHearts = 3, StartCoins = 7 };
        var c = new Profile();
        T.Check(c.Hearts == 3 && c.Coins == 7, "config drives a fresh profile");
        Profile.Cfg = new ShellConfig();
    }
}
