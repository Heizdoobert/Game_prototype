using CandyJam.Core;
using Proto.Shell;
using UnityEngine;

namespace CandyJam.View
{
    [UnityEngine.Scripting.Preserve]
    public sealed class GameModule : IGameModule
    {
        static readonly string[] Names = { "Hole", "Rainbow", "Vacuum", "Broom", "Jar", "Needle" };
        readonly BoosterDef[] boosters;
        PlayController ctl;

        // gate: level n comes from Resources/CandyJam/levels/n.txt when that file exists, else from the generator
        static readonly ILevelSource Levels = new AuthoredLevels(n =>
        {
            var t = Resources.Load<TextAsset>("CandyJam/levels/" + n);
            return t == null ? null : t.text;
        }, new GeneratedLevels());

        public GameModule()
        {
            boosters = new BoosterDef[Names.Length];
            for (int i = 0; i < Names.Length; i++) boosters[i] = new BoosterDef { Name = Names[i], Price = Rules.BoosterPrice[i], UnlockLevel = Rules.UnlockLevel[i], FreeOnUnlock = Rules.FreeOnUnlock };
        }

        public string Name { get { return "Candy Jam"; } }
        public string Tagline { get { return "Sort the candies into jars.\nDon't fill the tray!"; } }
        public BoosterDef[] Boosters { get { return boosters; } }

        public ShellConfig Config
        {
            get { return new ShellConfig { MaxHearts = Rules.MaxHearts, HeartRegenMinutes = Rules.HeartRegenMinutes, StartCoins = Rules.StartCoins, ReviveCost = Rules.ReviveCost }; }
        }

        public LevelInfo Prepare(int level)
        {
            var d = Levels.Get(level);
            return new LevelInfo { Number = level, WinCoins = Rules.WinCoins(d.Diff), Data = d };
        }

        public IPlay Begin(LevelInfo level, Profile profile, Camera cam)
        {
            if (ctl == null) ctl = new GameObject("Play").AddComponent<PlayController>();
            ctl.Begin((LevelData)level.Data, profile, cam);
            return ctl;
        }
    }
}
