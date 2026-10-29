import contextlib, io, os, shutil, tempfile, unittest
from apk2proto.state import Workdir, fingerprint

class StateTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_mark_roundtrip_across_instances(self):
        w = Workdir(self.d); self.assertFalse(w.is_done('s', 'k'))
        w.mark('s', 'k'); self.assertTrue(Workdir(self.d).is_done('s', 'k'))
        self.assertFalse(Workdir(self.d).is_done('s', 'other'))

    def test_corrupt_state_is_empty_with_warning(self):
        for bad in ('{not json', '[1, 2]', ''):
            with open(os.path.join(self.d, 'state.json'), 'w') as fh: fh.write(bad)
            with contextlib.redirect_stdout(io.StringIO()) as out: w = Workdir(self.d)
            self.assertEqual(w.state, {}); self.assertIn('warning', out.getvalue()); self.assertIn('state.json', out.getvalue())
        w.mark('s', 'k'); self.assertTrue(Workdir(self.d).is_done('s', 'k'))      # recovers

    def test_lock_is_exclusive(self):
        w1, w2 = Workdir(self.d), Workdir(self.d)
        with w1.lock():
            with self.assertRaises(SystemExit):
                with w2.lock(): pass
        with w2.lock(): pass            # released

    def test_fingerprint_changes_with_content_size(self):
        f = os.path.join(self.d, 'a.txt')
        with open(f, 'w') as fh: fh.write('x')
        a = fingerprint(f)
        with open(f, 'w') as fh: fh.write('xy')
        self.assertNotEqual(a, fingerprint(f))
        self.assertNotEqual(fingerprint(f), fingerprint(os.path.join(self.d, 'missing')))

    def test_suffix_filter_ignores_meta_and_tracks_cs(self):
        a = os.path.join(self.d, 'A.cs')
        with open(a, 'w') as fh: fh.write('x')
        base = fingerprint(self.d, suffixes=('.cs',))
        with open(a + '.meta', 'w') as fh: fh.write('guid')
        self.assertEqual(base, fingerprint(self.d, suffixes=('.cs',)))
        self.assertNotEqual(base, fingerprint(self.d))               # unfiltered sees the .meta
        with open(a, 'w') as fh: fh.write('xyz')
        self.assertNotEqual(base, fingerprint(self.d, suffixes=('.cs',)))

    def test_suffix_filter_on_file_argument(self):
        j = os.path.join(self.d, 'a.json')
        with open(j, 'w') as fh: fh.write('x')
        a = fingerprint(j, suffixes=('.cs',))
        with open(j, 'w') as fh: fh.write('xyz')
        self.assertEqual(a, fingerprint(j, suffixes=('.cs',)))

if __name__ == '__main__': unittest.main()
