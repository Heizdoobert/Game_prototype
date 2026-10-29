import hashlib, json, os, re, sys
from . import paths
sys.path.insert(0, os.path.join(paths.KIT, 'bin'))
import redact                                   # kit module: secret detection

SKIP = {'Library', 'Temp', 'obj', 'bin', 'Builds', 'Logs', '.git', 'UserSettings'}
MIN = 64                    # smaller files (stubs, tiny metas) legitimately coincide
MAX_SCAN = 2_000_000        # bigger text files are skipped silently: the kit regex is quadratic, generated code is not hand-written secrets
LINE = 4000                 # ponytail: only the first 4000 chars of a line / spec string are checked; raise if secrets can sit deeper.
BLOB = re.compile(r'\w{300,}')   # ponytail: lines holding a 300+ char \w run (base64/hex blobs) are NOT scanned (kit regex is quadratic on them); a secret on such a line is missed

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

def _has_big_key(node):
    if isinstance(node, dict): return any((isinstance(k, str) and len(k) > LINE) or _has_big_key(v) for k, v in node.items())
    if isinstance(node, list): return any(_has_big_key(v) for v in node)
    return False

def _leak_line(path):
    """1-based number of the first line that redact would change, else 0."""
    with open(path, encoding='utf-8', errors='replace') as f:
        for n, line in enumerate(f, 1):
            line = line[:LINE]
            if BLOB.search(line): continue
            if redact.redact_text(line) != line: return n
    return 0

def verify(project, apk_dir, spec_path=None):
    problems, orig = [], set()
    subs = [os.path.join(apk_dir, s) for s in ('assets', 'res')]
    if not any(os.path.isdir(d) for d in subs):
        problems.append('apk assets/res not found: asset-copy check could not run')
    for d in subs:
        for f in _files(d):
            try:
                if os.path.getsize(f) >= MIN: orig.add(_sha(f))
            except OSError: problems.append(f'unreadable: {os.path.relpath(f, apk_dir)}')
    for f in _files(project, SKIP):
        rel = os.path.relpath(f, project)
        try:
            size = os.path.getsize(f)
            if size >= MIN and _sha(f) in orig: problems.append(f'original asset copied: {rel}')
            if f.endswith(('.cs', '.json')) and size <= MAX_SCAN:
                n = _leak_line(f)
                if n: problems.append(f'possible secret in {rel}:{n}')
        except OSError: problems.append(f'unreadable: {rel}')
    if spec_path:
        try:
            with open(spec_path, encoding='utf-8') as fh: spec = json.load(fh)
            if _has_big_key(spec): problems.append('spec.json has an oversized key')
            else:
                spec = _clip(spec)
                if redact.redact_obj(spec) != spec: problems.append('possible secret in spec.json')
        except (OSError, ValueError, RecursionError): problems.append('spec.json unreadable')
    return problems
