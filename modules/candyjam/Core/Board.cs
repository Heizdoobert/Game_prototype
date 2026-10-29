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

        Board() { }

        public Board Clone()
        {
            var b = new Board { Remaining = Remaining };
            foreach (var c in Candies) b.Candies.Add(c.Clone());
            return b;
        }

        public Board(CandySpec[] specs)
        {
            for (int i = 0; i < specs.Length; i++) Candies.Add(new Candy(i, specs[i]));
            Remaining = specs.Length;
        }

        // ponytail: O(n^2) over a full level (<=300 candies); add a grid if profiling says so
        public bool IsFree(Candy c)
        {
            if (c.Removed) return false;
            float lim = Rules.CoverDist * Rules.CoverDist;
            foreach (var o in Candies)
            {
                if (o.Removed || o.Layer <= c.Layer) continue;
                float dx = o.X - c.X, dy = o.Y - c.Y;
                if (dx * dx + dy * dy < lim) return false;
            }
            return true;
        }

        public List<Candy> Free()
        {
            var r = new List<Candy>();
            foreach (var c in Candies) if (IsFree(c)) r.Add(c);
            return r;
        }

        public void Remove(Candy c)
        {
            if (c.Removed) return;
            c.Removed = true;
            Remaining--;
        }
    }
}
