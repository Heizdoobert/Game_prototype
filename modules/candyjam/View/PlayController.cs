using System;
using System.Collections;
using CandyJam.Core;
using Proto.Shell;
using UnityEngine;
using UnityEngine.EventSystems;

namespace CandyJam.View
{
    // one level session: input, flight animation, boosters; Core stays the source of truth
    public sealed class PlayController : MonoBehaviour, IPlay
    {
        public event Action<PlayStatus> Ended;
        public event Action<string> Message;
        public Game Game { get; private set; }
        public bool RainbowPending { get; private set; }

        BoardView board;
        JarTrayView tray;
        Profile profile;
        Camera cam;
        bool busy, ended;
        SpriteRenderer fly;

        public void Begin(LevelData level, Profile p, Camera c)
        {
            Stop();
            profile = p; cam = c;
            Game = new Game(level); // default seed 1 = the seed LevelGen's solver validated
            if (board == null) board = new GameObject("Board").AddComponent<BoardView>();
            if (tray == null) tray = new GameObject("JarTray").AddComponent<JarTrayView>();
            board.gameObject.SetActive(true);
            tray.gameObject.SetActive(true);
            board.Build(Game, new Vector2(0f, 0.4f), 8.6f, 9.2f);
            tray.Refresh(Game);
            busy = false; RainbowPending = false; ended = false;
        }

        public void Stop()
        {
            StopAllCoroutines();
            if (fly != null) Destroy(fly.gameObject);
            fly = null;
            ended = false;
            RainbowPending = false;
            Game = null;
            if (board != null) { board.Clear(); board.gameObject.SetActive(false); }
            if (tray != null) tray.gameObject.SetActive(false);
        }

        void Update()
        {
            if (Game == null || busy || Game.State != GameState.Playing) return;
            if (!Input.GetMouseButtonDown(0)) return;
            if (OverUi()) return;
            Vector2 p = cam.ScreenToWorldPoint(Input.mousePosition);
            var c = board.Hit(p);
            if (c == null) return;
            if (RainbowPending)
            {
                RainbowPending = false;
                if (!CanPay(BoosterKind.Rainbow)) { Say("Not enough coins"); Sync(); return; }
                if (Game.UseRainbow(c) == BoosterResult.Success) Pay(BoosterKind.Rainbow);
                else Say("Can't use Rainbow on that colour");
                Sync();
                return;
            }
            StartCoroutine(DoTap(c));
        }

        static bool OverUi()
        {
            if (EventSystem.current == null) return false;
            return Input.touchCount > 0
                ? EventSystem.current.IsPointerOverGameObject(Input.GetTouch(0).fingerId)
                : EventSystem.current.IsPointerOverGameObject();
        }

        IEnumerator DoTap(Candy c)
        {
            busy = true;
            Vector3 from = board.PosOf(c);
            Color col = Palette.Candy[c.Color];
            var r = Game.Tap(c, out int dest);
            if (r == TapResult.Rejected) { busy = false; yield break; }
            fly = new GameObject("fly").AddComponent<SpriteRenderer>();
            fly.sprite = Sprites.Disc; fly.color = col; fly.sortingOrder = 100;
            fly.transform.localScale = Vector3.one * board.Scale;
            board.Refresh();
            Vector3 to = r == TapResult.ToJar ? tray.JarWorld(dest) : tray.TrayWorld(dest);
            const float dur = 0.28f;
            for (float t = 0f; t < dur; t += Time.deltaTime)
            {
                fly.transform.position = Vector3.Lerp(from, to, t / dur);
                yield return null;
            }
            Destroy(fly.gameObject);
            fly = null;
            busy = false;
            Sync();
        }

        public void UseBooster(BoosterKind k)
        {
            if (Game == null || busy || Game.State != GameState.Playing) return;
            if (!CanPay(k)) { Say("Not enough coins"); return; }
            if (k == BoosterKind.Rainbow)
            {
                RainbowPending = !RainbowPending;
                if (RainbowPending) Say("Tap a candy: its colour gets a jar");
                return;
            }
            RainbowPending = false; // a pending Rainbow must not survive spending coins elsewhere
            BoosterResult r;
            switch (k)
            {
                case BoosterKind.AddHole: r = Game.UseAddHole(); break;
                case BoosterKind.Broom: r = Game.UseBroom(); break;
                case BoosterKind.AddJar: r = Game.UseAddJar(); break;
                default: r = Game.UseVacuum(out _); break;
            }
            if (r == BoosterResult.Success) Pay(k);
            else Say(r == BoosterResult.LimitReached ? "Already at the limit" : "Can't use that now");
            Sync();
        }

        bool CanPay(BoosterKind k) { return profile.CanPay((int)k, Rules.BoosterPrice[(int)k]); }
        void Pay(BoosterKind k) { profile.Pay((int)k, Rules.BoosterPrice[(int)k]); }

        public PlayStatus Status { get { return Game == null ? PlayStatus.Playing : (PlayStatus)(int)Game.State; } }
        public string Hint { get { return RainbowPending ? "Tap a candy: its colour gets a jar" : null; } }
        void IPlay.UseBooster(int id) { UseBooster((BoosterKind)id); }

        public bool Revive()
        {
            if (Game == null || !Game.Revive()) return false;
            Sync();
            return true;
        }

        void Say(string m) { if (Message != null) Message(m); }

        public void Sync()
        {
            if (Game == null) return;
            board.Refresh();
            tray.Refresh(Game);
            if (Game.State == GameState.Playing) ended = false; // e.g. after Revive
            else if (!ended)
            {
                ended = true;
                if (Ended != null) Ended((PlayStatus)(int)Game.State);
            }
        }
    }
}
