using System;

namespace CandyJam.Core
{
    // unit-box silhouettes: u,v in [-1,1]; 0-4 are the original five, 5-15 added [tuned]
    public static class Shapes
    {
        public static bool Inside(int shape, float u, float v)
        {
            float r = (float)Math.Sqrt(u * u + v * v);
            float au = Math.Abs(u), av = Math.Abs(v);
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
                case 4: return au + av <= 1f; // diamond
                case 5: return (au <= 0.35f) || (av <= 0.35f); // cross
                case 6: return r <= 1f && Dist(u, v, 0.45f, 0.2f) > 0.8f; // crescent
                case 7: return r <= 0.55f + 0.35f * Math.Abs((float)Math.Cos(3.0 * Math.Atan2(v, u))); // flower
                case 8: return Dist(u, v, 0f, -0.3f) <= 0.65f || (v >= -0.1f && v <= 1f && au <= 0.6f * (1f - v) / 1.1f); // droplet
                case 9: return av <= 0.866f && 0.866f * au + 0.5f * av <= 0.866f; // hexagon
                case 10: return (au <= 0.7f && v >= -0.9f && v <= 0.2f) || (v > 0.2f && v <= 1f && au <= (1f - v) / 0.8f); // house
                case 11: // fish: ellipse body plus tail
                {
                    float e = (u + 0.2f) / 0.75f, f = v / 0.5f;
                    return e * e + f * f <= 1f || (u >= 0.5f && av <= 1.4f * (u - 0.5f));
                }
                case 12: // cat head: disc plus two ears
                    return Dist(u, v, 0f, -0.1f) <= 0.8f || (v >= 0.3f && v <= 1f && Math.Abs(au - 0.5f) <= 0.3f * (1f - v) / 0.7f);
                case 13: return (v >= -0.1f && r <= 1f) || (au <= 0.35f && v >= -1f && v < -0.1f); // mushroom
                case 14: return (v >= 0.1f && v <= 1f && au <= (1f - v) / 0.9f) || (au <= 0.28f && v >= -1f && v < 0.1f); // arrow
                default: // ghost: half-disc head, wavy-bottomed body
                    return (v >= 0f && r <= 0.8f) || (au <= 0.8f && v < 0f && v >= -0.75f + 0.15f * (float)Math.Sin(8.0 * u));
            }
        }

        static float Dist(float u, float v, float cx, float cy)
        {
            float dx = u - cx, dy = v - cy;
            return (float)Math.Sqrt(dx * dx + dy * dy);
        }
    }
}
