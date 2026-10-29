import argparse, json, os, subprocess, sys
from collections import namedtuple
from . import distill as D, doctor as DR, paths, scaffold as S, verify as V
from .state import Workdir, fingerprint

Stage = namedtuple('Stage', 'name fn key exists')

class Paused(Exception): pass

# doctor.checks() names the Unity build needs (adb is only for install)
BUILD_CHECKS = ('Unity Editor + Android module', 'cmdline-tools has only 16.0', 'NDK ' + DR.NDK, 'JDK 17 (JAVA_HOME or Unity bundled)')
MIN_MEM_MB = 3500

PAUSE_MSG = '''\
author: write the game module, then re-run the same command.
  read : {wd}/spec.json and {wd}/spec_index.md  (skill: apk2proto)
  write: {module}/module.json, Core/*.cs, View/GameModule.cs, Tests/*Tests.cs   (see modules/candyjam for the shape)
'''

def sh(cmd, **kw):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)

def _module(wd, a): return a.module or wd.p('module')
def _kit(*p): return os.path.join(paths.KIT, 'bin', *p)

def _check_engine(engine_txt):
    with open(engine_txt) as fh: first = fh.read().split('\n')[0].strip()
    if first != 'Unity': raise SystemExit('engine %r is not supported yet (other engines are separate specs)' % first)

def st_detect(wd, a):
    sh([_kit('unpack.sh'), a.apk, wd.path])
    _check_engine(wd.p('engine.txt'))

def st_dump(wd, a): sh([_kit('run_all.sh'), a.apk, wd.path, 'meta dump assets'])
def st_distill(wd, a): D.distill(wd.path)

def st_author(wd, a):
    m = _module(wd, a)
    if not os.path.isfile(os.path.join(m, 'View', 'GameModule.cs')):
        print(PAUSE_MSG.format(wd=wd.path, module=m)); raise Paused()

def st_scaffold(wd, a): S.scaffold(wd.p('proto'), paths.TEMPLATE, _module(wd, a))
def st_test(wd, a): sh(['dotnet', 'run', '--project', wd.p('proto', 'Tests~', 'Core.Tests')])

def st_verify(wd, a):
    problems = V.verify(wd.p('proto'), wd.p('apk'), wd.p('spec.json'))
    if problems: raise SystemExit('verify failed:\n  ' + '\n  '.join(problems))

def _mem_available_mb():
    try:
        with open('/proc/meminfo') as fh:
            for line in fh:
                if line.startswith('MemAvailable:'): return int(line.split()[1]) // 1024
    except (OSError, ValueError): pass
    return None                                        # unknown (not Linux): do not block

def st_build(wd, a):
    bad = [(n, fix) for ok, n, fix in DR.checks() if not ok and n in BUILD_CHECKS]   # adb is only for install
    if bad: raise SystemExit('build prerequisites missing:\n' + '\n'.join('MISS %s -> %s' % b for b in bad))
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
    if not ok: raise SystemExit('build failed, see ' + log)

def st_install(wd, a):
    with open(wd.p('proto', 'build.json')) as fh: app_id = json.load(fh)['appId']
    sh(['adb', 'install', '-r', wd.p('proto', 'Builds', 'game.apk')])
    sh(['adb', 'shell', 'monkey', '-p', app_id, '-c', 'android.intent.category.LAUNCHER', '1'])

STAGES = [
    Stage('detect', st_detect, lambda wd, a: fingerprint(a.apk), lambda wd: os.path.isfile(wd.p('engine.txt')) and os.path.isdir(wd.p('apk'))),
    Stage('dump', st_dump, lambda wd, a: fingerprint(a.apk), lambda wd: os.path.isfile(wd.p('il2cpp', 'dump.cs'))),
    Stage('distill', st_distill, lambda wd, a: fingerprint(wd.p('il2cpp', 'dump.cs'), wd.p('assets_dump'), wd.p('hints.json')), None),
    Stage('author', st_author, lambda wd, a: fingerprint(_module(wd, a)), None),
    Stage('scaffold', st_scaffold, lambda wd, a: fingerprint(_module(wd, a), paths.TEMPLATE), None),
    Stage('test', st_test, lambda wd, a: fingerprint(wd.p('proto', 'Assets'), wd.p('proto', 'Tests~', 'Core.Tests', 'Game')), None),
    Stage('verify', st_verify, lambda wd, a: fingerprint(wd.p('proto', 'Assets'), wd.p('spec.json')), None),
    Stage('build', st_build, lambda wd, a: fingerprint(wd.p('proto', 'Assets'), wd.p('proto', 'build.json')), None),
    Stage('install', st_install, lambda wd, a: None, None),
]

def run(a, stages=None):
    stages = stages or STAGES
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
    return run(a)
