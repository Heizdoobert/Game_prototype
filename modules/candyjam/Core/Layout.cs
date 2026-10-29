using System;
using System.Collections.Generic;

namespace CandyJam.Core
{
    public static class Layout
    {
        public enum Style { OffsetGrid, Concentric, Banded }

        const float Spacing = 1.2f;
        const float SameLayerGap = 1.0f; // candies on one layer must not overlap visually

        public static List<(float X, float Y, int Layer)> Build(int shape, Style style, int layers, int count, Random rng)
        {
            float radius;
            return Build(shape, style, layers, count, rng, out radius);
        }

        // layered grid points inside a shape; the radius grows until the shape holds count points
        public static List<(float X, float Y, int Layer)> Build(int shape, Style style, int layers, int count, Random rng, out float radius)
        {
            for (radius = 2.5f; ; radius += 0.3f)
            {
                // offset-grid layers alternate half a cell so they overlap (cover) lower ones;
                // the other styles scatter two such lattices and relabel the layer by position
                int lattices = style == Style.OffsetGrid ? layers : 2;
                var all = new List<(float X, float Y, int Layer)>();
                int n = (int)(radius / Spacing) + 2;
                for (int l = 0; l < lattices; l++)
                {
                    float off = (l % 2) * Spacing / 2f;
                    for (int gx = -n; gx <= n; gx++)
                        for (int gy = -n; gy <= n; gy++)
                        {
                            float x = gx * Spacing + off, y = gy * Spacing + off;
                            if (Shapes.Inside(shape, x / radius, y / radius)) all.Add((x, y, l));
                        }
                }
                if (style != Style.OffsetGrid) all = Relabel(all, style, layers, radius, rng);
                if (all.Count < count) continue;
                if (style == Style.OffsetGrid) Shuffle(all, rng);
                all.RemoveRange(count, all.Count - count);
                return all;
            }
        }

        static List<(float X, float Y, int Layer)> Relabel(List<(float X, float Y, int Layer)> cand, Style style, int layers, float radius, Random rng)
        {
            Shuffle(cand, rng);
            float band = Spacing * 1.5f;
            var kept = new List<(float X, float Y, int Layer)>();
            foreach (var p in cand)
            {
                int layer;
                if (style == Style.Concentric)
                {
                    float r = (float)Math.Sqrt(p.X * p.X + p.Y * p.Y);
                    layer = Math.Max(0, Math.Min(layers - 1, (int)((1f - r / radius) * layers)));
                }
                else layer = ((int)Math.Floor((p.X + radius) / band) % layers + layers) % layers;
                bool clash = false;
                foreach (var k in kept)
                {
                    float dx = k.X - p.X, dy = k.Y - p.Y;
                    if (k.Layer == layer && dx * dx + dy * dy < SameLayerGap * SameLayerGap) { clash = true; break; }
                }
                if (!clash) kept.Add((p.X, p.Y, layer));
            }
            return kept;
        }

        static void Shuffle<T>(IList<T> a, Random r)
        {
            for (int i = a.Count - 1; i > 0; i--)
            {
                int j = r.Next(i + 1);
                T tmp = a[i]; a[i] = a[j]; a[j] = tmp;
            }
        }
    }
}
