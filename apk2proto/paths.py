import glob, os

KIT = os.environ.get('GRE_KIT', '/mnt/second_drive/Ghost_melon/game_re_kit')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'template')

def unity_editor():
    found = sorted(glob.glob(os.path.expanduser('~/Unity/Hub/Editor/*/Editor/Unity')))
    return found[-1] if found else None
