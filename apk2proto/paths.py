import glob, importlib, os, re, sys

KIT = os.environ.get('GRE_KIT', '/mnt/second_drive/Ghost_melon/game_re_kit')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')

def unity_editor():
    found = glob.glob(os.path.expanduser('~/Unity/Hub/Editor/*/Editor/Unity'))
    # newest by version numbers: a plain sort puts 6000.10 before 6000.6
    return max(found, key=lambda p: [int(n) for n in re.findall(r'\d+', p.split(os.sep)[-3])], default=None)

def redact():
    """The kit's redact module, imported on first use so commands that never redact (doctor) work without the kit."""
    if 'redact' not in sys.modules:
        b = os.path.join(KIT, 'bin')
        if not os.path.isfile(os.path.join(b, 'redact.py')): raise SystemExit('game_re_kit not found at %s (set GRE_KIT)' % KIT)
        if b not in sys.path: sys.path.insert(0, b)
    return importlib.import_module('redact')
