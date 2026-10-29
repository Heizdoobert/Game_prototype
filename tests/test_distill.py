import json, os, shutil, tempfile, unittest
from apk2proto import distill
from apk2proto.schema import validate

DUMP = '''// Image 0: Assembly-CSharp.dll - 0
// Image 1: mscorlib.dll - 3
// Namespace:
public class BoardController : MonoBehaviour // TypeDefIndex: 0
{
	// Fields
	private const int MaxSlots = 5;
	public int slotCount; // 0x20
	// Methods
	// RVA: 0x10 Offset: 0x10 VA: 0x10
	public void AddSlot() { }
}
// Namespace:
public enum ColorType // TypeDefIndex: 1
{
	// Fields
	public byte value__; // 0x0
	public const ColorType Blue = 0;
	public const ColorType Red = 1;
}
// Namespace:
public class PausePopup : Popup // TypeDefIndex: 2
{
}
// Namespace: System
public class String // TypeDefIndex: 3
{
	public const int MaxLen = 9;
}
'''

def write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh: fh.write(text)
    return p

class ParseDumpTests(unittest.TestCase):
    def test_parse_first_assembly_only(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        types = distill.parse_dump(write(d, 'dump.cs', DUMP))
        self.assertEqual([t['name'] for t in types], ['BoardController', 'ColorType', 'PausePopup'])
        b, e = types[0], types[1]
        self.assertEqual(b['consts'], {'MaxSlots': '5'})
        self.assertEqual(b['fields'], [['int', 'slotCount', '20']])
        self.assertEqual(b['methods'], ['AddSlot'])
        self.assertEqual((e['kind'], e['members']), ('enum', {'Blue': '0', 'Red': '1'}))

    def parse_text(self, text):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return distill.parse_dump(write(d, 'dump.cs', text))

    def test_generic_type_name_kept(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            '// Namespace: \n'
            'public class BasePackData<TConfig, TRemoteReward> : Base // TypeDefIndex: 0\n'
            '{\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['BasePackData<TConfig, TRemoteReward>'])

    def test_generic_field_type_kept(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class Board // TypeDefIndex: 0\n'
            '{\n'
            '\tpublic Dictionary<ColorType, int> slotByColor; // 0x58\n'
            '}\n')
        self.assertEqual(types[0]['fields'], [['Dictionary<ColorType, int>', 'slotByColor', '58']])

    def test_unparsed_header_does_not_leak_members(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class Prev // TypeDefIndex: 0\n'
            '{\n'
            '\tpublic int own; // 0x10\n'
            '}\n'
            'weird header // TypeDefIndex: 7\n'
            '{\n'
            '\tpublic int leaked; // 0x18\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['Prev'])
        self.assertEqual(types[0]['fields'], [['int', 'own', '10']])

    def test_single_image_dump_returns_all_types(self):
        # no "// Image 1:" line: fail-open, nothing is cut off
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class A // TypeDefIndex: 0\n'
            '{\n'
            '}\n'
            'public class B // TypeDefIndex: 1\n'
            '{\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['A', 'B'])

def build_workdir():
    d = tempfile.mkdtemp()
    write(d, 'il2cpp/dump.cs', DUMP)
    write(d, 'manifest_badging.txt', "package: name='com.x.y' versionCode='7' versionName='1.2'\n")
    write(d, 'engine.txt', 'Unity\nIL2CPP -> use bin/il2cpp_dump.sh\n')
    write(d, 'assets_dump/player/bundle_summary.json',
          json.dumps({'data.unity3d': {'script_classes': {'Image': 5, 'Button': 2}}}))
    odin = list('featureUnlock'.encode('utf-16le'))
    write(d, 'assets_dump/player/data__GameConfig__GameConfig__1.json',
          json.dumps({'m_Name': 'GameConfig', 'serializationData': {'SerializedBytes': [1, 0] + odin + [0, 0]}}))
    write(d, 'assets_dump/mono/a__Cfg__x__2.json', json.dumps({'serverPassword': '<REDACTED>', 'price': [1, 2, 3, 4, 5, 6]}))
    return d

class DistillTests(unittest.TestCase):
    def workdir(self):
        d = build_workdir(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def test_spec_is_valid_and_sections_filled(self):
        d = self.workdir(); spec = distill.distill(d)
        validate(spec)
        with open(os.path.join(d, 'spec.json')) as fh: self.assertEqual(json.load(fh), spec)
        self.assertEqual((spec['app']['package'], spec['app']['version'], spec['app']['engine']), ('com.x.y', '1.2', 'Unity'))
        self.assertEqual(spec['enums']['ColorType'], {'Blue': '0', 'Red': '1'})
        self.assertEqual(spec['constants']['BoardController'], {'MaxSlots': '5'})
        self.assertEqual([c['name'] for c in spec['classes']], ['BoardController'])
        self.assertEqual(spec['screens'], ['PausePopup'])
        self.assertEqual(spec['levels']['script_classes'], {'Image': 5, 'Button': 2})
        self.assertIn('featureUnlock', spec['config_odin'][0]['strings'])
        self.assertEqual(spec['secrets'], [{'file': 'mono/a__Cfg__x__2.json', 'key': 'serverPassword'}])
        self.assertTrue(os.path.exists(os.path.join(d, 'spec_index.md')))
        self.assertIn('Odin', ' '.join(spec['coverage']['notes']))

    def test_hints_widen_class_filter(self):
        d = self.workdir(); write(d, 'hints.json', json.dumps({'keywords': ['Popup']}))
        spec = distill.distill(d)
        self.assertIn('PausePopup', [c['name'] for c in spec['classes']])

    def test_limit_trims_and_flags(self):
        d = self.workdir(); spec = distill.distill(d, limit=1)       # impossible limit: every trim step runs
        self.assertTrue(spec['coverage']['trimmed'])
        self.assertTrue(all(c['fields'] == [] and c['methods'] == [] for c in spec['classes']))
        self.assertEqual(spec['config'], [])
        validate(spec)                                                # trimming never drops required keys

    def test_fit_shrinks_members_before_dropping_classes(self):
        classes = [{'name': 'C%d' % i, 'namespace': '', 'kind': 'class',
                    'fields': [['int', 'f%d' % j, '10'] for j in range(40)],
                    'methods': ['m%d' % j for j in range(40)]} for i in range(50)]
        spec = {'config': [{'asset': 'a', 'json': '{}'}], 'strings': [], 'classes': classes, 'coverage': {'trimmed': False}}
        size = lambda: len(json.dumps(spec, separators=(',', ':')))
        n5 = {**spec, 'classes': [dict(c, fields=c['fields'][:5], methods=c['methods'][:5]) for c in classes]}
        limit = len(json.dumps(n5, separators=(',', ':')))         # met exactly after the n=5 step, not after n=15
        self.assertGreater(size(), limit)
        distill._fit(spec, limit)
        self.assertEqual(len(spec['classes']), 50)
        self.assertTrue(all(len(c['fields']) == 5 and len(c['methods']) == 5 for c in spec['classes']))
        self.assertTrue(spec['coverage']['trimmed'])
        self.assertEqual(spec['config'], [{'asset': 'a', 'json': '{}'}])

if __name__ == '__main__': unittest.main()
