# apk2proto

Turns a Unity APK into a playable Android prototype with new, procedural art. The pipeline reverse-engineers the build into a compact `spec.json`, an agent authors a small game module from it, and a Unity project template plus that module is built into `game.apk`. Design: [`../docs/specs/2026-10-29-apk2proto-design.md`](../docs/specs/2026-10-29-apk2proto-design.md).

Intended use is learning, QA and internal prototypes. Shipping the output is a separate decision about the source game's rights.

## Prerequisites

Linux only: the runner uses `fcntl` locks, `/proc/meminfo`, `~/Unity/Hub/Editor` and `/usr/lib/jvm`.


Stdlib-only Python 3, the game RE kit (`GRE_KIT`, default `/mnt/second_drive/Ghost_melon/game_re_kit`), and for the build: Unity 6000.6.7f1 with Android support, Android SDK (`cmdline-tools` holding only `16.0`), NDK 27.2.12479018, JDK 17, dotnet 8, adb.

```
python3 -m apk2proto doctor     # prints ok / MISS with a fix hint per item; exit 1 on any MISS
```

## Usage

```
python3 -m apk2proto run GAME.apk WORKDIR [--module DIR] [--from STAGE] [--only STAGE] [--force]
```

Stages: `detect, dump, distill, author, scaffold, test, verify, build, install`. Unchanged stages are skipped. Exit codes: 0 done, 1 a stage failed (cause printed), 3 authoring is due: write the module (see below) and re-run the same command. `build` needs 3500 MB free RAM; `install` needs an adb device (set `ANDROID_SERIAL=<id>` when several devices are connected).

Outputs in `WORKDIR`: `spec.json` + `spec_index.md` (what the agent reads), `module/` (what the agent writes), `proto/` (the Unity project), `build.log`, `proto/Builds/game.apk`.

## Module shape

The contract is the XML docs in [`template/Assets/Scripts/Shell/View/IGameModule.cs`](template/Assets/Scripts/Shell/View/IGameModule.cs); [`modules/candyjam/`](modules/candyjam) is the worked example.

```
module/
  module.json          {"id": "candyjam", "name": "Candy Jam"}   id = lowercase letters/digits
  Core/*.cs            pure C#, no UnityEngine
  View/GameModule.cs   the one IGameModule ([UnityEngine.Scripting.Preserve]) + board view + IPlay
  Tests/*Tests.cs      public static void Run() using T.Check
```

`WORKDIR/rules.md` (next to `spec.json`): every rule tagged [C]/[A]/[S]/[?]. `WORKDIR/hints.json` (optional, before `distill`): `{"keywords": ["extra", "words"]}` widens the class/enum filter. Test classes must be named `*Tests` with `public static void Run()` (any file name). Hearts, coins and revive come from `IGameModule.Config`; `modules/candyjam/View/Sprites.cs` and `Palette.cs` are reusable procedural-art examples.

Art is procedural; extracted textures, meshes and audio are never read or copied, and `verify` fails the run if a project file matches an original asset or contains a possible secret. `raw/`, `apk/`, `il2cpp/` and `assets_dump/` can hold passwords and SDK keys: do not share them.

## Install the skill (run this yourself)

```
ln -s /mnt/second_drive/Knit2D/apk2proto/skill/apk2proto ~/.claude/skills/apk2proto
```

## Tests

```
python3 -W error::ResourceWarning -m unittest discover -s tests
```

## Measured (estimates)

Golden run on Knit Away 3.3.12 (`app.apk`), 2026-10-29, existing dumps reused (`detect`/`dump` skipped), `--module modules/candyjam`, no device attached. The runner prints no timings: these are rough wall-clock estimates from that session, not benchmarks.

| stage | approx. wall-clock |
|---|---|
| distill | 0.8 s |
| scaffold | 0.5 s |
| test (dotnet harness, ALL PASS) | 3.9 s |
| verify | 16 s |
| build (Unity batchmode, cold Library) | about 2 min |
| install | ran and failed: no device attached (needs a connected device) |

- `spec.json`: 75.8 KB on disk (limit 100 KB), 492 classes kept of 2656 types, 13 enums, `trimmed: true`, `over_limit: false`, 0 config assets, 1 Odin asset (values not decoded), levels = asset overview only.
- Build: `BUILD RESULT: Succeeded`, `proto/Builds/game.apk` 24.7 MB.
- The dump stage (not re-run here, done once in the first build) is the dominant cost for a new APK; authoring the module is manual and not included.
- Stage keys use file mtimes: re-scaffolding the same module touches mtimes and triggers a rebuild.

## Accepted differences from the hand-made Candy Jam

The generated prototype is not a byte-for-byte port of the hand-made `CandyJam`:

- UI strings differ (for example "You lost").
- The save key is `proto.profile`.
- The booster inventory is padded with 3 of each booster.
- Revive pays only after a successful revive.
