namespace CandyJam.Core
{
    public enum Difficulty { Normal, Hard, VeryHard }
    public enum TapResult { Rejected, ToJar, ToTray }
    public enum GameState { Playing, Won, Lost }
    public enum BoosterKind { AddHole, Rainbow, Vacuum, Broom, AddJar, Needle }
    public enum BoosterResult { Success, Unusable, LimitReached }

    public static class Rules
    {
        public const int JarCapacity = 3;
        public const int JarSlots = 4;
        public const int JarsUnlocked = 2;
        public const int TrayInit = 5;
        public const int TrayMax = 7;
        public const int Palette = 12;
        public const float CandyRadius = 0.5f;
        public const float CoverDist = 0.9f;
        public const int MaxHearts = 5;
        public const int HeartRegenMinutes = 20;
        public const int StartCoins = 1500;
        public const int ReviveCost = 900;
        // indexed by BoosterKind; original 3-pack prices 1200/1500/1500/2100 divided by 3, AddJar tuned, Needle [tuned]
        public static readonly int[] BoosterPrice = { 400, 500, 500, 700, 400, 500 };

        // by BoosterKind index: unlock level and free grant on unlock (KB 02_gameplay_rules)
        public static readonly int[] UnlockLevel = { 2, 9, 5, 7, 4, 12 };
        public const int FreeOnUnlock = 3;

        public static int WinCoins(Difficulty d)
        {
            return d == Difficulty.VeryHard ? 70 : d == Difficulty.Hard ? 60 : 50;
        }
    }
}
