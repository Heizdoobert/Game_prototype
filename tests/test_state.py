import os, shutil, tempfile, unittest
from apk2proto.state import Workdir, fingerprint

class StateTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_mark_roundtrip_across_instances(self):
        w = Workdir(self.d); self.assertFalse(w.is_done('s', 'k'))
        w.mark('s', 'k'); self.assertTrue(Workdir(self.d).is_done('s', 'k'))
        self.assertFalse(Workdir(self.d).is_done('s', 'other'))

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

if __name__ == '__main__': unittest.main()
