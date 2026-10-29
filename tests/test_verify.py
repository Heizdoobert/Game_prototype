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
        self.assertTrue(any('B.cs' in p for p in verify(self.proj, self.apk)))

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

if __name__ == '__main__': unittest.main()
