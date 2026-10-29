import hashlib, json, os, re
from . import paths
from .textutil import clip, secret_pairs, secret_value

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

PER_KEY, MAX_VALUE_LEN, MAX_DUMP = 50, 200, 20_000_000

def _secret_values(spec_path, assets_dump):
    """{value bytes: [(file, key)]} of the original secret values named by spec['secrets'], read from the raw dump.
    Values are never reported. At most PER_KEY per {file,key} so no key can starve another; long values are checked by their first 200 chars."""
    try:
        with open(spec_path, encoding='utf-8') as fh: entries = json.load(fh).get('secrets', [])
    except (OSError, ValueError, AttributeError, RecursionError): return {}
    out = {}
    for e in entries if isinstance(entries, list) else []:
        if not (isinstance(e, dict) and isinstance(e.get('file'), str) and isinstance(e.get('key'), str)): continue
        f, key, mine = os.path.join(assets_dump, e['file']), e['key'], set()
        try:
            if os.path.getsize(f) > MAX_DUMP: continue
            with open(f, encoding='utf-8', errors='replace') as fh: data = json.load(fh)
            for name, leaf in secret_pairs(data, lambda k: k == key):
                v = secret_value(leaf)
                if v is not None: mine.add(v[:MAX_VALUE_LEN])
                if len(mine) >= PER_KEY: break
        except (OSError, ValueError, RecursionError): continue
        for v in mine:
            if (e['file'], key) not in out.setdefault(v.encode('utf-8', 'replace'), []): out[v.encode('utf-8', 'replace')].append((e['file'], key))
    return out

def _value_hits(values, files):
    """problems for exact byte hits of a secret value in the (label, path, optional) files; names file+key, never the value"""
    out = []
    for label, path, optional in files:
        try:
            if os.path.getsize(path) > MAX_SCAN: continue
            with open(path, 'rb') as fh: data = fh.read()
        except FileNotFoundError:
            if not optional: out.append(f'unreadable: {label}')
            continue
        except OSError: out.append(f'unreadable: {label}'); continue
        for val, where in values.items():
            if val in data: out += [f'secret value from {rel}:{key} appears in {label}' for rel, key in where]
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
        values = _secret_values(spec_path, assets_dump) if assets_dump else {}
        if values:
            d = os.path.dirname(os.path.abspath(spec_path))
            files = [(n, os.path.join(d, n), True) for n in (os.path.basename(spec_path), 'spec_index.md', 'rules.md')]
            files += [(os.path.relpath(f, project), f, False) for f in _files(project, SKIP)]    # every file type: an .xml/.asset/.bytes copy counts
            files += [(f, f, False) for f in extra_text_files]
            problems += [p for p in dict.fromkeys(_value_hits(values, files)) if p not in problems]
    return problems
