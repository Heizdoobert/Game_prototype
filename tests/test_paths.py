import os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock
from apk2proto import paths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class PathsTests(unittest.TestCase):
    def test_redact_missing_kit_exits_with_message(self):
        kit = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, kit, ignore_errors=True)
        with mock.patch.object(paths, 'KIT', kit), mock.patch.dict(sys.modules):
            sys.modules.pop('redact', None)
            with self.assertRaises(SystemExit) as cm: paths.redact()
        self.assertIn('game_re_kit not found at ' + kit, str(cm.exception)); self.assertIn('GRE_KIT', str(cm.exception))

    def test_modules_import_without_kit(self):
        r = subprocess.run([sys.executable, '-c', 'import apk2proto.distill, apk2proto.verify, apk2proto.runner'],
                           cwd=ROOT, env=dict(os.environ, GRE_KIT='/nonexistent'), capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stderr), (0, ''))

if __name__ == '__main__': unittest.main()
