namespace Proto.Shell
{
    // economy knobs the shell owns; a game module overrides what its source game differs on
    public sealed class ShellConfig
    {
        public int MaxHearts = 5;
        public int HeartRegenMinutes = 20;
        public int StartCoins = 1500;
        public int ReviveCost = 900;
    }
}
