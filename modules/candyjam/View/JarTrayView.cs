using CandyJam.Core;
using UnityEngine;

namespace CandyJam.View
{
    // jars along the top, tray along the bottom, all in world space
    public sealed class JarTrayView : MonoBehaviour
    {
        const float JarY = 6.4f, TrayY = -5.4f;

        SpriteRenderer[] jarFrame, jarFill, trayFrame, trayCandy;
        SpriteRenderer[][] pips;

        public Vector3 JarWorld(int s) { return new Vector3((s - 1.5f) * 2.3f, JarY, 0f); }
        public Vector3 TrayWorld(int t) { return new Vector3((t - 3f) * 1.25f, TrayY, 0f); }

        void Awake()
        {
            jarFrame = new SpriteRenderer[Rules.JarSlots];
            jarFill = new SpriteRenderer[Rules.JarSlots];
            pips = new SpriteRenderer[Rules.JarSlots][];
            for (int s = 0; s < Rules.JarSlots; s++)
            {
                jarFrame[s] = Make("jar", Sprites.Jar, JarWorld(s), 1f, -50);
                jarFill[s] = Make("fill", Sprites.Jar, JarWorld(s), 0.88f, -49);
                pips[s] = new SpriteRenderer[Rules.JarCapacity];
                for (int i = 0; i < Rules.JarCapacity; i++)
                    pips[s][i] = Make("pip", Sprites.Disc, JarWorld(s) + new Vector3((i - 1) * 0.6f, -0.1f, 0f), 0.5f, -48);
            }
            trayFrame = new SpriteRenderer[Rules.TrayMax];
            trayCandy = new SpriteRenderer[Rules.TrayMax];
            for (int t = 0; t < Rules.TrayMax; t++)
            {
                trayFrame[t] = Make("slot", Sprites.Slot, TrayWorld(t), 1f, -50);
                trayCandy[t] = Make("tc", Sprites.Disc, TrayWorld(t), 0.8f, -48);
            }
        }

        SpriteRenderer Make(string name, Sprite sprite, Vector3 pos, float scale, int order)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            go.transform.position = pos;
            go.transform.localScale = Vector3.one * scale;
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sortingOrder = order;
            return sr;
        }

        public void Refresh(Game g)
        {
            for (int s = 0; s < Rules.JarSlots; s++)
            {
                jarFrame[s].color = g.JarUnlocked[s] ? new Color(1f, 1f, 1f, 0.95f) : new Color(0.25f, 0.25f, 0.25f, 0.4f);
                var j = g.Jars[s];
                jarFill[s].enabled = j != null;
                for (int i = 0; i < Rules.JarCapacity; i++) pips[s][i].enabled = j != null && i < j.Count;
                if (j == null) continue;
                Color col = Palette.Candy[j.Color];
                jarFill[s].color = new Color(col.r, col.g, col.b, 0.5f);
                for (int i = 0; i < Rules.JarCapacity; i++) pips[s][i].color = col;
            }
            for (int t = 0; t < Rules.TrayMax; t++)
            {
                bool open = t < g.TraySlots;
                trayFrame[t].enabled = open;
                bool has = open && g.Tray[t] >= 0;
                trayCandy[t].enabled = has;
                if (has) trayCandy[t].color = Palette.Candy[g.Tray[t]];
            }
        }
    }
}
