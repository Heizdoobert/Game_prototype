import json, os, shutil, tempfile, unittest
from apk2proto import paths
from apk2proto.scaffold import scaffold


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        fh.write(text)


def mk_module(root, with_game=True):
    write(os.path.join(root, 'module.json'), json.dumps({'id': 'demo', 'name': 'Demo Game'}))
    if with_game:
        write(os.path.join(root, 'View', 'GameModule.cs'), '// m')
    write(os.path.join(root, 'Core', 'X.cs'), '// x')
    write(os.path.join(root, 'Tests', 'XTests.cs'), '// t')


class ScaffoldTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def test_layout_and_build_json(self):
        m, p = self.tmp(), os.path.join(self.tmp(), 'proto')
        mk_module(m)
        meta = scaffold(p, paths.TEMPLATE, m)
        self.assertEqual(meta['id'], 'demo')
        for rel in ('Assets/Scripts/Shell/View/App.cs', 'Assets/Scripts/Game/Core/X.cs',
                    'Assets/Scripts/Game/View/GameModule.cs', 'Tests~/Core.Tests/Game/XTests.cs',
                    'Packages/manifest.json'):
            self.assertTrue(os.path.exists(os.path.join(p, rel)), rel)
        with open(os.path.join(p, 'build.json')) as fh:
            self.assertEqual(json.load(fh), {'product': 'Demo Game', 'appId': 'com.proto.demo'})

    def test_rescaffold_replaces_game_files_keeps_unity_state(self):
        m, p = self.tmp(), os.path.join(self.tmp(), 'proto')
        mk_module(m)
        scaffold(p, paths.TEMPLATE, m)
        write(os.path.join(p, 'Library', 'x'), 'cache')
        write(os.path.join(p, 'Builds', 'a.apk'), 'apk')
        write(os.path.join(p, 'Assets/Scripts/Shell/View/App.cs.meta'), 'meta')
        os.remove(os.path.join(m, 'Core', 'X.cs'))
        write(os.path.join(m, 'Core', 'Y.cs'), '// y')
        scaffold(p, paths.TEMPLATE, m)
        self.assertFalse(os.path.exists(os.path.join(p, 'Assets/Scripts/Game/Core/X.cs')))
        self.assertTrue(os.path.exists(os.path.join(p, 'Assets/Scripts/Game/Core/Y.cs')))
        for rel in ('Library/x', 'Builds/a.apk', 'Assets/Scripts/Shell/View/App.cs.meta'):
            self.assertTrue(os.path.exists(os.path.join(p, rel)), rel)

    def test_missing_game_module_refused(self):
        m = self.tmp()
        mk_module(m, with_game=False)
        with self.assertRaises(SystemExit):
            scaffold(os.path.join(self.tmp(), 'p'), paths.TEMPLATE, m)


if __name__ == '__main__':
    unittest.main()
