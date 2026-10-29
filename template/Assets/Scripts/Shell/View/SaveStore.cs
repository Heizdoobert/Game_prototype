using UnityEngine;

namespace Proto.Shell
{
    public static class SaveStore
    {
        const string Key = "proto.profile";

        public static Profile Load(int[] startCounts)
        {
            var p = new Profile();
            try
            {
                string json = PlayerPrefs.GetString(Key, "");
                if (!string.IsNullOrEmpty(json)) JsonUtility.FromJsonOverwrite(json, p);
            }
            catch (System.Exception) { p = new Profile(); }
            Sanitise(p, startCounts);
            return p;
        }

        // a hand-edited / corrupt save must never break the app shell
        static void Sanitise(Profile p, int[] start)
        {
            p.PadBoosters(start);
            p.Hearts = Mathf.Clamp(p.Hearts, 0, Profile.Cfg.MaxHearts);
            if (p.Level < 1) p.Level = 1;
            if (p.Coins < 0) p.Coins = 0;
            if (p.Hearts < Profile.Cfg.MaxHearts
                && (p.HeartRegenAtTicks <= 0 || p.HeartRegenAtTicks > System.DateTime.MaxValue.Ticks))
                p.HeartRegenAtTicks = System.DateTime.UtcNow.AddMinutes(Profile.Cfg.HeartRegenMinutes).Ticks;
        }

        public static void Save(Profile p)
        {
            PlayerPrefs.SetString(Key, JsonUtility.ToJson(p));
            PlayerPrefs.Save();
        }
    }
}
