using UnityEngine;

namespace CandyJam.View
{
    public static class Palette
    {
        public static readonly Color[] Candy =
        {
            Hex("E53935"), Hex("FB8C00"), Hex("FDD835"), Hex("7CB342"), Hex("00897B"), Hex("00ACC1"),
            Hex("1E88E5"), Hex("3949AB"), Hex("8E24AA"), Hex("EC407A"), Hex("6D4C41"), Hex("90A4AE"),
        };

        static Color Hex(string h)
        {
            ColorUtility.TryParseHtmlString("#" + h, out var c);
            return c;
        }
    }
}
