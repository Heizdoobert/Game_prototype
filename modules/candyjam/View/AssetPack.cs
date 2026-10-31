using System.Collections.Generic;
using CandyJam.Core;
using UnityEngine;

namespace CandyJam.View
{
    public struct Look
    {
        public Sprite Sprite;
        public Color Tint; // white for a full-colour sprite
        public Look(Sprite sprite, Color tint) { Sprite = sprite; Tint = tint; }
    }

    // gate: everything the game shows or plays that is not rules. Views ask Art.Pack and never name a file or a colour.
    public interface IAssetPack
    {
        Look Candy(int color);
        Color Tint(int color);        // the colour of a jar fill for this candy colour
        Sprite Jar { get; }
        Sprite Slot { get; }
        Sprite Background { get; }    // null = none, the camera colour shows
        AudioClip Clip(Sfx sfx);      // null = silent
    }

    // the built-in art: white shapes drawn at runtime, tinted by the palette
    public sealed class ProceduralPack : IAssetPack
    {
        public Look Candy(int color) { return new Look(Sprites.Disc, Palette.Candy[color]); }
        public Color Tint(int color) { return Palette.Candy[color]; }
        public Sprite Jar { get { return Sprites.Jar; } }
        public Sprite Slot { get { return Sprites.Slot; } }
        public Sprite Background { get { return null; } }
        public AudioClip Clip(Sfx sfx) { return null; }
    }

    // Files under Resources/<root>/ named by PackKeys (png or wav); each missing one falls back, so a half-made pack works.
    // Images are 128 px per world unit: a candy is 128 px, a jar 256x192.
    public sealed class ResourcesPack : IAssetPack
    {
        const float Ppu = 128f;
        readonly string root;
        readonly IAssetPack fallback;
        readonly Dictionary<string, Sprite> sprites = new Dictionary<string, Sprite>();
        readonly Dictionary<Sfx, AudioClip> clips = new Dictionary<Sfx, AudioClip>();
        readonly Look[] candies = new Look[Rules.Palette];
        readonly bool[] candyDone = new bool[Rules.Palette];

        public ResourcesPack(string root, IAssetPack fallback) { this.root = root; this.fallback = fallback; }

        public Look Candy(int color)
        {
            if (candyDone[color]) return candies[color];
            var own = Load(PackKeys.CandyColor(color));
            var shared = own == null ? Load(PackKeys.Candy) : null;
            candies[color] = own != null ? new Look(own, Color.white)
                : shared != null ? new Look(shared, fallback.Tint(color))
                : fallback.Candy(color);
            candyDone[color] = true;
            return candies[color];
        }

        public Color Tint(int color) { return fallback.Tint(color); }
        public Sprite Jar { get { return Load(PackKeys.Jar) ?? fallback.Jar; } }
        public Sprite Slot { get { return Load(PackKeys.Slot) ?? fallback.Slot; } }
        public Sprite Background { get { return Load(PackKeys.Background) ?? fallback.Background; } }

        public AudioClip Clip(Sfx sfx)
        {
            if (!clips.TryGetValue(sfx, out var c)) clips[sfx] = c = Resources.Load<AudioClip>(root + "/" + PackKeys.SfxName(sfx));
            return c != null ? c : fallback.Clip(sfx);
        }

        // a PNG in Resources imports as Texture2D unless set to Sprite, so accept both
        Sprite Load(string key)
        {
            if (sprites.TryGetValue(key, out var s)) return s;
            s = Resources.Load<Sprite>(root + "/" + key);
            if (s == null)
            {
                var t = Resources.Load<Texture2D>(root + "/" + key);
                if (t != null) s = Sprite.Create(t, new Rect(0, 0, t.width, t.height), new Vector2(0.5f, 0.5f), Ppu);
            }
            sprites[key] = s;
            return s;
        }
    }

    // the one place that decides which pack the game uses
    public static class Art
    {
        public static IAssetPack Pack = new ResourcesPack("CandyJam/pack", new ProceduralPack());
    }

    public static class Audio
    {
        static AudioSource src;

        public static void Play(Sfx sfx)
        {
            var clip = Art.Pack.Clip(sfx);
            if (clip == null) return;
            if (src == null)
            {
                var go = new GameObject("Sfx");
                Object.DontDestroyOnLoad(go);
                src = go.AddComponent<AudioSource>();
            }
            src.PlayOneShot(clip);
        }
    }
}
