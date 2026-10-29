import json, os, shutil, tempfile, time, unittest
from apk2proto.verify import verify

PNG = b'\x89PNG' + b'a' * 200

def put(root, rel, data):
    p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f: f.write(data if isinstance(data, bytes) else data.encode())
    return p

class VerifyTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True); return d

    def setUp(self):
        self.apk, self.proj = self.tmp(), self.tmp()
        put(self.apk, 'assets/tex.png', PNG)
        put(self.apk, 'res/drawable/ic.png', PNG + b'res')
        put(self.proj, 'Assets/Scripts/A.cs', 'class A {}')

    def test_clean(self): self.assertEqual(verify(self.proj, self.apk), [])

    def test_copied_asset_detected_even_renamed(self):
        put(self.proj, 'Assets/Art/x.bin', PNG)
        out = verify(self.proj, self.apk)
        self.assertEqual(len(out), 1); self.assertIn('x.bin', out[0])

    def test_copied_res_detected(self):
        put(self.proj, 'Assets/Art/r.bin', PNG + b'res')
        out = verify(self.proj, self.apk)
        self.assertEqual(len(out), 1); self.assertIn('r.bin', out[0])

    def test_small_identical_file_not_flagged(self):
        put(self.apk, 'assets/tiny.bin', b'x' * 63); put(self.proj, 'Assets/tiny.bin', b'x' * 63)
        self.assertEqual(verify(self.proj, self.apk), [])

    def test_skip_dirs_not_scanned(self):
        for d in ('Library', 'Temp', 'obj', 'bin', 'Builds', 'Logs', '.git', 'UserSettings'):
            put(self.proj, d + '/c.bin', PNG)
            put(self.proj, d + '/s.cs', 'var x = {"apiKey": "abcd1234efgh"};')
        self.assertEqual(verify(self.proj, self.apk), [])

    def test_secret_in_spec_detected(self):
        spec = put(self.tmp(), 'spec.json', json.dumps({'a': {'serverPassword': 'hunter22x'}}))
        self.assertTrue(any('spec' in p for p in verify(self.proj, self.apk, spec)))

    def test_clean_spec_ok(self):
        spec = put(self.tmp(), 'spec.json', json.dumps({'a': {'serverPassword': '<REDACTED>', 'n': 1}}))
        self.assertEqual(verify(self.proj, self.apk, spec), [])

    def test_secret_in_project_text_detected(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'var x = {"apiKey": "abcd1234efgh"};')
        self.assertEqual(verify(self.proj, self.apk), [f'possible secret in {os.path.join("Assets", "Scripts", "B.cs")}:1'])

    def test_secret_line_number_reported(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'class B {}\n\nvar x = {"apiKey": "abcd1234efgh"};\n')
        self.assertTrue(verify(self.proj, self.apk)[0].endswith('B.cs:3'))

    def test_problem_names_path_never_secret(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'var x = {"apiKey": "abcd1234efgh"};')
        spec = put(self.tmp(), 'spec.json', json.dumps({'serverPassword': 'hunter22x'}))
        out = verify(self.proj, self.apk, spec)
        self.assertTrue(any('B.cs' in p for p in out))
        for p in out:
            self.assertNotIn('abcd1234efgh', p); self.assertNotIn('hunter22x', p)

    def test_huge_single_line_file_skipped(self):
        put(self.proj, 'Assets/Scripts/Big.cs', 'var s = "' + 'a' * 3_000_000 + '";')
        t = time.monotonic()
        self.assertEqual(verify(self.proj, self.apk), [])
        self.assertLess(time.monotonic() - t, 5)

    def test_long_line_checked_bounded(self):
        put(self.proj, 'Assets/Scripts/L.cs', 'var s = "' + 'a' * 1_000_000 + '";')
        t = time.monotonic()
        self.assertEqual(verify(self.proj, self.apk), [])
        self.assertLess(time.monotonic() - t, 5)

    def test_huge_spec_string_bounded(self):
        spec = put(self.tmp(), 'spec.json', json.dumps({'k': 'a' * 300_000}))
        t = time.monotonic()
        self.assertEqual(verify(self.proj, self.apk, spec), [])
        self.assertLess(time.monotonic() - t, 5)

    def test_missing_apk_dir_not_vacuous(self):
        out = verify(self.proj, os.path.join(self.apk, 'nope'))
        self.assertEqual(out, ['apk assets/res not found: asset-copy check could not run'])

    def test_symlinked_apk_dir_works(self):
        link = os.path.join(self.tmp(), 'link'); os.symlink(self.apk, link)
        put(self.proj, 'Assets/Art/x.bin', PNG)
        out = verify(self.proj, link)
        self.assertEqual(len(out), 1); self.assertIn('x.bin', out[0])
        parent = self.tmp(); os.rmdir(parent); os.symlink(os.path.dirname(self.apk), parent); self.addCleanup(os.unlink, parent)
        out = verify(self.proj, os.path.join(parent, os.path.basename(self.apk)))
        self.assertEqual(len(out), 1); self.assertIn('x.bin', out[0])

    def test_dangling_symlink_unreadable_continues(self):
        os.symlink(os.path.join(self.proj, 'gone'), os.path.join(self.proj, 'Assets', 'dead.cs'))
        put(self.proj, 'Assets/Scripts/B.cs', 'var x = {"apiKey": "abcd1234efgh"};')
        out = verify(self.proj, self.apk)
        self.assertIn('unreadable: ' + os.path.join('Assets', 'dead.cs'), out)
        self.assertTrue(any('B.cs:1' in p for p in out))

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root ignores file modes')
    def test_mode_000_file_unreadable_continues(self):
        p = put(self.proj, 'Assets/Scripts/Locked.cs', 'class L {}' * 20); os.chmod(p, 0)
        self.addCleanup(os.chmod, p, 0o600)
        put(self.proj, 'Assets/Scripts/B.cs', 'var x = {"apiKey": "abcd1234efgh"};')
        out = verify(self.proj, self.apk)
        self.assertIn('unreadable: ' + os.path.join('Assets', 'Scripts', 'Locked.cs'), out)
        self.assertTrue(any('B.cs:1' in p for p in out))

    def test_missing_spec_unreadable(self):
        self.assertEqual(verify(self.proj, self.apk, os.path.join(self.tmp(), 'spec.json')), ['spec.json unreadable'])

    def test_invalid_json_spec_unreadable(self):
        spec = put(self.tmp(), 'spec.json', '{not json')
        self.assertEqual(verify(self.proj, self.apk, spec), ['spec.json unreadable'])

    def test_oversized_spec_key_flagged(self):
        spec = put(self.tmp(), 'spec.json', json.dumps({'a': [{'k' * 5000: 1}]}))
        self.assertEqual(verify(self.proj, self.apk, spec), ['spec.json has an oversized key'])

    def test_many_blob_lines_fast(self):
        put(self.proj, 'Assets/Scripts/M.cs', ('a' * 4000 + '\n') * 400)
        t = time.monotonic()
        self.assertEqual(verify(self.proj, self.apk), [])
        self.assertLess(time.monotonic() - t, 5)

class VerifyAssetsDumpTests(unittest.TestCase):
    """exact-value cross-check against assets_dump (FAKE values only)"""
    def tmp(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True); return d

    def setUp(self):
        self.apk, self.proj, self.wd = self.tmp(), self.tmp(), self.tmp()
        put(self.apk, 'assets/tex.png', PNG)
        put(self.proj, 'Assets/Scripts/A.cs', 'class A {}')
        put(self.wd, 'assets_dump/mono/Cfg.json', json.dumps({'PassCheat': 'FAKEcheat-9999', 'a': {'sdkKey': 'FAKEsdk-0001'}, 'short': 'ab', 'done': '<REDACTED>', 'pin': 1234567}))
        self.spec = put(self.wd, 'spec.json', json.dumps({'secrets': [
            {'file': 'mono/Cfg.json', 'key': 'PassCheat'}, {'file': 'mono/Cfg.json', 'key': 'sdkKey'},
            {'file': 'mono/Cfg.json', 'key': 'short'}, {'file': 'mono/Cfg.json', 'key': 'done'}, {'file': 'mono/Cfg.json', 'key': 'pin'}]}))
        self.dump = os.path.join(self.wd, 'assets_dump')

    def run_verify(self, **kw): return verify(self.proj, self.apk, self.spec, assets_dump=self.dump, **kw)

    def assert_no_values(self, out):
        for p in out:
            for v in ('FAKEcheat-9999', 'FAKEsdk-0001', '1234567'): self.assertNotIn(v, p)

    def test_clean(self): self.assertEqual(self.run_verify(), [])

    def test_value_in_module_cs_detected(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'class B { const string P = "FAKEcheat-9999"; }')
        out = self.run_verify()
        self.assertEqual(len(out), 1); self.assertIn('PassCheat', out[0]); self.assertIn('mono/Cfg.json', out[0]); self.assertIn('B.cs', out[0])
        self.assert_no_values(out)

    def test_value_in_rules_and_index_detected(self):
        put(self.wd, 'rules.md', 'the code is FAKEsdk-0001 ok'); put(self.wd, 'spec_index.md', 'cheat FAKEcheat-9999')
        out = self.run_verify()
        self.assertTrue(any('sdkKey' in p and 'rules.md' in p for p in out))
        self.assertTrue(any('PassCheat' in p and 'spec_index.md' in p for p in out))
        self.assert_no_values(out)

    def test_value_in_spec_json_detected(self):
        put(self.wd, 'spec.json', json.dumps({'secrets': [{'file': 'mono/Cfg.json', 'key': 'PassCheat'}], 'x': 'FAKEcheat-9999'}))
        out = self.run_verify()
        self.assertTrue(any('PassCheat' in p and 'spec.json' in p for p in out)); self.assert_no_values(out)

    def test_extra_text_files_and_digits(self):
        extra = put(self.tmp(), 'module/G.cs', 'int pin = 1234567;')
        out = self.run_verify(extra_text_files=[extra])
        self.assertEqual(len(out), 1); self.assertIn('pin', out[0]); self.assert_no_values(out)

    def test_without_assets_dump_behaves_as_before(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'class B { const string P = "FAKEcheat-9999"; }')
        self.assertEqual(verify(self.proj, self.apk, self.spec), [])

    def test_short_and_redacted_values_ignored(self):
        put(self.proj, 'Assets/Scripts/B.cs', 'var s = "ab"; var r = "<REDACTED>"; var n = 123456;')
        self.assertEqual(self.run_verify(), [])

    def test_missing_dump_file_skipped(self):
        put(self.wd, 'spec.json', json.dumps({'secrets': [{'file': 'mono/gone.json', 'key': 'k'}]}))
        self.assertEqual(self.run_verify(), [])

class VerifyValueRobustnessTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True); return d

    def setUp(self):
        self.apk, self.proj, self.wd = self.tmp(), self.tmp(), self.tmp()
        put(self.apk, 'assets/tex.png', PNG); put(self.proj, 'Assets/Scripts/A.cs', 'class A {}')
        self.dump = os.path.join(self.wd, 'assets_dump')

    def spec(self, dump_obj, entries):
        put(self.wd, 'assets_dump/c.json', json.dumps(dump_obj))
        return put(self.wd, 'spec.json', json.dumps({'secrets': [{'file': 'c.json', 'key': k} for k in entries]}))

    def run_verify(self, spec): return verify(self.proj, self.apk, spec, assets_dump=self.dump)

    def test_over_matched_key_cannot_starve_real_secret(self):
        spec = self.spec({'aaaPass': ['fake-common-%04d' % i for i in range(250)], 'zzzSdkKey': 'FAKErealvalue-77'}, ['aaaPass', 'zzzSdkKey'])
        put(self.proj, 'Assets/Scripts/B.cs', 'const string K = "FAKErealvalue-77";')
        out = self.run_verify(spec)
        self.assertEqual(len(out), 1); self.assertIn('zzzSdkKey', out[0]); self.assertNotIn('FAKErealvalue-77', out[0])

    def test_twenty_thousand_values_fast(self):
        data = {'k%03dPass' % i: ['fake-%03d-value-%03d' % (i, j) for j in range(50)] for i in range(400)}
        spec = self.spec(data, list(data))
        for i in range(5): put(self.proj, 'Assets/Scripts/F%d.cs' % i, 'class F {}' * 100)
        t = time.monotonic(); out = self.run_verify(spec)
        self.assertEqual(out, []); self.assertLess(time.monotonic() - t, 3)

    def test_long_value_checked_by_prefix(self):
        v = 'FAKElong-' + 'x' * 400
        spec = self.spec({'sdkKey': v}, ['sdkKey'])
        put(self.proj, 'Assets/Scripts/B.cs', 'var s = "' + v[:200] + 'DIFFERENT-TAIL";')
        out = self.run_verify(spec); self.assertEqual(len(out), 1); self.assertNotIn('xxxx', out[0])

    def test_any_file_type_scanned_as_bytes(self):
        spec = self.spec({'sdkKey': 'FAKE-sdk-value-1'}, ['sdkKey'])
        for rel in ('Assets/a.xml', 'Assets/b.asset', 'Assets/c.bytes'): put(self.proj, rel, b'\x00\x01FAKE-sdk-value-1\xff')
        out = self.run_verify(spec); self.assertEqual(len(out), 3)
        for rel in ('a.xml', 'b.asset', 'c.bytes'): self.assertTrue(any(rel in p for p in out))

    def test_unreadable_project_file_is_reported_once(self):
        spec = self.spec({'sdkKey': 'FAKE-sdk-value-1'}, ['sdkKey'])
        os.symlink(os.path.join(self.proj, 'gone'), os.path.join(self.proj, 'Assets', 'dead.cs'))
        self.assertEqual(self.run_verify(spec), ['unreadable: ' + os.path.join('Assets', 'dead.cs')])

    def test_flag_words_and_short_alpha_not_secret_values(self):
        spec = self.spec({'passType': 'true', 'passMode': 'full', 'passNo': 'No', 'dbgPass': 'null'}, ['passType', 'passMode', 'passNo', 'dbgPass'])
        put(self.proj, 'Assets/Scripts/B.cs', 'bool a = true; var m = "full"; object n = null; var x = "No";')
        self.assertEqual(self.run_verify(spec), [])

    def test_eligibility_boundaries_still_checked(self):
        spec = self.spec({'sdkKey': 'abcdefghijk', 'passCode': 'ab12cd'}, ['sdkKey', 'passCode'])
        put(self.proj, 'Assets/Scripts/B.cs', 'var a = "abcdefghijk"; var b = "ab12cd";')
        self.assertEqual(len(self.run_verify(spec)), 2)

    def test_list_values_and_kv_pair_shape(self):
        spec = self.spec({'keys': [{'key': 'PassCheat', 'value': 'FAKEkv-value-9'}], 'pins': {'sdkKeys': ['FAKElist-val-1']}}, ['PassCheat', 'sdkKeys'])
        put(self.proj, 'Assets/Scripts/B.cs', 'var a = "FAKEkv-value-9"; var b = "FAKElist-val-1";')
        out = self.run_verify(spec); self.assertEqual(len(out), 2)

if __name__ == '__main__': unittest.main()
