---
name: apk2proto
description: Turn a Unity APK into a playable Android prototype with new procedural art; use when the user hands over an APK and wants a quick prototype/clone, or resumes an apk2proto workdir
---

# apk2proto

Pipeline: `detect, dump, distill, author, scaffold, test, verify, build, install`. The runner does everything except `author`, which is yours.
Repo: `/mnt/second_drive/Knit2D/apk2proto` (run every command from there). Design: `/mnt/second_drive/Knit2D/docs/specs/2026-10-29-apk2proto-design.md`.

Answer the user in the user's language (this user speaks Vietnamese). This file and all code/comments stay English.

## Steps

1. `python3 -m apk2proto doctor`. Any `MISS` line: stop, show it (with its fix hint) to the user. `adb` MISS only blocks `install`.
2. `python3 -m apk2proto run GAME.apk WORKDIR` (add `--module DIR` to use an existing module instead of `WORKDIR/module`).
   - Stages that already ran on unchanged inputs print `skip`; the dump is the slow part and is reused.
   - Flags: `--from STAGE` (start there), `--only STAGE` (run just that one, ignoring skip), `--force` (ignore skip for every stage).
   - Exit 0 = all stages passed. Exit 1 = a stage failed; the printed cause (dotnet test, verify problems, build log tail, adb) is the thing to fix. Exit 3 = authoring is due (step 3). Non-Unity engines are refused at `detect`.
   - `build` refuses to start Unity when MemAvailable < 3500 MB: tell the user to free RAM, do not work around it. `install` needs a connected device.
3. Authoring (exit 3). Read `WORKDIR/spec.json`, **check `coverage` first and tell the user what is thin**:
   - `coverage.notes` lists what distill skipped or could not read; `trimmed: true` / `over_limit: true` mean the spec was cut to fit its size limit, so some classes/members are missing.
   - Odin-serialized config values are NOT decoded (`odin_assets` counts them): their numbers (balance, rewards, level layouts) are unknown. Mark such rules [?] or [A], never invent values as if known.
   Then read `WORKDIR/spec_index.md`. Dig into the dump only for the 2-3 methods that carry a rule: kit `bin/fn.py 'Class$$Method' DIR -n 120` and `bin/xref.py -f Class field` (kit at `$GRE_KIT`, default `/mnt/second_drive/Ghost_melon/game_re_kit`). Never `cat` a decompiled `.c` file.
   Write `WORKDIR/module/` in the shape of `modules/candyjam/` (the worked example):
   - `module.json` `{"id": "...", "name": "..."}`; id is lowercase letters/digits only.
   - `Core/` pure C#, no `UnityEngine` (it is tested headless by `dotnet`).
   - `View/GameModule.cs`: the `IGameModule` implementation, plus the board view and an `IPlay`.
   - `Tests/*Tests.cs`, each with `public static void Run()` using `T.Check`.
   - Write `WORKDIR/rules.md`: every rule tagged [C] confirmed in code, [A] assumed/typical for the genre, [S] seen in strings/config names only, [?] unknown. Tags first, then the rule text.
4. Re-run the same `run` command. It resumes at `author` (passes once `View/GameModule.cs` exists), then scaffold, test, verify, build, install. Fix the printed cause and re-run; use `--from STAGE` to skip ahead.
5. Hard rules:
   - Do not print, quote or share contents of `apk/`, `il2cpp/`, `assets_dump/`, `raw/` (they hold passwords and SDK keys). Describe, never paste.
   - One heavy process at a time (dotnet build, Unity, Ghidra); `/tmp` is RAM. Never `pkill -f`/`pgrep -f` a pattern in your own command line.
   - Never weaken `verify` or the module tests to get green.

## Module contract

The contract is the XML doc comments in `template/Assets/Scripts/Shell/View/IGameModule.cs` (`IGameModule`, `IPlay`, `LevelInfo`, `BoosterDef`, `PlayStatus`). Read that file before writing a module; `modules/candyjam/` is a complete example (Core rules, tests, `GameModule.cs`, `PlayController.cs`).

Rules for module authoring:
- Exactly one `IGameModule` implementation in the project, marked `[UnityEngine.Scripting.Preserve]`, parameterless constructor (the shell finds it by reflection).
- `module.json` id = lowercase letters and digits only.
- `Core/` is pure C# (LangVersion 9) with no `UnityEngine`; Unity-facing code lives in `View/`.
- Art is procedural only (sprites generated in code). Never read, load, convert or copy extracted textures, meshes or audio. `verify` hashes every file in the APK's `assets/` and `res/` and fails the stage if any project file is byte-identical to one.
- Never copy original game code or assets into the module; re-express rules in new code.
- Tag every rule in `rules.md` with [C]/[A]/[S]/[?] and write nothing the spec does not support without tagging it [A].
- `verify` also fails with `possible secret in <file>:<line>` when the kit's redact check would change a `.cs`/`.json` line in the project (e.g. an identifier or string that looks like a key/token/password assignment) or `spec.json`; fix by renaming/removing the offender, not by editing verify.
