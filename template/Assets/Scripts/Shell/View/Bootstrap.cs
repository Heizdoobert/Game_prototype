using UnityEngine;

namespace Proto.Shell
{
    public static class Bootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Init()
        {
            if (Object.FindAnyObjectByType<App>() != null) return;
            new GameObject("App").AddComponent<App>();
        }
    }
}
