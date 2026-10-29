using System.Collections.Generic;
using CandyJam.Core;
using UnityEngine;

namespace CandyJam.View
{
    public sealed class BoardView : MonoBehaviour
    {
        readonly Dictionary<Candy, SpriteRenderer> views = new Dictionary<Candy, SpriteRenderer>();
        Game game;
        public float Scale { get; private set; } = 1f;

        public void Build(Game g, Vector2 center, float maxW, float maxH)
        {
            Clear();
            game = g;
            float minX = float.MaxValue, minY = float.MaxValue, maxX = float.MinValue, maxY = float.MinValue;
            foreach (var c in g.Board.Candies)
            {
                minX = Mathf.Min(minX, c.X); maxX = Mathf.Max(maxX, c.X);
                minY = Mathf.Min(minY, c.Y); maxY = Mathf.Max(maxY, c.Y);
            }
            float w = maxX - minX + 1f, h = maxY - minY + 1f;
            Scale = Mathf.Min(1f, Mathf.Min(maxW / w, maxH / h));
            var mid = new Vector2((minX + maxX) / 2f, (minY + maxY) / 2f);
            foreach (var c in g.Board.Candies)
            {
                var go = new GameObject("candy");
                go.transform.SetParent(transform, false);
                go.transform.position = center + (new Vector2(c.X, c.Y) - mid) * Scale;
                go.transform.localScale = Vector3.one * Scale;
                var sr = go.AddComponent<SpriteRenderer>();
                sr.sprite = Sprites.Disc;
                sr.sortingOrder = c.Layer * 10;
                views[c] = sr;
            }
            Refresh();
        }

        public void Clear()
        {
            foreach (var kv in views) if (kv.Value != null) Destroy(kv.Value.gameObject);
            views.Clear();
        }

        // hide removed candies, dim blocked ones
        public void Refresh()
        {
            foreach (var kv in views)
            {
                var c = kv.Key;
                var sr = kv.Value;
                sr.enabled = !c.Removed;
                if (c.Removed) continue;
                Color col = Palette.Candy[c.Color];
                if (!game.Board.IsFree(c)) col *= 0.45f;
                col.a = 1f;
                sr.color = col;
            }
        }

        // topmost live candy under the point (blocked ones too; the game rejects them)
        public Candy Hit(Vector2 world)
        {
            Candy best = null;
            float reach = Rules.CandyRadius * Scale;
            foreach (var kv in views)
            {
                var c = kv.Key;
                if (c.Removed) continue;
                if (((Vector2)kv.Value.transform.position - world).magnitude > reach) continue;
                if (best == null || c.Layer > best.Layer) best = c;
            }
            return best;
        }

        // Needle: any live candy near the point, covered ones included; nearest centre wins so a candy under another stays pickable
        public Candy HitAny(Vector2 world)
        {
            Candy best = null;
            float bestD = float.MaxValue, reach = Rules.CandyRadius * Scale;
            foreach (var kv in views)
            {
                var c = kv.Key;
                if (c.Removed) continue;
                float d = ((Vector2)kv.Value.transform.position - world).magnitude;
                if (d > reach) continue;
                if (best == null || d < bestD - 1e-4f || (d <= bestD + 1e-4f && c.Layer > best.Layer)) { best = c; bestD = d; }
            }
            return best;
        }

        public Vector3 PosOf(Candy c) { return views[c].transform.position; }
    }
}
