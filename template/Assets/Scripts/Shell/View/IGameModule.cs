using System;
using UnityEngine;

namespace Proto.Shell
{
    public enum PlayStatus { Playing, Won, Lost }

    public sealed class BoosterDef { public string Name; public int Price; }

    // Prepare() does the heavy per-level work once; Data carries the module's own level object to Begin()
    public sealed class LevelInfo { public int Number; public int WinCoins; public object Data; }

    public interface IPlay
    {
        PlayStatus Status { get; }
        string Hint { get; }                       // shown over the board while non-null (e.g. a pending booster)
        event Action<PlayStatus> Ended;
        event Action<string> Message;              // short toast
        void UseBooster(int id);
        bool Revive();                             // false = not possible; true = the failure is cleared
        void Stop();
    }

    public interface IGameModule
    {
        string Name { get; }
        string Tagline { get; }
        ShellConfig Config { get; }
        BoosterDef[] Boosters { get; }
        LevelInfo Prepare(int level);
        IPlay Begin(LevelInfo level, Profile profile, Camera cam);
    }
}
