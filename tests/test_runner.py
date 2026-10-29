import argparse, os, shutil, subprocess, tempfile, unittest
from unittest import mock
from apk2proto import doctor as DR, runner
from apk2proto.runner import Stage

def args(wd, **kw):
    d = dict(apk='g.apk', workdir=wd, module=None, start=None, only=None, force=False); d.update(kw)
    return argparse.Namespace(**d)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.wd, self.calls = tempfile.mkdtemp(), []
        self.addCleanup(shutil.rmtree, self.wd, ignore_errors=True)

    def stage(self, name, key='k', exists=None, boom=None):
        def fn(wd, a):
            self.calls.append(name)
            if boom: raise boom
        return Stage(name, fn, lambda wd, a: key, exists)

    def test_runs_in_order_then_skips_unchanged(self):
        st = [self.stage('a'), self.stage('b')]
        self.assertEqual(runner.run(args(self.wd), st), 0); self.assertEqual(self.calls, ['a', 'b'])
        runner.run(args(self.wd), st); self.assertEqual(self.calls, ['a', 'b'])          # skipped

    def test_force_and_only(self):
        st = [self.stage('a'), self.stage('b')]; runner.run(args(self.wd), st); self.calls.clear()
        runner.run(args(self.wd, only='b'), st); self.assertEqual(self.calls, ['b'])      # only runs even if done
        self.calls.clear(); runner.run(args(self.wd, force=True), st); self.assertEqual(self.calls, ['a', 'b'])

    def test_start_skips_earlier_stages(self):
        runner.run(args(self.wd, start='b'), [self.stage('a'), self.stage('b')]); self.assertEqual(self.calls, ['b'])

    def test_exists_predicate_skips_without_state(self):
        runner.run(args(self.wd), [self.stage('a', exists=lambda wd: True), self.stage('b')]); self.assertEqual(self.calls, ['b'])

    def test_none_key_never_skips(self):
        st = [Stage('i', lambda wd, a: self.calls.append('i'), lambda wd, a: None, None)]
        runner.run(args(self.wd), st); runner.run(args(self.wd), st); self.assertEqual(self.calls, ['i', 'i'])

    def test_pause_returns_3_and_resumes(self):
        st = [self.stage('a'), self.stage('author', boom=runner.Paused()), self.stage('z')]
        self.assertEqual(runner.run(args(self.wd), st), 3); self.assertEqual(self.calls, ['a', 'author'])
        st[1] = self.stage('author'); self.calls.clear()
        self.assertEqual(runner.run(args(self.wd), st), 0); self.assertEqual(self.calls, ['author', 'z'])

    def test_called_process_error_returns_1(self):
        st = [self.stage('a', boom=subprocess.CalledProcessError(7, ['dotnet', 'run'])), self.stage('z')]
        with mock.patch('builtins.print') as pr:
            self.assertEqual(runner.run(args(self.wd), st), 1)
        self.assertEqual(self.calls, ['a'])
        msgs = [' '.join(map(str, c.args)) for c in pr.call_args_list]
        self.assertIn('stage a failed (exit 7): dotnet run', msgs)

    def test_failed_stage_is_not_marked_done(self):
        runner.run(args(self.wd), [self.stage('a', boom=subprocess.CalledProcessError(1, ['x']))])
        self.calls.clear(); runner.run(args(self.wd), [self.stage('a')]); self.assertEqual(self.calls, ['a'])

    def test_system_exit_propagates(self):
        with self.assertRaises(SystemExit) as cm: runner.run(args(self.wd), [self.stage('a', boom=SystemExit('nope'))])
        self.assertEqual(str(cm.exception), 'nope')

    def test_stage_names_and_order(self):
        self.assertEqual([s.name for s in runner.STAGES],
                         ['detect', 'dump', 'distill', 'author', 'scaffold', 'test', 'verify', 'build', 'install'])

class AuthorTests(unittest.TestCase):
    def test_pause_message_mentions_spec_path(self):
        wd = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, wd, ignore_errors=True)
        with mock.patch('builtins.print') as pr, self.assertRaises(runner.Paused):
            runner.st_author(runner.Workdir(wd), args(wd))
        out = ' '.join(str(c.args[0]) for c in pr.call_args_list)
        self.assertIn(os.path.join(wd, 'spec.json'), out); self.assertIn('spec_index.md', out)

class EngineTests(unittest.TestCase):
    def check(self, text):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = os.path.join(d, 'engine.txt')
        with open(p, 'w') as fh: fh.write(text)
        return runner._check_engine(p)

    def test_unity_ok(self): self.check('Unity\n2022.3\n')
    def test_other_engine_rejected(self):
        with self.assertRaises(SystemExit) as cm: self.check('Cocos\n')
        self.assertIn("'Cocos'", str(cm.exception)); self.assertIn('not supported', str(cm.exception))

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.wd = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.wd, ignore_errors=True)
        self.w, self.a = runner.Workdir(self.wd), args(self.wd)

    def all_ok(self): return [(True, n, 'fix') for n in ('dotnet', 'adb') + tuple(runner.BUILD_CHECKS)]

    def test_build_checks_exist_in_doctor(self):
        self.assertTrue(set(runner.BUILD_CHECKS) <= {n for _, n, _ in DR.checks()})

    def test_refuses_on_failing_checks(self):
        bad = [(False, 'NDK ' + DR.NDK, 'sdkmanager it')] + self.all_ok()
        with mock.patch.object(DR, 'checks', return_value=bad), mock.patch.object(runner, 'subprocess') as sp:
            with self.assertRaises(SystemExit) as cm: runner.st_build(self.w, self.a)
        self.assertIn('MISS NDK ' + DR.NDK + ' -> sdkmanager it', str(cm.exception)); sp.run.assert_not_called()

    def test_missing_adb_does_not_block_build(self):
        checks = [(False, 'adb', 'install adb')] + self.all_ok()
        with mock.patch.object(DR, 'checks', return_value=checks), mock.patch.object(runner, '_mem_available_mb', return_value=100):
            with self.assertRaises(SystemExit) as cm: runner.st_build(self.w, self.a)
        self.assertNotIn('adb', str(cm.exception)); self.assertIn('100', str(cm.exception))

    def test_refuses_on_low_memory(self):
        with mock.patch.object(DR, 'checks', return_value=self.all_ok()), \
             mock.patch.object(runner, '_mem_available_mb', return_value=1200), mock.patch.object(runner, 'subprocess') as sp:
            with self.assertRaises(SystemExit) as cm: runner.st_build(self.w, self.a)
        self.assertIn('1200', str(cm.exception)); self.assertIn(str(runner.MIN_MEM_MB), str(cm.exception)); sp.run.assert_not_called()

if __name__ == '__main__': unittest.main()
