using System;
using UnityEngine;

namespace Proto.Shell
{
    public enum PlayStatus { Playing, Won, Lost }

    public sealed class BoosterDef { public string Name; public int Price; }

    /// <summary>
    /// Prepare() does the heavy per-level work once; Data carries the module's own level object to Begin().
    /// The shell reuses the same LevelInfo on retry, so Begin() must not mutate Data.
    /// </summary>
    public sealed class LevelInfo
    {
        public int Number;
        /// <summary>Coins the shell pays when the play ends Won.</summary>
        public int WinCoins;
        public object Data;
    }

    /// <summary>One running level, created by IGameModule.Begin.</summary>
    public interface IPlay
    {
        PlayStatus Status { get; }

        /// <summary>Non-null only while a pending action needs a prompt (e.g. a booster awaiting a target); the shell shows it over the board.</summary>
        string Hint { get; }

        /// <summary>Raised at most once per Won/Lost transition (again after a successful Revive and a new loss).</summary>
        event Action<PlayStatus> Ended;

        /// <summary>Short toast text for the shell to display.</summary>
        event Action<string> Message;

        void UseBooster(int id);

        /// <summary>The module refreshes its own view. Return true only if the failure state was actually cleared; false = not possible (the shell then charges nothing).</summary>
        bool Revive();

        void Stop();
    }

    /// <summary>
    /// The seam between the shell and a game. Exactly one implementation may exist in the project: the shell finds it by
    /// reflection. It needs a parameterless constructor (may be non-public) and should be marked
    /// [UnityEngine.Scripting.Preserve] so IL2CPP stripping cannot remove it.
    /// </summary>
    public interface IGameModule
    {
        string Name { get; }
        string Tagline { get; }
        ShellConfig Config { get; }

        /// <summary>Must return a cached array (read every frame). Its Length fixes the number of booster slots in the profile.</summary>
        BoosterDef[] Boosters { get; }

        LevelInfo Prepare(int level);
        IPlay Begin(LevelInfo level, Profile profile, Camera cam);
    }
}
