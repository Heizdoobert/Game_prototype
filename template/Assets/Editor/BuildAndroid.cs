using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Proto.EditorTools
{
    // Batchmode: Unity -batchmode -quit -projectPath . -executeMethod Proto.EditorTools.BuildAndroid.Build
    public static class BuildAndroid
    {
        const string ScenePath = "Assets/Scenes/Main.unity";
        const string OutPath = "Builds/game.apk";

        [System.Serializable] public sealed class BuildCfg { public string product = "Proto"; public string appId = "com.proto.game"; }

        static BuildCfg Cfg()
        {
            var c = new BuildCfg();
            try { if (File.Exists("build.json")) JsonUtility.FromJsonOverwrite(File.ReadAllText("build.json"), c); }
            catch (System.Exception e) { Debug.LogWarning("build.json ignored, using defaults: " + e.Message); c = new BuildCfg(); }
            return c;
        }

        // Optional: point Unity at an existing SDK/NDK/JDK via env vars (reflection: the Android module may be absent).
        static void UseExternalTools()
        {
            var t = System.Type.GetType("UnityEditor.Android.AndroidExternalToolsSettings, UnityEditor.Android.Extensions");
            if (t == null) return;
            foreach (var (prop, env) in new[] { ("sdkRootPath", "ANDROID_SDK_ROOT"), ("ndkRootPath", "ANDROID_NDK_ROOT"), ("jdkRootPath", "JAVA_HOME") })
            {
                var v = System.Environment.GetEnvironmentVariable(env);
                if (!string.IsNullOrEmpty(v)) t.GetProperty(prop)?.SetValue(null, v);
            }
        }

        public static void Build()
        {
            UseExternalTools();
            Directory.CreateDirectory("Assets/Scenes");
            Directory.CreateDirectory("Builds");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);

            PlayerSettings.companyName = "Proto";
            var cfg = Cfg();
            PlayerSettings.productName = cfg.product;
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, cfg.appId);
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;
            PlayerSettings.SetManagedStrippingLevel(NamedBuildTarget.Android, ManagedStrippingLevel.Low);
            EditorUserBuildSettings.buildAppBundle = false;
            EditorUserBuildSettings.development = true; // device log + Profiler hooks while we playtest

            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = OutPath,
                target = BuildTarget.Android,
                options = BuildOptions.Development,
            });
            Debug.Log("BUILD RESULT: " + report.summary.result + " errors=" + report.summary.totalErrors + " size=" + report.summary.totalSize);
            EditorApplication.Exit(report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded ? 0 : 1);
        }
    }
}
