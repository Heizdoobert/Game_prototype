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
