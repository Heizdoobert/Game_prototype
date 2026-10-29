using UnityEngine;

namespace Proto.Shell
{
    public static class Bootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Init()
        {
            if (Object.FindFirstObjectByType<App>() != null) return;
            new GameObject("App").AddComponent<App>();
        }
    }
}
