using System;
using System.Collections.Generic;

namespace CandyJam.Core
{
    public static class LevelGen
    {
        public static Difficulty DifficultyOf(int n)
        {
            if (n >= 5 && n % 15 == 0) return Difficulty.VeryHard;
            if (n >= 5 && n % 8 == 0) return Difficulty.Hard;
            return Difficulty.Normal;
        }

        // Normal: ramp min(12, 3 + n/6). Hard/VeryHard capped at what the bot reaches on those boards (measured
        // Hard 4-6 past level 60, VeryHard 3-4), so early attempts pass instead of failing solves at every colour step [tuned]
        public static int TargetColors(int n)
        {
            int ramp = Math.Min(Rules.MaxColors, 3 + n / 6);
            var d = DifficultyOf(n);
            return d == Difficulty.VeryHard ? Math.Min(ramp, 4) : d == Difficulty.Hard ? Math.Min(ramp, 5) : ramp;
        }

        // ponytail: bot-verified rejection sampling; colour count drops every 5 failed attempts (floor 3), counted in
        // attempts, never time, so generation stays deterministic. A failed solve on a big board costs ~0.2 s.
        public static LevelData Generate(int number)
        {
            int colors = TargetColors(number);
            for (int attempt = 0; attempt < 200; attempt++)
            {
                if (attempt > 0 && attempt % 5 == 0 && colors > 3) colors--;
                var level = Build(number, colors, attempt);
                if (Solver.Solve(level)) return level;
            }
            throw new InvalidOperationException("no solvable layout for level " + number);
        }

        // cycle through all silhouettes in a reshuffled order; a cycle never starts with the previous one's last shape
        public static int ShapeOf(int n)
        {
            int cycle = (n - 1) / Rules.ShapeCount;
            while (Perms.Count <= cycle) Perms.Add(NextPerm(Perms.Count));
            return Perms[cycle][(n - 1) % Rules.ShapeCount];
        }

        static readonly List<int[]> Perms = new List<int[]>();

        static int[] NextPerm(int c)
        {
            var prev = c > 0 ? Perms[c - 1] : null;
            for (int attempt = 0; ; attempt++)
            {
                var p = new int[Rules.ShapeCount];
                for (int i = 0; i < p.Length; i++) p[i] = i;
                Layout.Shuffle(p, new Random(c * 7919 + attempt * 31 + 5));
                if (prev == null || SeamOk(prev, p)) return p;
            }
        }

        // equal shapes in neighbouring cycles must sit at least 8 levels apart (p-prev positions)
        static bool SeamOk(int[] prev, int[] p)
        {
            var posPrev = new int[p.Length];
            for (int i = 0; i < prev.Length; i++) posPrev[prev[i]] = i;
            for (int i = 0; i < p.Length; i++) if (Rules.ShapeCount + i - posPrev[p[i]] < 8) return false;
            return true;
        }

        public static int LayersOf(int n)
        {
            var d = DifficultyOf(n);
            return Math.Min(2 + n / 12 + (d == Difficulty.VeryHard ? 2 : d == Difficulty.Hard ? 1 : 0), 6);
        }

        // hashed so the style does not line up with the tier cadence; Hard/VeryHard skip Concentric, the loosest
        // cover (~19% of candies covered at start vs Banded ~30%, OffsetGrid ~80%), so tiers really are harder [tuned]
        public static Layout.Style StyleOf(int n)
        {
            var s = (Layout.Style)(((uint)n * 2654435761u >> 16) % 3);
            return s == Layout.Style.Concentric && DifficultyOf(n) != Difficulty.Normal ? Layout.Style.Banded : s;
        }

        static LevelData Build(int number, int colors, int attempt)
        {
            var rng = new Random(number * 7919 + 13 + attempt * 101);
            var diff = DifficultyOf(number);
            double scale = diff == Difficulty.VeryHard ? 1.16 : diff == Difficulty.Hard ? 1.08 : 1.0;
            int count = Math.Min((int)(Math.Min(54 + (number - 1) * 2, 297) * scale), 297) / 3 * 3;
            int layers = LayersOf(number);
            var pts = Layout.Build(ShapeOf(number), StyleOf(number), layers, count, rng);

            var ids = new List<int>();
            for (int i = 0; i < Rules.Palette; i++) ids.Add(i);
            Layout.Shuffle(ids, rng);
            var colorOf = new List<int>();
            var groups = Groups(colors, count / 3, rng);
            for (int i = 0; i < colors; i++)
                for (int k = 0; k < groups[i] * 3; k++) colorOf.Add(ids[i]);
            Layout.Shuffle(colorOf, rng);

            var specs = new CandySpec[count];
            for (int i = 0; i < count; i++) specs[i] = new CandySpec(pts[i].X, pts[i].Y, pts[i].Layer, colorOf[i]);
            return new LevelData { Number = number, Diff = diff, Candies = specs, Rows = RowsFor(diff) };
        }

        // colorRate: each colour is common (weight 10) or rare (5), at least one of each; groups of 3 candies are
        // shared out in proportion to weight, every colour gets one
        static int[] Groups(int colors, int total, Random rng)
        {
            var w = new int[colors];
            for (int i = 0; i < colors; i++) w[i] = rng.Next(2) == 0 ? 10 : 5;
            if (colors >= 2 && Array.IndexOf(w, 5) < 0) w[rng.Next(colors)] = 5;
            if (colors >= 2 && Array.IndexOf(w, 10) < 0) w[rng.Next(colors)] = 10;
            var g = new int[colors];
            for (int i = 0; i < colors; i++) g[i] = 1;
            for (int n = colors; n < total; n++)
            {
                int best = 0; // most under-served by weight: w/g largest
                for (int i = 1; i < colors; i++) if (w[i] * g[best] > w[best] * g[i]) best = i;
                g[best]++;
            }
            return g;
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
    }
}
