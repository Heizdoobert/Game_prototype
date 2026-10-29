import json, os, re, shutil, tempfile, time, unittest
from apk2proto import distill, paths
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
    write(d, 'engine.txt', 'Unity\nIL2CPP -> use bin/il2cpp_dump.sh (+ unity_dump.py, ghidra_decomp.sh)\n')
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

    def test_spec_index_points_at_dump_not_missing_decompiler_tools(self):
        d = self.workdir(); distill.distill(d)
        with open(os.path.join(d, 'spec_index.md')) as fh: text = fh.read()
        self.assertIn('il2cpp/dump.cs', text); self.assertNotIn('fn.py', text); self.assertNotIn('xref.py', text)

    def test_backend_label_uses_line_prefix(self):
        d = self.workdir(); self.assertEqual(distill.distill(d)['app']['backend'], 'IL2CPP')
        write(d, 'engine.txt', 'Unity\nMono: Assembly-CSharp.dll present -> decompile with ilspycmd/dnSpy (no IL2CPP step)\n')
        self.assertEqual(distill.distill(d)['app']['backend'], 'Mono/other')

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
        size = lambda: len(json.dumps(spec, indent=1))
        n5 = {**spec, 'classes': [dict(c, fields=c['fields'][:5], methods=c['methods'][:5]) for c in classes]}
        limit = len(json.dumps(n5, indent=1)) + 100                # met after the n=5 step (slack covers coverage keys), not after n=15
        self.assertGreater(size(), limit)
        distill._fit(spec, limit)
        self.assertEqual(len(spec['classes']), 50)
        self.assertTrue(all(len(c['fields']) == 5 and len(c['methods']) == 5 for c in spec['classes']))
        self.assertTrue(spec['coverage']['trimmed'])
        self.assertEqual(spec['config'], [{'asset': 'a', 'json': '{}'}])
        self.assertEqual((spec['coverage']['classes_kept'], spec['coverage']['over_limit']), (50, False))

    def spec_text(self, d):
        with open(os.path.join(d, 'spec.json')) as fh: return fh.read()

    def test_config_redacted_before_truncation(self):
        d = self.workdir()
        data = {'n%d' % i: i for i in range(600)}
        data['pad'] = ''; data['apiKey'] = 'SECRETVALUE123'
        pad = 7996 - json.dumps(data, separators=(',', ':')).index('SECRETVALUE123')
        data['pad'] = 'x' * pad
        idx = json.dumps(data, separators=(',', ':')).index('SECRETVALUE123')
        self.assertTrue(idx < 8000 < idx + 14)                      # the secret value straddles the old cut
        write(d, 'assets_dump/mono/GameSettings_1.json', json.dumps(data))
        spec = distill.distill(d)
        self.assertIn('mono/GameSettings_1.json', [c['asset'] for c in spec['config']])
        self.assertNotIn('SECRE', self.spec_text(d))

    def test_non_odin_game_secret_keys_masked_and_listed(self):
        d = self.workdir()
        fake = {'PassCheat': 'FAKEcheat-9999', 'sdkKey': 'FAKEsdk-key-0001', 'adUnitId': 'FAKEunit-0002', 'price': [1, 2, 3, 4, 5, 6, 7]}
        write(d, 'assets_dump/mono/data__AppLovinSettings__x.json', json.dumps(fake))
        spec = distill.distill(d)
        self.assertIn('mono/data__AppLovinSettings__x.json', [c['asset'] for c in spec['config']])
        text = self.spec_text(d)
        for v in ('FAKEcheat-9999', 'FAKEsdk-key-0001', 'FAKEunit-0002'): self.assertNotIn(v, text)
        for k in ('PassCheat', 'sdkKey', 'adUnitId'):
            self.assertIn({'file': 'mono/data__AppLovinSettings__x.json', 'key': k}, spec['secrets'])

    def test_masker_covers_numbers_and_lists_under_secret_keys(self):
        out = distill._mask({'debugPin': 12345678, 'saltList': ['a', 'bbbbb'], 'n': 5, 'nested': [{'licenseKey': 'FAKE-lic-1'}], 'on': True})
        self.assertEqual(out, {'debugPin': '<REDACTED>', 'saltList': ['<REDACTED>', '<REDACTED>'], 'n': 5,
                               'nested': [{'licenseKey': '<REDACTED>'}], 'on': True})

    def all_text(self, d):
        with open(os.path.join(d, 'spec.json')) as fh: a = fh.read()
        with open(os.path.join(d, 'spec_index.md')) as fh: return a + fh.read()

    def test_dict_and_list_under_secret_key_masked_and_listed(self):
        d = self.workdir()
        write(d, 'assets_dump/mono/data__Ads__x.json', json.dumps(
            {'sdkKeys': {'android': 'FAKEdict-android-1', 'ios': ['FAKEdict-ios-2']}, 'price': [1, 2, 3, 4, 5, 6], 'on': True}))
        spec = distill.distill(d); text = self.all_text(d)
        for v in ('FAKEdict-android-1', 'FAKEdict-ios-2'): self.assertNotIn(v, text)
        self.assertIn({'file': 'mono/data__Ads__x.json', 'key': 'sdkKeys'}, spec['secrets'])
        self.assertEqual(json.loads(spec['config'][-1]['json'])['sdkKeys'], {'android': '<REDACTED>', 'ios': ['<REDACTED>']})

    def test_same_value_under_harmless_key_and_strings_scrubbed_everywhere(self):
        d = self.workdir(); v = 'Fake secret phrase 42'
        write(d, 'assets_dump/mono/data__Keys__x.json', json.dumps({'PassCheat': v, 'label': v, 'price': [1, 2, 3, 4, 5, 6]}))
        write(d, 'assets_dump/mono/data__Other__y.json', json.dumps({'note': 'see ' + v + ' ok', 'n': [1, 2, 3, 4, 5, 6]}))    # another asset, no secret key
        write(d, 'il2cpp/stringliteral.json', json.dumps([{'value': v}, {'value': 'Hello brave world'}]))
        spec = distill.distill(d)
        self.assertNotIn(v, self.all_text(d))
        self.assertIn('Hello brave world', spec['strings'])
        cfg = {c['asset']: json.loads(c['json']) for c in spec['config']}
        self.assertEqual(cfg['mono/data__Keys__x.json']['label'], '<REDACTED>')
        self.assertEqual(cfg['mono/data__Other__y.json']['note'], 'see <REDACTED> ok')
        self.assertIn({'file': 'mono/data__Keys__x.json', 'key': 'PassCheat'}, spec['secrets'])
        self.assertNotIn('label', [e['key'] for e in spec['secrets']])

    def test_key_value_pair_shapes_masked_and_listed(self):
        d = self.workdir()
        write(d, 'assets_dump/mono/data__Pairs__x.json', json.dumps({
            'entries': [{'key': 'PassCheat', 'value': 'FAKEpair-val-1'}, {'Name': 'sdkKey', 'Value': ['FAKEpair-val-2']},
                        {'key': 'volume', 'value': 'FAKEplain-val-3'}], 'n': [1, 2, 3, 4, 5, 6]}))
        spec = distill.distill(d); text = self.all_text(d)
        for v in ('FAKEpair-val-1', 'FAKEpair-val-2'): self.assertNotIn(v, text)
        self.assertIn('FAKEplain-val-3', text)                                     # non-secret name: untouched
        for k in ('PassCheat', 'sdkKey'): self.assertIn({'file': 'mono/data__Pairs__x.json', 'key': k}, spec['secrets'])
        self.assertNotIn('volume', [e['key'] for e in spec['secrets']])

    def test_flag_values_are_not_scrubbed_from_the_spec(self):
        d = self.workdir()
        write(d, 'assets_dump/mono/data__Flags__x.json', json.dumps({'passType': 'true', 'passMode': 'full', 'mode': 'true full', 'n': [1, 2, 3, 4, 5, 6]}))
        spec = distill.distill(d)
        self.assertEqual(json.loads([c for c in spec['config'] if 'Flags' in c['asset']][0]['json'])['mode'], 'true full')

    def test_odin_keeps_keys_drops_values(self):
        d = self.workdir()
        raw = ['featureUnlock/', 'odinval9999secret', 'deadbeef12345678', 'authToken_x']
        bytes_ = [b for r in raw for b in list(r.encode('utf-16le')) + [0, 0]]
        write(d, 'assets_dump/player/data__Odin__x__3.json', json.dumps({'serializationData': {'SerializedBytes': bytes_}}))
        spec = distill.distill(d)
        strings = [o for o in spec['config_odin'] if o['asset'].endswith('data__Odin__x__3.json')][0]['strings']
        self.assertEqual(strings, ['featureUnlock/'])
        text = self.spec_text(d)
        self.assertNotIn('odinval9999secret', text); self.assertNotIn('deadbeef12345678', text); self.assertNotIn('authToken_x', text)

    def test_huge_config_string_is_bounded_and_fast(self):
        d = self.workdir()
        write(d, 'assets_dump/mono/GameSettings_2.json', json.dumps(
            {'a': 'a' * 100 + '"' + 'a' * 199_900, 'b': 'c' * 200_000, 'n': [1, 2, 3, 4, 5, 6, 7]}))
        t0 = time.monotonic(); spec = distill.distill(d); elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 5)
        self.assertIn('mono/GameSettings_2.json', [c['asset'] for c in spec['config']])
        self.assertIsNone(re.search(r'(.)\1{2000}', self.spec_text(d)))

    def test_odin_non_list_bytes_do_not_crash(self):
        d = self.workdir()
        write(d, 'assets_dump/player/data__Odin__x__4.json', json.dumps({'serializationData': {'SerializedBytes': 'oops'}}))
        write(d, 'assets_dump/player/data__Odin__x__5.json', json.dumps({'serializationData': {'SerializedBytes': ['a', None]}}))
        spec = distill.distill(d)
        validate(spec)

    def test_string_constants_dropped(self):
        d = self.workdir()
        write(d, 'il2cpp/dump.cs', DUMP.replace('\tprivate const int MaxSlots = 5;',
              '\tprivate const int MaxSlots = 5;\n\tprivate const string Endpoint = "https://h/x?token=tok99887766";'))
        spec = distill.distill(d)
        self.assertEqual(spec['constants']['BoardController'], {'MaxSlots': '5'})
        self.assertNotIn('tok99887766', self.spec_text(d))

    def test_secretish_ui_strings_dropped(self):
        d = self.workdir()
        write(d, 'il2cpp/stringliteral.json', json.dumps([{'value': 'Cheat code is zebra pass'},
              {'value': 'Debug build only here'}, {'value': 'Not enough coins left'}]))
        spec = distill.distill(d)
        self.assertEqual(spec['strings'], ['Not enough coins left'])
        self.assertNotIn('zebra', self.spec_text(d))

    def test_malformed_hints_ignored(self):
        for bad in ('{not json', '[]', '{"keywords": "Popup"}', '{"keywords": [1, null, "", "  "]}'):
            d = self.workdir(); write(d, 'hints.json', bad)
            spec = distill.distill(d)
            self.assertEqual([c['name'] for c in spec['classes']], ['BoardController'], bad)
            self.assertIn('hints.json', ' '.join(spec['coverage']['notes']))

    def test_malformed_assets_degrade(self):
        d = self.workdir()
        write(d, 'assets_dump/player/bundle_summary.json', json.dumps({'a': 5, 'b': {'types': 'x'}, 'c': {'script_classes': {'Image': 'n', 'Button': 2}}}))
        write(d, 'assets_dump/mono/list.json', json.dumps([1, 2, 3]))
        write(d, 'assets_dump/mono/broken.json', '{nope')
        spec = distill.distill(d)
        validate(spec)
        self.assertEqual(spec['levels']['script_classes'], {'Button': 2})

    def test_written_size_honours_limit(self):
        d = self.workdir(); full = distill.distill(d)
        self.assertEqual((full['coverage']['trimmed'], full['coverage']['over_limit']), (False, False))
        self.assertEqual(os.path.getsize(os.path.join(d, 'spec.json')), full['coverage']['bytes'])
        limit = full['coverage']['bytes'] - 10
        spec = distill.distill(d, limit=limit)
        self.assertTrue(spec['coverage']['trimmed'])
        self.assertFalse(spec['coverage']['over_limit'])
        self.assertLessEqual(os.path.getsize(os.path.join(d, 'spec.json')), limit)
        self.assertEqual(os.path.getsize(os.path.join(d, 'spec.json')), spec['coverage']['bytes'])
        tiny = distill.distill(d, limit=1)
        self.assertTrue(tiny['coverage']['over_limit'])

if __name__ == '__main__': unittest.main()
