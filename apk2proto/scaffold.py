import json, os, re, shutil


def scaffold(proto, template, module):
    """Copy template into proto and replace its Game dirs (Core, View, Tests, Resources = the module's asset pack and authored levels) and their .meta files with the module's. Shell and Unity state (Library, Shell .meta) are kept."""
    if not os.path.isfile(os.path.join(module, 'module.json')) or not os.path.isfile(os.path.join(module, 'View', 'GameModule.cs')):
        raise SystemExit('module needs module.json and View/GameModule.cs: ' + module)
    mj = os.path.join(module, 'module.json')
    try:
        with open(mj) as fh: meta = json.load(fh)
    except ValueError: meta = None
    if not isinstance(meta, dict): raise SystemExit('module.json is not valid JSON object: ' + mj)
    if not re.fullmatch(r'[a-z][a-z0-9]{1,30}', str(meta.get('id', ''))) or not str(meta.get('name', '')).strip():
        raise SystemExit('module.json needs id (lowercase letters/digits, e.g. candyjam) and a non-empty name')
    shutil.copytree(template, proto, dirs_exist_ok=True, ignore=shutil.ignore_patterns('bin', 'obj'))
    for src, dst in (('Core', 'Assets/Scripts/Game/Core'), ('View', 'Assets/Scripts/Game/View'), ('Tests', 'Tests~/Core.Tests/Game'), ('Resources', 'Assets/Resources')):
        d = os.path.join(proto, dst)
        shutil.rmtree(d, ignore_errors=True)
        if os.path.isdir(os.path.join(module, src)):
            shutil.copytree(os.path.join(module, src), d)
    os.makedirs(os.path.join(proto, 'Tests~', 'Core.Tests', 'Game'), exist_ok=True)   # the harness fails on a Game/ dir with no test class
    with open(os.path.join(proto, 'build.json'), 'w') as fh:
        json.dump({'product': meta['name'], 'appId': 'com.proto.' + meta['id']}, fh)
    return meta
