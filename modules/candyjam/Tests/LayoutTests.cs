using System;
using System.Collections.Generic;
using CandyJam.Core;

static class LayoutTests
{
    public static void Run()
    {
        T.Check(Rules.ShapeCount == 16, "16 silhouettes");
        bool threw = false;
        try { Shapes.Inside(16, 0f, 0f); } catch (ArgumentOutOfRangeException) { threw = true; }
        T.Check(threw, "unknown shape index throws");
        Determinism();
        LayerRule();
        ShapeAreas();
        ShapeSchedule();
        StyleLayouts();
        StyleStructure();
        CountsTiersScores();
    }

    static void ShapeAreas()
    {
        for (int s = 0; s < Rules.ShapeCount; s++)
        {
            int inside = 0;
            for (int i = 0; i <= 40; i++)
                for (int j = 0; j <= 40; j++)
                    if (Shapes.Inside(s, -1f + i * 0.05f, -1f + j * 0.05f)) inside++;
            double frac = inside / 1681.0;
            T.Check(inside > 0 && inside < 1681, "shape " + s + " has inside and outside points");
            T.Check(frac >= 0.12 && frac <= 0.85, "shape " + s + " area fraction " + frac.ToString("F2"));
        }
    }

    static void ShapeSchedule()
    {
        var seen = new HashSet<int>();
        for (int n = 1; n <= 64; n++)
        {
            int s = LevelGen.ShapeOf(n);
            T.Check(s >= 0 && s < Rules.ShapeCount, "level " + n + " shape in range");
            seen.Add(s);
        }
        T.Check(seen.Count == Rules.ShapeCount, "levels 1-64 use all 16 shapes");
        for (int c = 0; c < 4; c++)
        {
            var cyc = new HashSet<int>();
            for (int p = 1; p <= 16; p++) cyc.Add(LevelGen.ShapeOf(c * 16 + p));
            T.Check(cyc.Count == 16, "cycle " + c + " is a permutation");
        }
        // ponytail: brief asked for no repeat in any 16-window; impossible with reshuffled cycles
        // (it forces identical permutations), so the guarantee is a 8-level window across seams.
        for (int n = 1; n + 7 <= 300; n++)
        {
            var w = new HashSet<int>();
            for (int k = 0; k < 8; k++) w.Add(LevelGen.ShapeOf(n + k));
            T.Check(w.Count == 8, "no shape repeats within 8 levels from " + n);
        }
        var styles = new HashSet<Layout.Style>();
        for (int n = 1; n <= 30; n++) styles.Add(LevelGen.StyleOf(n));
        T.Check(styles.Count == 3, "all three cover styles used over levels 1-30");
    }

    static void StyleLayouts()
    {
        foreach (Layout.Style st in new[] { Layout.Style.OffsetGrid, Layout.Style.Concentric, Layout.Style.Banded })
            for (int shape = 0; shape < Rules.ShapeCount; shape++)
                foreach (int layers in new[] { 2, 4 })
                {
                    float radius;
                    var pts = Layout.Build(shape, st, layers, 60, new Random(shape * 31 + layers), out radius);
                    string tag = st + "/shape" + shape + "/L" + layers;
                    T.Check(pts.Count == 60, tag + " returns exactly count points, got " + pts.Count);
                    var distinct = new HashSet<int>();
                    foreach (var p in pts)
                    {
                        T.Check(Shapes.Inside(shape, p.X / radius, p.Y / radius), tag + " point inside shape");
                        T.Check(p.Layer >= 0 && p.Layer < layers, tag + " layer in range");
                        distinct.Add(p.Layer);
                    }
                    T.Check(distinct.Count >= 2, tag + " uses >= 2 layers");
                }
    }

    static void StyleStructure()
    {
        for (int shape = 0; shape < Rules.ShapeCount; shape++)
        {
            float radius;
            var og = Layout.Build(shape, Layout.Style.OffsetGrid, 4, 90, new Random(shape + 1), out radius);
            foreach (var p in og)
            {
                double cell = (p.X - (p.Layer % 2) * Layout.Spacing / 2f) / Layout.Spacing;
                T.Check(Math.Abs(cell - Math.Round(cell)) < 1e-3, "OffsetGrid shape" + shape + " layer " + p.Layer + " sits on its lattice (odd layers half-offset)");
            }

            var bd = Layout.Build(shape, Layout.Style.Banded, 4, 90, new Random(shape + 1), out radius);
            foreach (var p in bd)
                T.Check(p.Layer == Layout.BandLayer(p.X, radius, 4), "Banded shape" + shape + " layer follows the x stripe");

            var cc = Layout.Build(shape, Layout.Style.Concentric, 3, 90, new Random(shape + 1), out radius);
            // the ring shape has no centre, so compare the lowest and highest layers actually present
            int lo = 99, hi = -1;
            foreach (var p in cc) { lo = Math.Min(lo, p.Layer); hi = Math.Max(hi, p.Layer); }
            double rLow = 0, rTop = 0; int nLow = 0, nTop = 0;
            foreach (var p in cc)
            {
                double r = Math.Sqrt(p.X * p.X + p.Y * p.Y);
                if (p.Layer == lo) { rLow += r; nLow++; } else if (p.Layer == hi) { rTop += r; nTop++; }
            }
            T.Check(hi > lo && nLow > 0 && nTop > 0 && rLow / nLow > rTop / nTop, "Concentric shape" + shape + " outer ring is layer 0, centre is top");
        }
    }

    static void Determinism()
    {
        var a = Layout.Build(3, Layout.Style.Concentric, 3, 60, new Random(7));
        var b = Layout.Build(3, Layout.Style.Concentric, 3, 60, new Random(7));
        bool same = a.Count == b.Count;
        for (int i = 0; same && i < a.Count; i++) same = a[i] == b[i];
        T.Check(same, "Layout.Build is deterministic for a seed");
        foreach (int n in new[] { 3, 8, 15, 40 })
        {
            var p = LevelGen.Generate(n);
            var q = LevelGen.Generate(n);
            bool eq = p.Candies.Length == q.Candies.Length;
            for (int i = 0; eq && i < p.Candies.Length; i++)
                eq = p.Candies[i].X == q.Candies[i].X && p.Candies[i].Y == q.Candies[i].Y
                    && p.Candies[i].Layer == q.Candies[i].Layer && p.Candies[i].Color == q.Candies[i].Color;
            T.Check(eq, "Generate(" + n + ") is deterministic");
        }
    }

    static void LayerRule()
    {
        // min(2 + n/12 + tier extra, 6), Hard +1, VeryHard +2
        int[] ns = { 1, 8, 11, 15, 24, 30, 60, 100 };
        int[] want = { 2, 3, 2, 5, 5, 6, 6, 6 };
        for (int i = 0; i < ns.Length; i++)
            T.Check(LevelGen.LayersOf(ns[i]) == want[i], "layers of level " + ns[i] + " = " + LevelGen.LayersOf(ns[i]));
    }

    static int NormalCurve(int n) { return Math.Min(54 + (n - 1) * 2, 297) / 3 * 3; }

    static void CountsTiersScores()
    {
        var cache = new Dictionary<int, LevelData>();
        Func<int, LevelData> gen = n => { if (!cache.ContainsKey(n)) cache[n] = LevelGen.Generate(n); return cache[n]; };

        for (int n = 1; n <= 60; n++)
        {
            int c = gen(n).Candies.Length;
            T.Check(c % 3 == 0 && c >= 54 && c <= 297, "level " + n + " count " + c);
            var d = LevelGen.DifficultyOf(n);
            if (d != Difficulty.Normal) T.Check(c >= NormalCurve(n), "level " + n + " tier count >= normal curve");
        }
        foreach (int n in new[] { 8, 16, 24 })
            T.Check(gen(n).Candies.Length > NormalCurve(n), "Hard level " + n + " has more candies than the normal curve");
        foreach (int n in new[] { 15, 30 })
            T.Check(gen(n).Candies.Length > NormalCurve(n), "VeryHard level " + n + " has more candies than the normal curve");
        T.Check(gen(30).Candies.Length > (int)(NormalCurve(30) * 1.08) / 3 * 3, "VeryHard 30 exceeds the Hard scale");

        int nor = 0, hard = 0, vh = 0;
        for (int n = 1; n <= 300; n++)
        {
            var d = LevelGen.DifficultyOf(n);
            if (d == Difficulty.Normal) nor++; else if (d == Difficulty.Hard) hard++; else vh++;
        }
        T.Check(nor >= 225 && nor <= 255, "normal share " + nor + "/300");
        T.Check(hard >= 30 && hard <= 48, "hard share " + hard + "/300");
        T.Check(vh >= 12 && vh <= 27, "very hard share " + vh + "/300");

        double sN = 0, sH = 0, sV = 0; int cN = 0, cH = 0, cV = 0;
        for (int n = 15; n <= 120; n++)
        {
            var d = LevelGen.DifficultyOf(n);
            double s = LevelScore.Of(gen(n));
            if (d == Difficulty.Normal) { sN += s; cN++; }
            else if (d == Difficulty.Hard) { sH += s; cH++; }
            else { sV += s; cV++; }
        }
        sN /= cN; sH /= cH; sV /= cV;
        Console.WriteLine("mean score 15-120: normal " + sN.ToString("F0") + " hard " + sH.ToString("F0") + " veryhard " + sV.ToString("F0"));
        T.Check(sV > sN, "VeryHard mean score above Normal");
        T.Check(sH > sN, "Hard mean score above Normal");
        // the score counts 5 per candy covered at start
        var cov = new LevelData { Number = 1, Diff = Difficulty.Normal, Rows = new[] { new ProgressRow(100, new[] { 1 }) },
            Candies = new[] { new CandySpec(0, 0, 0, 0), new CandySpec(0.3f, 0, 1, 0), new CandySpec(9, 9, 0, 0) } };
        T.Check(LevelScore.Of(cov) == 5, "one covered candy scores 5");
    }
}
