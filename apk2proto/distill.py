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

def _read(path, default=''):
    if not os.path.exists(path): return default
    with open(path, encoding='utf-8', errors='replace') as fh: return fh.read()

def _load_json(path):
    with open(path, encoding='utf-8') as fh: return json.load(fh)

def _app(wd):
    badge = _read(os.path.join(wd, 'manifest_badging.txt'))
    pkg = re.search(r"package: name='([^']+)'", badge); ver = re.search(r"versionName='([^']*)'", badge)
    eng = _read(os.path.join(wd, 'engine.txt'))
    libs = sorted({os.path.basename(p)[3:-3] for p in glob.glob(os.path.join(wd, 'apk', 'lib', '*', 'lib*.so'))})
    return {'package': pkg[1] if pkg else '', 'version': ver[1] if ver else '',
            'engine': (eng.split('\n')[0].strip() or 'unknown'), 'backend': 'IL2CPP' if 'IL2CPP' in eng else 'Mono/other',
            'native_libs': libs}

def _asset_overview(dump):
    out = {'bundles': 0, 'object_types': {}, 'script_classes': {}}
    for f in glob.glob(os.path.join(dump, '**', 'bundle_summary.json'), recursive=True):
        for v in _load_json(f).values():
            if 'script_classes' in v:
                for c, n in v['script_classes'].items(): out['script_classes'][c] = out['script_classes'].get(c, 0) + n
            else:
                out['bundles'] += 1
                for c, n in v.get('types', {}).items(): out['object_types'][c] = out['object_types'].get(c, 0) + n
    out['script_classes'] = dict(sorted(out['script_classes'].items(), key=lambda kv: -kv[1])[:40])
    out['object_types'] = dict(sorted(out['object_types'].items(), key=lambda kv: -kv[1])[:40])
    return out

def _odin_strings(byte_list):
    raw = bytes(b & 255 for b in byte_list)
    out = []
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}', raw):
        s = m.group().decode('utf-16le')
        if s not in out: out.append(s)
    return out[:300]

def _secret_keys(node, rel, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v == '<REDACTED>' and re.search(redact.KEY, k, re.I):
                if {'file': rel, 'key': k} not in out: out.append({'file': rel, 'key': k})
            else: _secret_keys(v, rel, out)
    elif isinstance(node, list):
        for v in node: _secret_keys(v, rel, out)

def _scan_assets(dump):
    config, odin, secrets = [], [], []
    for f in sorted(glob.glob(os.path.join(dump, '**', '*.json'), recursive=True)):
        if os.path.basename(f) == 'bundle_summary.json': continue
        try: d = _load_json(f)
        except Exception: continue
        rel = os.path.relpath(f, dump); _secret_keys(d, rel, secrets)
        sd = d.get('serializationData') if isinstance(d, dict) else None
        if isinstance(sd, dict) and sd.get('SerializedBytes'):
            odin.append({'asset': rel, 'strings': _odin_strings(sd['SerializedBytes'])}); continue
        s = json.dumps(d, separators=(',', ':'))
        if CONFIGY.search(os.path.basename(f)) and len(re.findall(r'[:\[,]-?\d+\.?\d*', s)) > 5:
            config.append({'asset': rel, 'json': s[:8000]})
    return config[:12], odin[:12], secrets

def _ui_strings(path, cap=300):
    if not os.path.exists(path): return []
    seen = {s['value'] for s in _load_json(path)
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,.!?':+-]{5,60}", s['value']) and ' ' in s['value']}
    return sorted(seen, key=lambda s: (len(s), s))[:cap]

def _fit(spec, limit):
    size = lambda: len(json.dumps(spec, separators=(',', ':')))
    if size() <= limit: return
    spec['coverage']['trimmed'] = True
    for c in spec['classes']: c['fields'], c['methods'] = c['fields'][:15], c['methods'][:15]
    if size() > limit: spec['config'] = []; spec['strings'] = spec['strings'][:50]
    if size() > limit: spec['classes'] = spec['classes'][:100]
    if size() > limit:
        for c in spec['classes']: c['fields'], c['methods'] = [], []

def distill(wd, limit=100_000):
    hints = json.loads(_read(os.path.join(wd, 'hints.json'), '{}'))
    rx = re.compile('|'.join([GAMEPLAY] + [re.escape(k) for k in hints.get('keywords', [])]), re.I)
    types = parse_dump(os.path.join(wd, 'il2cpp', 'dump.cs'))
    picked = [t for t in types if rx.search(t['name'])]
    classes = [t for t in picked if t['kind'] != 'enum']
    config, odin, secrets = _scan_assets(os.path.join(wd, 'assets_dump'))
    spec = {
        'app': _app(wd),
        'enums': {t['name']: t['members'] for t in picked if t['kind'] == 'enum'},
        'constants': {t['name']: t['consts'] for t in classes if t['consts']},
        'config': config, 'config_odin': odin,
        'classes': [{'name': t['name'], 'namespace': t['namespace'], 'kind': t['kind'],
                     'fields': t['fields'][:60], 'methods': t['methods'][:80]} for t in classes],
        'levels': _asset_overview(os.path.join(wd, 'assets_dump')),
        'strings': _ui_strings(os.path.join(wd, 'il2cpp', 'stringliteral.json')),
        'screens': [t['name'] for t in types if SCREEN.search(t['name'])],
        'secrets': secrets,
        'coverage': {'types_total': len(types), 'classes': len(classes), 'enums': len(picked) - len(classes),
                     'config_assets': len(config), 'odin_assets': len(odin), 'trimmed': False,
                     'notes': ['config values inside Odin-serialised assets are not decoded; only key names are listed (config_odin)',
                               'levels is an asset overview, not per-level layouts']},
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
