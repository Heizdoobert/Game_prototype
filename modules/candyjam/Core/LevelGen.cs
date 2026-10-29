using System;
using System.Collections.Generic;

namespace CandyJam.Core
{
    public static class LevelGen
    {
        const float Spacing = 1.2f;

        struct Pt { public float X, Y; public int Layer; }

        public static Difficulty DifficultyOf(int n)
        {
            if (n >= 5 && n % 15 == 0) return Difficulty.VeryHard;
            if (n >= 5 && n % 8 == 0) return Difficulty.Hard;
            return Difficulty.Normal;
        }

        // ponytail: bot-verified rejection sampling; colour count drops every 10 failed attempts (floor 3).
        // The greedy Solver cannot solve >= 5 colours at real board sizes, so the ramp stops at 5; the fallback
        // decrement stays as a safety net. Lever for more colours = a stronger Solver.
        public static LevelData Generate(int number)
        {
            int colors = Math.Min(5, 3 + number / 15);
            for (int attempt = 0; attempt < 200; attempt++)
            {
                if (attempt > 0 && attempt % 10 == 0 && colors > 3) colors--;
                var level = Build(number, colors, attempt);
                if (Solver.Solve(level)) return level;
            }
            throw new InvalidOperationException("no solvable layout for level " + number);
        }

        static LevelData Build(int number, int colors, int attempt)
        {
            var rng = new Random(number * 7919 + 13 + attempt * 101);
            int count = Math.Min(54 + (number - 1) * 2, 297) / 3 * 3;
            int layers = Math.Min(2 + number / 12, 5);
            var pts = Layout((number - 1) % 5, layers, count, rng);

            var ids = new List<int>();
            for (int i = 0; i < Rules.Palette; i++) ids.Add(i);
            Shuffle(ids, rng);
            var colorOf = new List<int>();
            for (int g = 0; g < count / 3; g++)
            {
                int c = ids[g % colors];
                colorOf.Add(c); colorOf.Add(c); colorOf.Add(c);
            }
            Shuffle(colorOf, rng);

            var specs = new CandySpec[count];
            for (int i = 0; i < count; i++) specs[i] = new CandySpec(pts[i].X, pts[i].Y, pts[i].Layer, colorOf[i]);
            var diff = DifficultyOf(number);
            return new LevelData { Number = number, Diff = diff, Candies = specs, Rows = RowsFor(diff) };
        }

        static ProgressRow[] RowsFor(Difficulty d)
        {
            switch (d)
            {
                case Difficulty.Hard:
                    return new[] { new ProgressRow(100, new[] { 40, 20, 10, 5, 2, 1 }) };
                case Difficulty.VeryHard:
                    return new[] { new ProgressRow(50, new[] { 80, 20, 5, 1 }), new ProgressRow(100, new[] { 60, 30, 10, 5, 1 }) };
                default:
                    return new[] { new ProgressRow(100, new[] { 1 }) };
            }
        }

        // layered grid points inside a shape; odd layers are offset half a cell so they overlap (cover) lower ones
        static List<Pt> Layout(int shape, int layers, int count, Random rng)
        {
            for (float radius = 2.5f; ; radius += 0.3f)
            {
                var all = new List<Pt>();
                int n = (int)(radius / Spacing) + 2;
                for (int l = 0; l < layers; l++)
                {
                    float off = (l % 2) * Spacing / 2f;
                    for (int gx = -n; gx <= n; gx++)
                        for (int gy = -n; gy <= n; gy++)
                        {
                            float x = gx * Spacing + off, y = gy * Spacing + off;
                            if (Inside(shape, x / radius, y / radius)) all.Add(new Pt { X = x, Y = y, Layer = l });
                        }
                }
                if (all.Count < count) continue;
                Shuffle(all, rng);
                all.RemoveRange(count, all.Count - count);
                return all;
            }
        }

        static bool Inside(int shape, float u, float v)
        {
            float r = (float)Math.Sqrt(u * u + v * v);
            switch (shape)
            {
                case 0: return r <= 1f; // circle
                case 1: // heart
                {
                    float a = u * 1.15f, b = v * 1.15f + 0.1f;
                    float t = a * a + b * b - 1f;
                    return t * t * t - a * a * b * b * b <= 0f;
                }
                case 2: // five-point star
                {
                    float th = (float)Math.Atan2(v, u);
                    return r <= 0.72f + 0.28f * (float)Math.Cos(5.0 * (th - Math.PI / 2));
                }
                case 3: return r >= 0.45f && r <= 1f; // ring
                default: return Math.Abs(u) + Math.Abs(v) <= 1f; // diamond
            }
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
