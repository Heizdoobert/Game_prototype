using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Proto.Shell
{
    // uGUI built in code (no prefabs); Canvas reference size 1080x1920
    public static class Ui
    {
        static Font font;

        public static Font Font
        {
            get
            {
                if (font == null) font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                return font;
            }
        }

        public static void EventSystem()
        {
            if (UnityEngine.EventSystems.EventSystem.current != null) return;
            new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        }

        public static Canvas Canvas()
        {
            var go = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var c = go.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            var s = go.GetComponent<CanvasScaler>();
            s.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            s.referenceResolution = new Vector2(1080, 1920);
            s.matchWidthOrHeight = 0.5f;
            return c;
        }

        public static RectTransform Rect(Transform parent, string name, Vector2 aMin, Vector2 aMax)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var r = go.GetComponent<RectTransform>();
            r.SetParent(parent, false);
            r.anchorMin = aMin; r.anchorMax = aMax;
            r.offsetMin = Vector2.zero; r.offsetMax = Vector2.zero;
            return r;
        }

        public static RectTransform Panel(Transform parent, string name, Color color)
        {
            var r = Rect(parent, name, Vector2.zero, Vector2.one);
            r.gameObject.AddComponent<Image>().color = color;
            return r;
        }

        public static Text Label(Transform parent, string text, int size, TextAnchor anchor, Vector2 aMin, Vector2 aMax)
        {
            var r = Rect(parent, "label", aMin, aMax);
            var t = r.gameObject.AddComponent<Text>();
            t.font = Font; t.text = text; t.fontSize = size; t.alignment = anchor;
            t.color = new Color(0.2f, 0.12f, 0.1f);
            t.raycastTarget = false;
            return t;
        }

        public static Button Button(Transform parent, string text, Vector2 aMin, Vector2 aMax, UnityAction onClick, Color color)
        {
            var r = Rect(parent, "button", aMin, aMax);
            r.gameObject.AddComponent<Image>().color = color;
            var b = r.gameObject.AddComponent<Button>();
            b.onClick.AddListener(onClick);
            var t = Label(r, text, 38, TextAnchor.MiddleCenter, Vector2.zero, Vector2.one);
            t.color = Color.white;
            return b;
        }
    }
}
