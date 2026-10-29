using System;

namespace Proto.Shell
{
    // public fields so UnityEngine.JsonUtility can persist it; Cfg is set by the app before a profile is created
    [Serializable]
    public sealed class Profile
    {
        public static ShellConfig Cfg = new ShellConfig();

        public int Level = 1;
        public int Coins = Cfg.StartCoins;
        public int Hearts = Cfg.MaxHearts;
        public long HeartRegenAtTicks;
        public int[] Boosters = new int[0];

        public void TickHearts(DateTime nowUtc)
        {
            if (Hearts >= Cfg.MaxHearts) { HeartRegenAtTicks = 0; return; }
            var at = new DateTime(HeartRegenAtTicks, DateTimeKind.Utc);
            while (Hearts < Cfg.MaxHearts && nowUtc >= at)
            {
                Hearts++;
                at = at.AddMinutes(Cfg.HeartRegenMinutes);
            }
            HeartRegenAtTicks = Hearts >= Cfg.MaxHearts ? 0 : at.Ticks;
        }

        public bool SpendHeart(DateTime nowUtc)
        {
            TickHearts(nowUtc);
            if (Hearts <= 0) return false;
            if (Hearts == Cfg.MaxHearts) HeartRegenAtTicks = nowUtc.AddMinutes(Cfg.HeartRegenMinutes).Ticks;
            Hearts--;
            return true;
        }

        public TimeSpan UntilNextHeart(DateTime nowUtc)
        {
            if (Hearts >= Cfg.MaxHearts) return TimeSpan.Zero;
            var d = new DateTime(HeartRegenAtTicks, DateTimeKind.Utc) - nowUtc;
            return d < TimeSpan.Zero ? TimeSpan.Zero : d;
        }

        public bool CanPay(int id, int price) { return Boosters[id] > 0 || Coins >= price; }

        public void Pay(int id, int price)
        {
            if (Boosters[id] > 0) Boosters[id]--;
            else Coins -= price;
        }

        public void Win(int coins) { Coins += coins; Level++; }

        public bool PayRevive()
        {
            if (Coins < Cfg.ReviveCost) return false;
            Coins -= Cfg.ReviveCost;
            return true;
        }
    }
}
