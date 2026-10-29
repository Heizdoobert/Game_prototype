using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace Proto.Shell
{
    // screen flow: Home -> Play -> Win / Lose(Revive); all UI is built here in code; the game lives behind IGameModule
    public sealed class App : MonoBehaviour
    {
        static readonly Color Pink = new Color(0.93f, 0.25f, 0.5f);
        static readonly Color Grey = new Color(0.45f, 0.45f, 0.5f);

        IGameModule mod;
        Profile profile;
        Camera cam;
        IPlay play;
        LevelInfo level;
        RectTransform home, boosterBar, modal;
        Text topLeft, topRight, toast, hint;
        Text[] boosterText;
        float toastUntil;

        void Start()
        {
            var type = typeof(App).Assembly.GetTypes().First(t => !t.IsAbstract && typeof(IGameModule).IsAssignableFrom(t));
            mod = (IGameModule)Activator.CreateInstance(type);
            Profile.Cfg = mod.Config;
            profile = SaveStore.Load(mod.Boosters.Length);
            cam = Camera.main;
            if (cam == null) cam = new GameObject("Camera", typeof(Camera), typeof(AudioListener)) { tag = "MainCamera" }.GetComponent<Camera>();
            cam.orthographic = true;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.99f, 0.93f, 0.88f);
            cam.transform.position = new Vector3(0f, 0f, -10f);
            cam.orthographicSize = Mathf.Max(8.5f, 5.2f / cam.aspect);

            Ui.EventSystem();
            var canvas = Ui.Canvas();
            BuildTopBar(canvas.transform);
            BuildBoosterBar(canvas.transform);
            BuildHome(canvas.transform);
            ShowHome();
        }

        void Update()
        {
            if (profile == null || topLeft == null) return; // Start not finished
            var now = DateTime.UtcNow;
            profile.TickHearts(now);
            topLeft.text = "Level " + profile.Level;
            var wait = profile.UntilNextHeart(now);
            string timer = profile.Hearts < Profile.Cfg.MaxHearts ? string.Format(" ({0}:{1:00})", (int)wait.TotalMinutes, wait.Seconds) : "";
            topRight.text = "Coins " + profile.Coins + "   Hearts " + profile.Hearts + timer;
            for (int i = 0; i < boosterText.Length; i++)
            {
                int inv = profile.Boosters[i];
                boosterText[i].text = mod.Boosters[i].Name + "\n" + (inv > 0 ? "x" + inv : mod.Boosters[i].Price + "c");
            }
            string h = play != null ? play.Hint : null;
            hint.text = h ?? "";
            hint.enabled = h != null;
            toast.enabled = Time.time < toastUntil;
        }

        void OnApplicationPause(bool paused) { if (paused && profile != null) SaveStore.Save(profile); }
        void OnApplicationQuit() { if (profile != null) SaveStore.Save(profile); }

        // ---------- building blocks ----------

        void BuildTopBar(Transform parent)
        {
            Ui.Panel(Ui.Rect(parent, "top", new Vector2(0, 0.94f), Vector2.one), "bg", new Color(1f, 1f, 1f, 0.6f));
            topLeft = Ui.Label(parent, "", 44, TextAnchor.MiddleLeft, new Vector2(0.04f, 0.94f), new Vector2(0.4f, 1f));
            topRight = Ui.Label(parent, "", 36, TextAnchor.MiddleRight, new Vector2(0.4f, 0.94f), new Vector2(0.96f, 1f));
            toast = Ui.Label(parent, "", 40, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.125f), new Vector2(0.95f, 0.175f));
            hint = Ui.Label(parent, "", 40, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.245f), new Vector2(0.95f, 0.295f));
        }

        void BuildBoosterBar(Transform parent)
        {
            int n = mod.Boosters.Length;
            boosterText = new Text[n];
            boosterBar = Ui.Rect(parent, "boosters", new Vector2(0, 0), new Vector2(1, 0.12f));
            for (int i = 0; i < n; i++)
            {
                int id = i;
                float x0 = i / (float)n + 0.01f, x1 = (i + 1) / (float)n - 0.01f;
                var b = Ui.Button(boosterBar, "", new Vector2(x0, 0.1f), new Vector2(x1, 0.9f), () => { if (play != null) play.UseBooster(id); }, Pink);
                boosterText[i] = b.GetComponentInChildren<Text>();
                boosterText[i].fontSize = 30;
            }
        }

        void BuildHome(Transform parent)
        {
            home = Ui.Panel(parent, "home", new Color(0.99f, 0.93f, 0.88f, 1f));
            home.SetSiblingIndex(0);
            Ui.Label(home, mod.Name, 120, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.62f), new Vector2(0.95f, 0.78f));
            Ui.Label(home, mod.Tagline, 44, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.5f), new Vector2(0.95f, 0.62f));
            Ui.Button(home, "Play", new Vector2(0.25f, 0.3f), new Vector2(0.75f, 0.4f), StartLevel, Pink);
        }

        RectTransform Modal(string title, string body, params (string label, UnityAction act)[] buttons)
        {
            ClearModal();
            var parent = home.parent;
            modal = Ui.Panel(parent, "modal", new Color(0f, 0f, 0f, 0.6f));
            var box = Ui.Panel(modal, "box", new Color(1f, 0.97f, 0.92f, 1f));
            box.anchorMin = new Vector2(0.1f, 0.3f); box.anchorMax = new Vector2(0.9f, 0.7f);
            Ui.Label(box, title, 80, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.7f), new Vector2(0.95f, 0.95f));
            Ui.Label(box, body, 44, TextAnchor.MiddleCenter, new Vector2(0.05f, 0.5f), new Vector2(0.95f, 0.7f));
            float h = 0.45f / Mathf.Max(1, buttons.Length);
            for (int i = 0; i < buttons.Length; i++)
            {
                float top = 0.45f - i * h;
                Ui.Button(box, buttons[i].label, new Vector2(0.1f, top - h + 0.015f), new Vector2(0.9f, top - 0.015f), buttons[i].act, i == 0 ? Pink : Grey);
            }
            return modal;
        }

        void ClearModal() { if (modal != null) Destroy(modal.gameObject); modal = null; }

        void Toast(string m)
        {
            toast.text = m;
            toastUntil = Time.time + 1.6f;
            toast.transform.SetAsLastSibling(); // stay readable above a modal's dim overlay
        }

        void Detach()
        {
            if (play == null) return;
            play.Ended -= OnEnded;
            play.Message -= Toast;
            play.Stop();
            play = null;
        }

        // ---------- flow ----------

        void ShowHome()
        {
            ClearModal();
            Detach();
            home.gameObject.SetActive(true);
            boosterBar.gameObject.SetActive(false);
            SaveStore.Save(profile);
        }

        void StartLevel()
        {
            profile.TickHearts(DateTime.UtcNow);
            if (profile.Hearts <= 0) { Toast("Out of hearts - wait for one to regenerate"); return; }
            ClearModal();
            Detach();
            if (level == null || level.Number != profile.Level) level = mod.Prepare(profile.Level);
            home.gameObject.SetActive(false);
            boosterBar.gameObject.SetActive(true);
            play = mod.Begin(level, profile, cam);
            play.Ended += OnEnded;
            play.Message += Toast;
        }

        void OnEnded(PlayStatus s)
        {
            if (s == PlayStatus.Won)
            {
                int gain = level.WinCoins;
                profile.Win(gain);
                SaveStore.Save(profile);
                Modal("Level clear!", "+" + gain + " coins", ("Next level", new UnityAction(StartLevel)), ("Home", new UnityAction(ShowHome)));
            }
            else
            {
                string revive = "Revive (" + Profile.Cfg.ReviveCost + " coins)";
                Modal("You lost", "Revive keeps your progress.\nRetry costs a heart.",
                    (revive, new UnityAction(TryRevive)), ("Retry", new UnityAction(Retry)), ("Home", new UnityAction(GiveUp)));
            }
        }

        void TryRevive()
        {
            if (profile.Coins < Profile.Cfg.ReviveCost) { Toast("Not enough coins"); return; }
            if (play == null || !play.Revive()) { Toast("Can't revive"); return; }
            profile.PayRevive();
            ClearModal();
            SaveStore.Save(profile);
        }

        void Retry()
        {
            if (!profile.SpendHeart(DateTime.UtcNow)) { ShowHome(); return; }
            SaveStore.Save(profile);
            if (profile.Hearts <= 0) { ShowHome(); Toast("Out of hearts - wait for one to regenerate"); return; }
            StartLevel();
        }

        void GiveUp()
        {
            profile.SpendHeart(DateTime.UtcNow);
            ShowHome();
        }
    }
}
