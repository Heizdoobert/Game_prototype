using System.Collections.Generic;

namespace CandyJam.Core
{
    public readonly struct CandySpec
    {
        public readonly float X, Y;
        public readonly int Layer, Color;
        public CandySpec(float x, float y, int layer, int color) { X = x; Y = y; Layer = layer; Color = color; }
    }

    public sealed class Candy
    {
        public readonly int Id;
        public readonly float X, Y;
        public readonly int Layer, Color;
        public bool Removed;
        public Candy(int id, CandySpec s) { Id = id; X = s.X; Y = s.Y; Layer = s.Layer; Color = s.Color; }
        public Candy Clone() { return new Candy(Id, new CandySpec(X, Y, Layer, Color)) { Removed = Removed }; }
    }

    public sealed class Board
    {
        public readonly List<Candy> Candies = new List<Candy>();
        public int Remaining { get; private set; }
        // ids of the candies on a higher layer that overlap each candy; the layout never moves, so clones share it
        int[][] cover;

        Board() { }

        public Board Clone()
        {
            var b = new Board { Remaining = Remaining, cover = cover };
            foreach (var c in Candies) b.Candies.Add(c.Clone());
            return b;
        }

        // ponytail: O(n^2) once per board (<=300 candies); the solver's many clones reuse it
        public Board(CandySpec[] specs)
        {
            for (int i = 0; i < specs.Length; i++) Candies.Add(new Candy(i, specs[i]));
            Remaining = specs.Length;
            float lim = Rules.CoverDist * Rules.CoverDist;
            cover = new int[specs.Length][];
            var over = new List<int>();
            for (int i = 0; i < specs.Length; i++)
            {
                over.Clear();
                for (int j = 0; j < specs.Length; j++)
                {
                    if (specs[j].Layer <= specs[i].Layer) continue;
                    float dx = specs[j].X - specs[i].X, dy = specs[j].Y - specs[i].Y;
                    if (dx * dx + dy * dy < lim) over.Add(j);
                }
                cover[i] = over.ToArray();
            }
        }

        public bool IsFree(Candy c)
        {
            if (c.Removed) return false;
            foreach (int o in cover[c.Id]) if (!Candies[o].Removed) return false;
            return true;
        }

        public List<Candy> Free()
        {
            var r = new List<Candy>();
            foreach (var c in Candies) if (IsFree(c)) r.Add(c);
            return r;
        }

        // live candies per colour; pass Free() for the ones that can be tapped now
        public static int[] CountByColor(IEnumerable<Candy> candies)
        {
            var n = new int[Rules.Palette];
            foreach (var c in candies) if (!c.Removed) n[c.Color]++;
            return n;
        }

        public void Remove(Candy c)
        {
            if (c.Removed) return;
            c.Removed = true;
            Remaining--;
        }
    }
}
