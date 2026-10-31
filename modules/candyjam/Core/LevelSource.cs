using System;
using System.Collections.Generic;
using System.Globalization;

namespace CandyJam.Core
{
    // gate: where a level comes from. The game asks for level n and never knows whether it was generated or drawn by hand.
    public interface ILevelSource { LevelData Get(int number); }

    public sealed class GeneratedLevels : ILevelSource
    {
        public LevelData Get(int number) { return LevelGen.Generate(number); }
    }

    // Hand-made levels as text, one file per level number; a level without a file comes from the fallback source.
    //   # comment
    //   diff Hard            optional: Normal (default), Hard, VeryHard (sets coin reward and jar-colour weights)
    //   x y layer color      one line per candy; layer 0 is lowest, color 0-11, every colour a multiple of 3 candies
    // The file does not promise the level is winnable: check it with Solver.Solve.
    public sealed class AuthoredLevels : ILevelSource
    {
        readonly Func<int, string> read;
        readonly ILevelSource fallback;

        public AuthoredLevels(Func<int, string> read, ILevelSource fallback) { this.read = read; this.fallback = fallback; }

        public LevelData Get(int number)
        {
            var text = read(number);
            return text == null ? fallback.Get(number) : Parse(number, text);
        }

        public static LevelData Parse(int number, string text)
        {
            var diff = Difficulty.Normal;
            var specs = new List<CandySpec>();
            var lines = text.Split('\n');
            for (int i = 0; i < lines.Length; i++)
            {
                var line = lines[i].Trim();
                if (line.Length == 0 || line[0] == '#') continue;
                var p = line.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                if (p[0] == "diff" && p.Length == 2)
                {
                    if (!Enum.TryParse(p[1], out diff)) throw Bad(number, i, "unknown difficulty '" + p[1] + "'");
                    continue;
                }
                var f = CultureInfo.InvariantCulture;
                if (p.Length != 4 || !float.TryParse(p[0], NumberStyles.Float, f, out var x) || !float.TryParse(p[1], NumberStyles.Float, f, out var y)
                    || !int.TryParse(p[2], out var layer) || !int.TryParse(p[3], out var color))
                    throw Bad(number, i, "expected 'x y layer color'");
                if (layer < 0) throw Bad(number, i, "layer must be >= 0");
                if (color < 0 || color >= Rules.Palette) throw Bad(number, i, "colour must be 0-" + (Rules.Palette - 1));
                specs.Add(new CandySpec(x, y, layer, color));
            }
            var count = new int[Rules.Palette];
            foreach (var s in specs) count[s.Color]++;
            for (int c = 0; c < count.Length; c++)
                if (count[c] % Rules.JarCapacity != 0) throw new FormatException("level " + number + ": colour " + c + " has " + count[c] + " candies, needs a multiple of " + Rules.JarCapacity);
            if (specs.Count == 0) throw new FormatException("level " + number + ": no candies");
            return new LevelData { Number = number, Diff = diff, Candies = specs.ToArray(), Rows = LevelGen.RowsFor(diff) };
        }

        static FormatException Bad(int number, int line, string why) { return new FormatException("level " + number + " line " + (line + 1) + ": " + why); }
    }
}
