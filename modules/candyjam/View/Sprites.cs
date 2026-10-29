using System;
using UnityEngine;

namespace CandyJam.View
{
    // all art is drawn at runtime: white shapes that are tinted by SpriteRenderer.color
    public static class Sprites
    {
        const float Ppu = 128f; // 128 px = 1 world unit, so Disc is exactly one candy wide
        static Sprite disc, jar, slot;

        public static Sprite Disc
        {
            get
            {
                if (disc == null) disc = Make(128, 128, (x, y) =>
                {
                    float nx = (x + 0.5f) / 64f - 1f, ny = (y + 0.5f) / 64f - 1f;
                    float d = Mathf.Sqrt(nx * nx + ny * ny);
                    float a = Mathf.Clamp01((1f - d) * 16f);
                    float shade = 0.78f + 0.22f * (1f - d);
                    float hl = Mathf.Clamp01(1f - Vector2.Distance(new Vector2(nx, ny), new Vector2(-0.35f, 0.4f)) * 3.2f);
                    float stripe = ((x + y) / 14) % 2 == 0 ? 0.06f : 0f;
                    float v = Mathf.Clamp01(shade + hl * 0.5f + stripe);
                    return new Color(v, v, v, a);
                });
                return disc;
            }
        }

        public static Sprite Jar
        {
            get
            {
                if (jar == null) jar = RoundRect(256, 192, 28f, 6f, 0.5f);
                return jar;
            }
        }

        public static Sprite Slot
        {
            get
            {
                if (slot == null) slot = RoundRect(128, 128, 24f, 4f, 0.45f);
                return slot;
            }
        }

        static Sprite RoundRect(int w, int h, float r, float border, float fillAlpha)
        {
            return Make(w, h, (x, y) =>
            {
                float rx = Mathf.Abs(x + 0.5f - w / 2f) - (w / 2f - r);
                float ry = Mathf.Abs(y + 0.5f - h / 2f) - (h / 2f - r);
                float outside = Mathf.Sqrt(Mathf.Max(rx, 0f) * Mathf.Max(rx, 0f) + Mathf.Max(ry, 0f) * Mathf.Max(ry, 0f));
                float dd = outside + Mathf.Min(Mathf.Max(rx, ry), 0f) - r; // < 0 inside
                float a = Mathf.Clamp01(-dd);
                bool rim = dd > -border;
                float v = rim ? 0.8f : 1f;
                return new Color(v, v, v, a * (rim ? 1f : fillAlpha));
            });
        }

        static Sprite Make(int w, int h, Func<int, int, Color> px)
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
            };
            var c = new Color[w * h];
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                    c[y * w + x] = px(x, y);
            t.SetPixels(c);
            t.Apply();
            return Sprite.Create(t, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), Ppu);
        }
    }
}
