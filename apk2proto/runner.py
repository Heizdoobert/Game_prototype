import argparse, json, os, subprocess
from collections import namedtuple
from . import distill as D, doctor as DR, paths, scaffold as S, verify as V
from .textutil import is_il2cpp
from .state import Workdir, fingerprint

Stage = namedtuple('Stage', 'name fn key exists')

class Paused(Exception): pass

# doctor.checks() names the Unity build needs (adb is only for install)
BUILD_CHECKS = ('Unity Editor', 'Unity Android module', 'cmdline-tools has only 16.0', 'NDK ' + DR.NDK, 'JDK 17 (JAVA_HOME or Unity bundled)')
DUMP_CHECKS = ('game_re_kit found',)             # detect and dump call the kit
MIN_MEM_MB = 3500

PAUSE_MSG = '''\
author: write the game module, then re-run the same command.
  read : {wd}/spec.json and {wd}/spec_index.md  (skill: apk2proto)
  contract: {contract}
  example : {example}  (a finished module)
  write: {module}/module.json, Core/*.cs, View/GameModule.cs, Tests/*Tests.cs
         {wd}/rules.md  (tagged [C]/[A]/[S]/[?], verify scans it for secret values)
'''

def sh(cmd, **kw):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)

def _module(wd, a): return a.module or wd.p('module')
def _kit(*p): return os.path.join(paths.KIT, 'bin', *p)

def _engine(path):
    """(first line, IL2CPP backend?) of the kit's engine.txt; ('', False) when unreadable."""
    try:
        with open(path) as fh: text = fh.read()
    except OSError: return '', False
    return text.split('\n')[0].strip(), is_il2cpp(text)

def _check_engine(engine_txt):
    first, il2cpp = _engine(engine_txt)
    if first != 'Unity': raise SystemExit('engine %r is not supported yet (other engines are separate specs)' % first)
    if not il2cpp: raise SystemExit('Unity Mono backend is not supported yet (no IL2CPP dump); other backends are separate specs')

def _need(names, what):
    bad = [(n, fix) for ok, n, fix in DR.checks() if not ok and n in names]
    if bad: raise SystemExit('%s prerequisites missing:\n' % what + '\n'.join('MISS %s -> %s' % b for b in bad))

def st_detect(wd, a):
    _need(DUMP_CHECKS, 'detect')
    sh([_kit('unpack.sh'), a.apk, wd.path])
    _check_engine(wd.p('engine.txt'))

def st_dump(wd, a):
    _need(DUMP_CHECKS, 'dump')
    cmd = [_kit('run_all.sh'), a.apk, wd.path, 'meta dump assets']
    print('+', ' '.join(cmd), flush=True)
    # the kit's run_all.sh can exit 1 after a good dump (trailing doctor|grep under pipefail): judge by the output only
    rc = subprocess.run(cmd, check=False).returncode
    if not os.path.isfile(wd.p('il2cpp', 'dump.cs')):
        raise SystemExit('dump produced no il2cpp/dump.cs (kit exit %s)' % rc)
def st_distill(wd, a): D.distill(wd.path)

def st_author(wd, a):
    m = _module(wd, a)
    # rules.md lives next to spec.json (skill and verify use WORKDIR/rules.md), not inside the module
    if not (os.path.isfile(os.path.join(m, 'View', 'GameModule.cs')) and os.path.isfile(wd.p('rules.md'))):
        print(PAUSE_MSG.format(wd=wd.path, module=m,
                               contract=os.path.join(paths.ROOT, 'template', 'Assets', 'Scripts', 'Shell', 'View', 'IGameModule.cs'),
                               example=os.path.join(paths.ROOT, 'modules', 'candyjam')))
        raise Paused()

def st_scaffold(wd, a): S.scaffold(wd.p('proto'), paths.TEMPLATE, _module(wd, a))
def st_test(wd, a): sh(['dotnet', 'run', '--project', wd.p('proto', 'Tests~', 'Core.Tests')])

def st_verify(wd, a):
    extra = [f for f in V._files(_module(wd, a), V.SKIP) if f.endswith(V.TEXT_EXT)]
    problems = V.verify(wd.p('proto'), wd.p('apk'), wd.p('spec.json'), assets_dump=wd.p('assets_dump'), extra_text_files=extra)
    if problems: raise SystemExit('verify failed:\n  ' + '\n  '.join(problems))

def _mem_available_mb():
    try:
        with open('/proc/meminfo') as fh:
            for line in fh:
                if line.startswith('MemAvailable:'): return int(line.split()[1]) // 1024
    except (OSError, ValueError): pass
    return None                                        # unknown (not Linux): do not block

ERR = ('error CS', 'Exception', 'BUILD RESULT', 'Build Failed', 'error:')

def _failure_lines(lines, errs=20, tail=5):
    """first `errs` lines that look like errors, then the last `tail` lines (no repeats); at most errs + tail lines"""
    hit = [i for i, l in enumerate(lines) if any(m in l for m in ERR)][:errs]
    return [lines[i] for i in sorted(set(hit) | set(range(max(0, len(lines) - tail), len(lines))))]

def st_build(wd, a):
    _need(BUILD_CHECKS, 'build')                       # adb is only for install
    mem = _mem_available_mb()
    if mem is not None and mem < MIN_MEM_MB:
        raise SystemExit('refusing to start Unity: MemAvailable %d MB < %d MB (free RAM first)' % (mem, MIN_MEM_MB))
    unity = paths.unity_editor()
    log = wd.p('build.log')
    if os.path.exists(log): os.remove(log)             # a stale "BUILD RESULT" must not satisfy this run
    subprocess.run([unity, '-batchmode', '-quit', '-nographics', '-projectPath', wd.p('proto'),
                    '-executeMethod', 'Proto.EditorTools.BuildAndroid.Build', '-logFile', log],
                   env=dict(os.environ, **DR.android_env()))
    ok = False
    if os.path.exists(log):
        with open(log, errors='replace') as fh: ok = 'BUILD RESULT: Succeeded' in fh.read()
    if not ok:
        if os.path.exists(log):
            with open(log, errors='replace') as fh: print(''.join(l if l.endswith('\n') else l + '\n' for l in _failure_lines(fh.readlines())), end='')
        raise SystemExit('build failed, see ' + log)

def st_install(wd, a):
    with open(wd.p('proto', 'build.json')) as fh: app_id = json.load(fh)['appId']
    sh(['adb', 'install', '-r', wd.p('proto', 'Builds', 'game.apk')])
    sh(['adb', 'shell', 'monkey', '-p', app_id, '-c', 'android.intent.category.LAUNCHER', '1'])

def _engine_is_unity(wd):
    first, il2cpp = _engine(wd.p('engine.txt'))
    return first == 'Unity' and il2cpp and os.path.isdir(wd.p('apk'))

def _cat(*digests): return ''.join(digests)

def _src(wd): return fingerprint(wd.p('proto', 'Assets', 'Scripts'), wd.p('proto', 'Tests~', 'Core.Tests', 'Game'), suffixes=('.cs',))

# Unity rewrites scenes and adds .meta files during a build, so test/verify/build keys hash only hand-written inputs
def _k_test(wd, a): return _src(wd) if os.path.isdir(wd.p('proto')) else None
def _k_verify(wd, a): return None      # safety gate (~16 s): never skip, module files can change under a stale key
def _k_build(wd, a):
    if not os.path.isfile(wd.p('proto', 'Builds', 'game.apk')): return None
    return _cat(fingerprint(wd.p('proto', 'Assets', 'Scripts'), wd.p('proto', 'Assets', 'Editor'), suffixes=('.cs',)),
                fingerprint(wd.p('proto', 'build.json'), wd.p('proto', 'Packages', 'manifest.json'), wd.p('proto', 'ProjectSettings', 'ProjectVersion.txt')))

STAGES = [
    Stage('detect', st_detect, lambda wd, a: fingerprint(a.apk), _engine_is_unity),
    Stage('dump', st_dump, lambda wd, a: fingerprint(a.apk), lambda wd: os.path.isfile(wd.p('il2cpp', 'dump.cs'))),
    Stage('distill', st_distill, lambda wd, a: fingerprint(wd.p('il2cpp', 'dump.cs'), wd.p('il2cpp', 'stringliteral.json'), wd.p('assets_dump'),
                                                          wd.p('hints.json'), wd.p('engine.txt'), wd.p('manifest_badging.txt')), None),
    Stage('author', st_author, lambda wd, a: fingerprint(_module(wd, a)), None),
    Stage('scaffold', st_scaffold, lambda wd, a: fingerprint(_module(wd, a), paths.TEMPLATE), None),
    Stage('test', st_test, _k_test, None),
    Stage('verify', st_verify, _k_verify, None),
    Stage('build', st_build, _k_build, None),
    Stage('install', st_install, lambda wd, a: None, None),
]

def run(a, stages=None):
    stages = stages or STAGES
    names = [st.name for st in stages]
    for n in (a.start, a.only):
        if n and n not in names: raise SystemExit('unknown stage %s; stages: %s' % (n, ', '.join(names)))
    wd = Workdir(a.workdir)
    started = a.start is None
    with wd.lock():
        for st in stages:
            if not started and st.name == a.start: started = True
            if not started: continue
            if a.only and st.name != a.only: continue
            key = st.key(wd, a)
            if not a.only and not a.force:
                if st.exists is not None and st.exists(wd): print('skip', st.name, '(outputs exist)'); continue
                if key is not None and wd.is_done(st.name, key): print('skip', st.name); continue
            print('==', st.name, flush=True)
            try: st.fn(wd, a)
            except Paused: return 3
            except subprocess.CalledProcessError as e:
                print('stage %s failed (exit %s): %s' % (st.name, e.returncode, ' '.join(map(str, e.cmd)))); return 1
            except FileNotFoundError as e:
                print('stage %s failed: %s not found' % (st.name, e.filename)); return 1
            if key is None: key = st.key(wd, a)   # build's key needs its own output (Builds/game.apk)
            if key is not None: wd.mark(st.name, key)
    return 0

def main(argv=None):
    ap = argparse.ArgumentParser(prog='apk2proto'); sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('apk'); r.add_argument('workdir'); r.add_argument('--module')
    r.add_argument('--from', dest='start'); r.add_argument('--only'); r.add_argument('--force', action='store_true')
    sub.add_parser('doctor')
    a = ap.parse_args(argv)
    if a.cmd == 'doctor': return DR.main()
    a.apk = os.path.abspath(a.apk)
    if a.module: a.module = os.path.abspath(a.module)
    if not os.path.isfile(a.apk): raise SystemExit('apk not found: ' + a.apk)
    return run(a)
