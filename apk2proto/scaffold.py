import json, os, shutil


def scaffold(proto, template, module):
    """Copy template into proto, swap in the module's game dirs. Unity state (Library, .meta) is kept."""
    if not os.path.isfile(os.path.join(module, 'module.json')) or not os.path.isfile(os.path.join(module, 'View', 'GameModule.cs')):
        raise SystemExit('module needs module.json and View/GameModule.cs: ' + module)
    with open(os.path.join(module, 'module.json')) as fh:
        meta = json.load(fh)
    shutil.copytree(template, proto, dirs_exist_ok=True, ignore=shutil.ignore_patterns('bin', 'obj'))
    for src, dst in (('Core', 'Assets/Scripts/Game/Core'), ('View', 'Assets/Scripts/Game/View'), ('Tests', 'Tests~/Core.Tests/Game')):
        d = os.path.join(proto, dst)
        shutil.rmtree(d, ignore_errors=True)
        if os.path.isdir(os.path.join(module, src)):
            shutil.copytree(os.path.join(module, src), d)
    with open(os.path.join(proto, 'build.json'), 'w') as fh:
        json.dump({'product': meta['name'], 'appId': 'com.proto.' + meta['id']}, fh)
    return meta
