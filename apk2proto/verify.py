import hashlib, json, os, re
from . import paths
from .textutil import clip

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
            if paths.redact().redact_text(line) != line: return n
    return 0

MAX_VALUES, MAX_VALUE_LEN, MAX_DUMP = 200, 200, 20_000_000
TEXT_EXT = ('.cs', '.json', '.md', '.txt', '.asmdef')

def _secret_values(spec_path, assets_dump):
    """[(file, key, value)] of the original secret values named by spec['secrets'], read from the raw dump. Never reported."""
    try:
        with open(spec_path, encoding='utf-8') as fh: entries = json.load(fh).get('secrets', [])
    except (OSError, ValueError, AttributeError, RecursionError): return []
    out = []
    def walk(node, rel, key):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == key:
                    for x in (v if isinstance(v, list) else [v]):
                        if isinstance(x, bool): continue
                        s = x if isinstance(x, str) else str(x) if isinstance(x, int) and len(str(abs(x))) >= 6 else ''
                        if len(s) >= 4 and s != '<REDACTED>' and len(s) <= MAX_VALUE_LEN and (rel, key, s) not in out: out.append((rel, key, s))
                walk(v, rel, key)
        elif isinstance(node, list):
            for v in node: walk(v, rel, key)
    for e in entries if isinstance(entries, list) else []:
        if not (isinstance(e, dict) and isinstance(e.get('file'), str) and isinstance(e.get('key'), str)): continue
        f = os.path.join(assets_dump, e['file'])
        try:
            if os.path.getsize(f) > MAX_DUMP: continue
            with open(f, encoding='utf-8', errors='replace') as fh: walk(json.load(fh), e['file'], e['key'])
        except (OSError, ValueError, RecursionError): continue
    return out[:MAX_VALUES]

def _value_hits(values, texts):
    """problems for every exact substring hit of a secret value in the (label, path) files; names file+key, never the value"""
    out = []
    for label, path in texts:
        try:
            if os.path.getsize(path) > MAX_SCAN: continue
            with open(path, encoding='utf-8', errors='replace') as fh: text = fh.read()
        except OSError: continue
        for rel, key, val in values:
            if val in text: out.append(f'secret value from {rel}:{key} appears in {label}')
    return out

def verify(project, apk_dir, spec_path=None, assets_dump=None, extra_text_files=()):
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
                spec = clip(spec, LINE)
                if paths.redact().redact_obj(spec) != spec: problems.append('possible secret in spec.json')
        except (OSError, ValueError, RecursionError): problems.append('spec.json unreadable')
        values = _secret_values(spec_path, assets_dump) if assets_dump else []
        if values:
            d = os.path.dirname(os.path.abspath(spec_path))
            texts = [(n, os.path.join(d, n)) for n in (os.path.basename(spec_path), 'spec_index.md', 'rules.md')]
            texts += [(os.path.relpath(f, project), f) for f in _files(project, SKIP) if f.endswith(TEXT_EXT)]
            texts += [(f, f) for f in extra_text_files]
            problems += _value_hits(values, texts)
    return problems
