import glob, json, os, re, sys
from . import paths
from .schema import validate

sys.path.insert(0, os.path.join(paths.KIT, 'bin'))
import redact                                   # kit module: secret masking

HDR = re.compile(r'^(?:public |internal |private |protected )?(?:static |abstract |sealed )*'
                 r'(class|struct|enum|interface) (.+?)(?: : [^/]*?)? // TypeDefIndex: (\d+)')
CONST = re.compile(r'^\t(?:public|private|internal|protected)(?: static)?(?: readonly)? const (\S+) (\w+) = (.+);')
FIELD = re.compile(r'^\t(?:public|private|internal|protected)(?: static)?(?: readonly)? ([^;=(]+?) (\w+)(?: = [^;]*)?; // 0x([0-9A-Fa-f]+)')
METH = re.compile(r'^\t(?:public|private|internal|protected)[^(=]* (\w+)\(.*\) \{ \}')
NS = re.compile(r'^// Namespace: ?(.*)')
IMG = re.compile(r'^// Image (\d+): \S+ - (\d+)')

def parse_dump(path):
    types, ns, cur, images = [], '', None, {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            m = IMG.match(line)
            if m: images[int(m[1])] = int(m[2]); continue
            m = NS.match(line)
            if m: ns = m[1].strip(); continue
            m = HDR.match(line)
            if m:
                # no "// Image 1:" line (single-assembly dump) means no cutoff: fail-open, all types returned
                if 1 in images and int(m[3]) >= images[1]: break     # left Assembly-CSharp
                cur = {'name': m[2], 'kind': m[1], 'namespace': ns, 'consts': {}, 'members': {}, 'fields': [], 'methods': []}
                types.append(cur); continue
            if '// TypeDefIndex:' in line: cur = None; continue      # unparsed header: do not leak its members into the previous type
            if cur is None: continue
            m = CONST.match(line)
            if m:
                (cur['members'] if cur['kind'] == 'enum' else cur['consts'])[m[2]] = m[3]; continue
            m = FIELD.match(line)
            if m:
                if m[2] != 'value__': cur['fields'].append([m[1], m[2], m[3]])
                continue
            m = METH.match(line)
            if m: cur['methods'].append(m[1])
    return types

GAMEPLAY = r'board|level|piece|slot|booster|score|turn|match|tile|grid|wave|box|jar|tray|win|lose|revive|heart|coin|combo|move|goal|target|spawn|color'
SCREEN = re.compile(r'(popup|panel|screen|dialog|window)$', re.I)
CONFIGY = re.compile(r'config|setting|profile|data|table|rate', re.I)
SECRET_KEY = re.compile(redact.KEY + r'|pass|cheat|debug|sdk_?key|app_?key|unit_?id|licen[cs]e|signature|salt|keystore', re.I)
SECRETISH = SECRET_KEY
ODIN_KEY = re.compile(r'^[A-Za-z_][A-Za-z0-9_./-]{3,39}$')
ODIN_SHAPE = re.compile(r'[a-z][A-Z]|[_/.]')
MAX_JSON = 20_000_000

def _read(path, default=''):
    if not os.path.exists(path): return default
    with open(path, encoding='utf-8', errors='replace') as fh: return fh.read()

def _load_json(path):
    with open(path, encoding='utf-8') as fh: return json.load(fh)

def _big(path, notes):
    if os.path.getsize(path) <= MAX_JSON: return False
    _note(notes, 'skipped JSON files larger than 20 MB'); return True

def _clip(node, n=2000):
    # bound every string/key so the kit's quadratic regex only ever sees short input
    if isinstance(node, dict): return {(k[:n] if isinstance(k, str) else k): _clip(v, n) for k, v in node.items()}
    if isinstance(node, list): return [_clip(v, n) for v in node]
    return node[:n] if isinstance(node, str) else node

def _note(notes, msg):
    if msg not in notes: notes.append(msg)

def _hints(wd, notes):
    try: h = json.loads(_read(os.path.join(wd, 'hints.json'), '{}'))
    except ValueError: h = None
    kws = h.get('keywords', []) if isinstance(h, dict) else None
    if not isinstance(kws, list):
        _note(notes, 'hints.json ignored (not an object with a keywords list)'); return []
    good = [k.strip() for k in kws if isinstance(k, str) and k.strip()]
    if len(good) != len(kws): _note(notes, 'hints.json: non-string or empty keywords ignored')
    return good

def _app(wd):
    badge = _read(os.path.join(wd, 'manifest_badging.txt'))
    pkg = re.search(r"package: name='([^']+)'", badge); ver = re.search(r"versionName='([^']*)'", badge)
    eng = _read(os.path.join(wd, 'engine.txt'))
    libs = sorted({os.path.basename(p)[3:-3] for p in glob.glob(os.path.join(wd, 'apk', 'lib', '*', 'lib*.so'))})
    return {'package': pkg[1] if pkg else '', 'version': ver[1] if ver else '',
            'engine': (eng.split('\n')[0].strip() or 'unknown'), 'backend': 'IL2CPP' if 'IL2CPP' in eng else 'Mono/other',
            'native_libs': libs}

def _count_into(dst, src):
    for c, n in src.items():
        if isinstance(n, int) and not isinstance(n, bool): dst[c] = dst.get(c, 0) + n

def _asset_overview(dump, notes):
    out = {'bundles': 0, 'object_types': {}, 'script_classes': {}}
    for f in glob.glob(os.path.join(dump, '**', 'bundle_summary.json'), recursive=True):
        if _big(f, notes): continue
        try: summary = _load_json(f)
        except Exception: summary = None
        if not isinstance(summary, dict): _note(notes, 'skipped unreadable bundle_summary.json'); continue
        for v in summary.values():
            if not isinstance(v, dict): _note(notes, 'skipped malformed bundle_summary entries'); continue
            if 'script_classes' in v:
                if isinstance(v['script_classes'], dict): _count_into(out['script_classes'], v['script_classes'])
            else:
                out['bundles'] += 1
                if isinstance(v.get('types'), dict): _count_into(out['object_types'], v['types'])
    out['script_classes'] = dict(sorted(out['script_classes'].items(), key=lambda kv: -kv[1])[:40])
    out['object_types'] = dict(sorted(out['object_types'].items(), key=lambda kv: -kv[1])[:40])
    return out

def _odin_strings(byte_list):
    # best-effort key-name candidates: identifier-shaped runs only, never anything secret-looking
    if not isinstance(byte_list, list): return []
    raw = bytes(b & 255 for b in byte_list)
    out = []
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}', raw):
        s = m.group().decode('utf-16le')
        if ODIN_KEY.match(s) and ODIN_SHAPE.search(s) and not SECRETISH.search(s) and s not in out: out.append(s)
    return out[:300]

def _secret_keys(node, rel, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and len(v) >= 4 and SECRET_KEY.search(k):
                if {'file': rel, 'key': k} not in out: out.append({'file': rel, 'key': k})
            else: _secret_keys(v, rel, out)
    elif isinstance(node, list):
        for v in node: _secret_keys(v, rel, out)

def _mask(node):
    # whole-value mask for any key the game-wide heuristic calls secret (kit redact_obj only knows its own narrow KEY)
    if isinstance(node, dict):
        return {k: ('<REDACTED>' if isinstance(k, str) and SECRET_KEY.search(k) and isinstance(v, (str, int, float, list)) and not isinstance(v, bool)
                    else _mask(v)) for k, v in node.items()}
    if isinstance(node, list): return [_mask(v) for v in node]
    return node

def _scan_assets(dump, notes):
    config, odin, secrets = [], [], []
    for f in sorted(glob.glob(os.path.join(dump, '**', '*.json'), recursive=True)):
        if os.path.basename(f) == 'bundle_summary.json': continue
        try:
            if _big(f, notes): continue
            d = _load_json(f)
        except Exception: _note(notes, 'skipped unreadable assets_dump JSON files'); continue
        rel = os.path.relpath(f, dump)
        try:
            _secret_keys(d, rel, secrets)
            sd = d.get('serializationData') if isinstance(d, dict) else None
            if isinstance(sd, dict) and sd.get('SerializedBytes'):
                odin.append({'asset': rel, 'strings': _odin_strings(sd['SerializedBytes'])}); continue
            if not CONFIGY.search(os.path.basename(f)): continue
            d = _clip(d)
            if len(re.findall(r'[:\[,]-?\d+\.?\d*', json.dumps(d, separators=(',', ':')))) > 5:
                # secret-named values are masked whole by redact_obj BEFORE the 8000 cut, so a cut never leaves half a secret
                config.append({'asset': rel, 'json': json.dumps(redact.redact_obj(_mask(d)), separators=(',', ':'))[:8000]})
        except Exception: _note(notes, 'skipped assets that could not be parsed')
    return config[:12], odin[:12], secrets

def _ui_strings(path, notes, cap=300):
    if not os.path.exists(path): return []
    if _big(path, notes): return []
    try: lits = _load_json(path)
    except Exception: _note(notes, 'skipped unreadable stringliteral.json'); return []
    vals = {s['value'] for s in lits if isinstance(s, dict) and isinstance(s.get('value'), str)} if isinstance(lits, list) else set()
    seen = {redact.redact_text(v) for v in vals
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,.!?':+-]{5,60}", v) and ' ' in v
            and not SECRETISH.search(v)}
    return sorted(seen, key=lambda v: (len(v), v))[:cap]

def _fit(spec, limit):
    cov = spec['coverage']
    size = lambda: len(json.dumps(spec, indent=1))      # same serialisation as the written spec.json
    cov.update(bytes=limit, over_limit=False, classes_kept=len(spec['classes']))    # placeholders: count their bytes
    def done():
        cov['classes_kept'] = len(spec['classes'])
        for _ in range(5):                               # bytes/over_limit are inside the measured text: settle on a fixed point
            n = size(); cov.update(bytes=n, over_limit=n > limit)
            if size() == n: break
    if size() > limit:
        cov['trimmed'] = True
        for n in (15, 5, 0):                             # shrink every class first, keep all of them while possible
            for c in spec['classes']: c['fields'], c['methods'] = c['fields'][:n], c['methods'][:n]
            if size() <= limit: return done()
        spec['config'] = []; spec['strings'] = spec['strings'][:50]
        if size() > limit: spec['classes'] = spec['classes'][:100]
    done()

def distill(wd, limit=100_000):
    notes = ['config values inside Odin-serialised assets are not decoded; only key names are listed (config_odin)',
             'odin strings are best-effort key-name candidates and may include values',
             'levels is an asset overview, not per-level layouts']
    rx = re.compile('|'.join([GAMEPLAY] + [re.escape(k) for k in _hints(wd, notes)]), re.I)
    types = parse_dump(os.path.join(wd, 'il2cpp', 'dump.cs'))
    picked = [t for t in types if rx.search(t['name'])]
    classes = [t for t in picked if t['kind'] != 'enum']
    dump = os.path.join(wd, 'assets_dump')
    config, odin, secrets = _scan_assets(dump, notes)
    consts = {t['name']: {k: v for k, v in t['consts'].items() if not v.startswith('"')} for t in classes}   # no string literals
    spec = {
        'app': _app(wd),
        'enums': {t['name']: t['members'] for t in picked if t['kind'] == 'enum'},
        'constants': {n: c for n, c in consts.items() if c},
        'config': config, 'config_odin': odin,
        'classes': [{'name': t['name'], 'namespace': t['namespace'], 'kind': t['kind'],
                     'fields': t['fields'][:60], 'methods': t['methods'][:80]} for t in classes],
        'levels': _asset_overview(dump, notes),
        'strings': _ui_strings(os.path.join(wd, 'il2cpp', 'stringliteral.json'), notes),
        'screens': [t['name'] for t in types if SCREEN.search(t['name'])],
        'secrets': secrets,
        'coverage': {'types_total': len(types), 'classes': len(classes), 'enums': len(picked) - len(classes),
                     'config_assets': len(config), 'odin_assets': len(odin), 'trimmed': False, 'notes': notes},
    }
    spec = redact.redact_obj(spec)
    _fit(spec, limit); validate(spec)
    with open(os.path.join(wd, 'spec.json'), 'w', encoding='utf-8') as fh: json.dump(spec, fh, indent=1)
    with open(os.path.join(wd, 'spec_index.md'), 'w', encoding='utf-8') as fh:
        fh.write('# spec index\n\nDeep dives (kit at `%s`):\n'
                 '- class body: `bin/fn.py \'Class$$Method\' DIR -n 120`; field users: `bin/xref.py -f Class field`\n'
                 '- raw dump: `il2cpp/dump.cs`; config assets: `assets_dump/`; strings: `il2cpp/stringliteral.json`\n'
                 '- coverage: see `spec.json` key `coverage`\n' % paths.KIT)
    return spec
