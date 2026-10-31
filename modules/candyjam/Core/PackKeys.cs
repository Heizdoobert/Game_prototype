using System.Collections.Generic;

namespace CandyJam.Core
{
    public enum Sfx { Tap, Jar, Win, Lose, Booster }

    // the file names an asset pack may carry (Resources/CandyJam/pack/<name>.png|.wav); every one is optional
    public static class PackKeys
    {
        public const string Candy = "candy";           // one sprite for all colours, tinted by the palette
        public const string Jar = "jar";
        public const string Slot = "slot";             // tray slot
        public const string Background = "bg";

        public static string CandyColor(int color) { return "candy_" + color; }   // full-colour sprite for one colour, not tinted
        public static string SfxName(Sfx s) { return "sfx_" + s.ToString().ToLowerInvariant(); }

        public static IEnumerable<string> All()
        {
            yield return Candy; yield return Jar; yield return Slot; yield return Background;
            for (int c = 0; c < Rules.Palette; c++) yield return CandyColor(c);
            foreach (Sfx s in System.Enum.GetValues(typeof(Sfx))) yield return SfxName(s);
        }
    }
}
