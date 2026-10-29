import hashlib, json, os, sys
from . import paths
sys.path.insert(0, os.path.join(paths.KIT, 'bin'))
import redact                                   # kit module: secret detection

SKIP = {'Library', 'Temp', 'obj', 'bin', 'Builds', 'Logs', '.git', 'UserSettings'}
MIN = 64                    # smaller files (stubs, tiny metas) legitimately coincide
MAX_SCAN = 2_000_000        # bigger text files are skipped silently: the kit regex is quadratic, generated code is not hand-written secrets
LINE = 4000                 # ponytail: only the first 4000 chars of a line / spec string are checked; raise if secrets can sit deeper

def _sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def _files(root, skip=()):
    for dp, dns, fs in os.walk(root):
        dns[:] = [d for d in dns if d not in skip]
        for f in fs: yield os.path.join(dp, f)

def _clip(node, n=LINE):
    if isinstance(node, dict): return {(k[:n] if isinstance(k, str) else k): _clip(v, n) for k, v in node.items()}
    if isinstance(node, list): return [_clip(v, n) for v in node]
    return node[:n] if isinstance(node, str) else node

def _leaks(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line[:LINE]
            if redact.redact_text(line) != line: return True
    return False

def verify(project, apk_dir, spec_path=None):
    problems, orig = [], set()
    for sub in ('assets', 'res'):
        for f in _files(os.path.join(apk_dir, sub)):
            if os.path.getsize(f) >= MIN: orig.add(_sha(f))
    for f in _files(project, SKIP):
        rel, size = os.path.relpath(f, project), os.path.getsize(f)
        if size >= MIN and _sha(f) in orig: problems.append(f'original asset copied: {rel}')
        if f.endswith(('.cs', '.json')) and size <= MAX_SCAN and _leaks(f): problems.append(f'possible secret in {rel}')
    if spec_path:
        with open(spec_path, encoding='utf-8') as fh: spec = _clip(json.load(fh))
        if redact.redact_obj(spec) != spec: problems.append('possible secret in spec.json')
    return problems
