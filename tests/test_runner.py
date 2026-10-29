import argparse, contextlib, io, json, os, shutil, subprocess, tempfile, unittest
from unittest import mock
from apk2proto import doctor as DR, runner
from apk2proto.runner import Stage

def args(wd, **kw):
    d = dict(apk='g.apk', workdir=wd, module=None, start=None, only=None, force=False); d.update(kw)
    return argparse.Namespace(**d)

def qrun(a, st=None):
    with contextlib.redirect_stdout(io.StringIO()): return runner.run(a, st)

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
        self.assertEqual(qrun(args(self.wd), st), 0); self.assertEqual(self.calls, ['a', 'b'])
        qrun(args(self.wd), st); self.assertEqual(self.calls, ['a', 'b'])          # skipped

    def test_force_and_only(self):
        st = [self.stage('a'), self.stage('b')]; qrun(args(self.wd), st); self.calls.clear()
        qrun(args(self.wd, only='b'), st); self.assertEqual(self.calls, ['b'])      # only runs even if done
        self.calls.clear(); qrun(args(self.wd, force=True), st); self.assertEqual(self.calls, ['a', 'b'])

    def test_start_skips_earlier_stages(self):
        qrun(args(self.wd, start='b'), [self.stage('a'), self.stage('b')]); self.assertEqual(self.calls, ['b'])

    def test_exists_predicate_skips_without_state(self):
        qrun(args(self.wd), [self.stage('a', exists=lambda wd: True), self.stage('b')]); self.assertEqual(self.calls, ['b'])

    def test_none_key_never_skips(self):
        st = [Stage('i', lambda wd, a: self.calls.append('i'), lambda wd, a: None, None)]
        qrun(args(self.wd), st); qrun(args(self.wd), st); self.assertEqual(self.calls, ['i', 'i'])

    def test_pause_returns_3_and_resumes(self):
        st = [self.stage('a'), self.stage('author', boom=runner.Paused()), self.stage('z')]
        self.assertEqual(qrun(args(self.wd), st), 3); self.assertEqual(self.calls, ['a', 'author'])
        st[1] = self.stage('author'); self.calls.clear()
        self.assertEqual(qrun(args(self.wd), st), 0); self.assertEqual(self.calls, ['author', 'z'])

    def test_called_process_error_returns_1(self):
        st = [self.stage('a', boom=subprocess.CalledProcessError(7, ['dotnet', 'run'])), self.stage('z')]
        with mock.patch('builtins.print') as pr:
            self.assertEqual(qrun(args(self.wd), st), 1)
        self.assertEqual(self.calls, ['a'])
        msgs = [' '.join(map(str, c.args)) for c in pr.call_args_list]
        self.assertIn('stage a failed (exit 7): dotnet run', msgs)

    def test_failed_stage_is_not_marked_done(self):
        qrun(args(self.wd), [self.stage('a', boom=subprocess.CalledProcessError(1, ['x']))])
        self.calls.clear(); qrun(args(self.wd), [self.stage('a')]); self.assertEqual(self.calls, ['a'])

    def test_system_exit_propagates(self):
        with self.assertRaises(SystemExit) as cm: qrun(args(self.wd), [self.stage('a', boom=SystemExit('nope'))])
        self.assertEqual(str(cm.exception), 'nope')

    def test_changed_key_input_reruns(self):
        key = ['k1']
        st = [Stage('a', lambda wd, a: self.calls.append('a'), lambda wd, a: key[0], None)]
        qrun(args(self.wd), st); qrun(args(self.wd), st); self.assertEqual(self.calls, ['a'])
        key[0] = 'k2'; qrun(args(self.wd), st); self.assertEqual(self.calls, ['a', 'a'])

    def test_none_key_recomputed_after_stage_is_marked(self):
        made = []
        def key(wd, a): return 'built' if made else None            # like build: the key needs the stage's output
        st = [Stage('b', lambda wd, a: (made.append(1), self.calls.append('b')), key, None)]
        qrun(args(self.wd), st); qrun(args(self.wd), st); self.assertEqual(self.calls, ['b'])

    def test_from_does_not_mark_earlier_stages(self):
        qrun(args(self.wd, start='b'), [self.stage('a'), self.stage('b')])
        w = runner.Workdir(self.wd); self.assertFalse(w.is_done('a', 'k')); self.assertTrue(w.is_done('b', 'k'))

    def test_lock_released_after_stage_raises(self):
        with self.assertRaises(SystemExit): qrun(args(self.wd), [self.stage('a', boom=SystemExit('x'))])
        with runner.Workdir(self.wd).lock(): pass

    def test_unknown_stage_rejected_before_anything_runs(self):
        for kw in ({'start': 'nope'}, {'only': 'nope'}):
            with self.assertRaises(SystemExit) as cm: qrun(args(self.wd, **kw), [self.stage('a'), self.stage('b')])
            self.assertEqual(str(cm.exception), 'unknown stage nope; stages: a, b')
        self.assertEqual(self.calls, [])

    def test_missing_tool_returns_1(self):
        e = FileNotFoundError(2, 'No such file', 'dotnet')
        with mock.patch('builtins.print') as pr: self.assertEqual(runner.run(args(self.wd), [self.stage('a', boom=e)]), 1)
        self.assertIn('stage a failed: dotnet not found', [' '.join(map(str, c.args)) for c in pr.call_args_list])

    def test_stage_names_and_order(self):
        self.assertEqual([s.name for s in runner.STAGES],
                         ['detect', 'dump', 'distill', 'author', 'scaffold', 'test', 'verify', 'build', 'install'])

class AuthorTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.wd = runner.Workdir(self.d)

    def put(self, *rel):
        p = os.path.join(self.d, *rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as fh: fh.write('x')

    def pause_text(self):
        with mock.patch('builtins.print') as pr, self.assertRaises(runner.Paused):
            runner.st_author(self.wd, args(self.d))
        return ' '.join(str(c.args[0]) for c in pr.call_args_list)

    def test_pause_message_lists_everything_the_author_needs(self):
        out = self.pause_text()
        for want in (os.path.join(self.d, 'spec.json'), 'spec_index.md', os.path.join(self.d, 'rules.md'),
                     os.path.join(runner.paths.ROOT, 'template', 'Assets', 'Scripts', 'Shell', 'View', 'IGameModule.cs'),
                     os.path.join(runner.paths.ROOT, 'modules', 'candyjam')):
            self.assertIn(want, out)
        self.assertTrue(os.path.isfile(os.path.join(runner.paths.ROOT, 'template', 'Assets', 'Scripts', 'Shell', 'View', 'IGameModule.cs')))
        self.assertTrue(os.path.isdir(os.path.join(runner.paths.ROOT, 'modules', 'candyjam')))

    def test_module_without_rules_md_still_pauses(self):
        self.put('module', 'View', 'GameModule.cs'); self.pause_text()

    def test_rules_md_without_module_still_pauses(self):
        self.put('rules.md'); self.pause_text()

    def test_complete_authoring_continues(self):
        self.put('module', 'View', 'GameModule.cs'); self.put('rules.md'); runner.st_author(self.wd, args(self.d))

class DetectDumpTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.wd = runner.Workdir(self.d)
        self.detect = [s for s in runner.STAGES if s.name == 'detect'][0]

    def engine(self, text, apk=True):
        with open(self.wd.p('engine.txt'), 'w') as fh: fh.write(text)
        if apk: os.makedirs(self.wd.p('apk'), exist_ok=True)

    def test_exists_false_for_unsupported_engine(self):
        self.engine('Cocos\n'); self.assertFalse(self.detect.exists(self.wd))

    def test_exists_true_for_unity(self):
        self.engine('Unity\n2022\nIL2CPP -> use bin/il2cpp_dump.sh'); self.assertTrue(self.detect.exists(self.wd))

    def test_exists_false_for_unity_mono(self):
        self.engine('Unity\n2022\nMono'); self.assertFalse(self.detect.exists(self.wd))

    def test_exists_false_without_apk_dir_or_engine(self):
        self.assertFalse(self.detect.exists(self.wd)); self.engine('Unity\n', apk=False); self.assertFalse(self.detect.exists(self.wd))

    def run_dump(self, rc):
        done = subprocess.CompletedProcess([], rc)
        with mock.patch.object(runner.subprocess, 'run', return_value=done) as run, mock.patch.object(runner, '_need'), \
             contextlib.redirect_stdout(io.StringIO()):
            runner.st_dump(self.wd, args(self.d))
        self.assertFalse(run.call_args.kwargs['check'])

    def test_dump_without_dump_cs_fails(self):
        with self.assertRaises(SystemExit) as cm: self.run_dump(1)
        self.assertEqual(str(cm.exception), 'dump produced no il2cpp/dump.cs (kit exit 1)')

    def test_dump_with_dump_cs_ok_even_if_kit_exits_1(self):
        os.makedirs(self.wd.p('il2cpp'))
        with open(self.wd.p('il2cpp', 'dump.cs'), 'w') as fh: fh.write('x')
        self.run_dump(1); self.run_dump(0)

class KitCheckTests(unittest.TestCase):
    def test_detect_and_dump_refuse_without_kit(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        wd = runner.Workdir(d)
        bad = [(False, 'game_re_kit found', 'set GRE_KIT')]
        for fn in (runner.st_detect, runner.st_dump):
            with mock.patch.object(DR, 'checks', return_value=bad), mock.patch.object(runner, 'sh') as sh:
                with self.assertRaises(SystemExit) as cm: fn(wd, args(d))
            self.assertIn('MISS game_re_kit found -> set GRE_KIT', str(cm.exception)); sh.assert_not_called()

    def test_check_name_sets_exist_in_doctor(self):
        names = {n for _, n, _ in DR.checks()}
        self.assertTrue(set(runner.DUMP_CHECKS) <= names); self.assertIn('Unity Android module', runner.BUILD_CHECKS)

class KeyTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.wd, self.a = runner.Workdir(self.d), args(self.d)
        self.st = {s.name: s for s in runner.STAGES}

    def put(self, rel, text='x'):
        p = self.wd.p(*rel.split('/')); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as fh: fh.write(text)

    def test_none_without_proto_or_apk(self):
        for n in ('test', 'verify', 'build'): self.assertIsNone(self.st[n].key(self.wd, self.a))

    def test_verify_never_skips(self):
        for rel in ('proto/Assets/Scripts/A.cs', 'proto/build.json', 'spec.json'): self.put(rel)
        self.assertIsNone(self.st['verify'].key(self.wd, self.a))

    def test_meta_and_scene_do_not_change_keys(self):
        for rel in ('proto/Assets/Scripts/A.cs', 'proto/Assets/Editor/B.cs', 'proto/build.json', 'proto/Builds/game.apk'): self.put(rel)
        before = {n: self.st[n].key(self.wd, self.a) for n in ('test', 'build')}
        self.assertTrue(all(before.values()))
        self.put('proto/Assets/Scenes/Main.unity', 'rewritten'); self.put('proto/Assets/Scripts/A.cs.meta')
        self.assertEqual(before, {n: self.st[n].key(self.wd, self.a) for n in before})
        self.put('proto/Assets/Scripts/A.cs', 'changed!')
        self.assertTrue(all(before[n] != self.st[n].key(self.wd, self.a) for n in before))

class VerifyStageTests(unittest.TestCase):
    def test_passes_assets_dump_and_module_files(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        wd = runner.Workdir(d)
        for rel in ('module/Core/A.cs', 'module/Library/skip.cs', 'module/img.png'):
            os.makedirs(wd.p(*rel.split('/')[:-1]), exist_ok=True)
            with open(wd.p(*rel.split('/')), 'w') as fh: fh.write('x')
        with mock.patch.object(runner.V, 'verify', return_value=[]) as v: runner.st_verify(wd, args(d))
        kw = v.call_args.kwargs
        self.assertEqual(kw['assets_dump'], wd.p('assets_dump'))
        self.assertEqual(kw['extra_text_files'], [wd.p('module', 'Core', 'A.cs')])

class EngineTests(unittest.TestCase):
    def check(self, text):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = os.path.join(d, 'engine.txt')
        with open(p, 'w') as fh: fh.write(text)
        return runner._check_engine(p)

    def test_unity_il2cpp_ok(self): self.check('Unity\nIL2CPP -> use bin/il2cpp_dump.sh\n')
    def test_unity_mono_rejected(self):
        with self.assertRaises(SystemExit) as cm: self.check('Unity\n2022.3\nMono\n')
        self.assertEqual(str(cm.exception), 'Unity Mono backend is not supported yet (no IL2CPP dump); other backends are separate specs')
    def test_missing_engine_file_rejected(self):
        with self.assertRaises(SystemExit): runner._check_engine('/nonexistent/engine.txt')
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

class BuildRunTests(unittest.TestCase):
    OK = 'noise\nBUILD RESULT: Succeeded\n'

    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.w, self.a = runner.Workdir(self.d), args(self.d)
        self.log = self.w.p('build.log'); self.seen = {}
        checks = [(True, n, 'f') for n in runner.BUILD_CHECKS]
        for p in (mock.patch.object(DR, 'checks', return_value=checks), mock.patch.object(runner, '_mem_available_mb', return_value=9999),
                  mock.patch.object(runner.paths, 'unity_editor', return_value='/u/Unity')):
            p.start(); self.addCleanup(p.stop)

    def fake(self, text):
        def run(cmd, **kw):
            self.seen.update(cmd=cmd, env=kw.get('env'), existed=os.path.exists(self.log))
            if text is not None:
                with open(self.log, 'w') as fh: fh.write(text)
        return run

    def build(self, text):
        with mock.patch.object(runner.subprocess, 'run', side_effect=self.fake(text)): runner.st_build(self.w, self.a)

    def test_success_and_command_env(self):
        self.build(self.OK)
        self.assertTrue({'-batchmode', '-quit', '-nographics'} <= set(self.seen['cmd']))
        self.assertIn('ANDROID_NDK_ROOT', self.seen['env']); self.assertIn('ANDROID_SDK_ROOT', self.seen['env'])

    def test_missing_log_fails(self):
        with self.assertRaises(SystemExit): self.build(None)

    def test_log_without_success_line_fails_and_tails_log(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as cm:
            self.build(''.join('line%d\n' % i for i in range(30)))
        self.assertIn('build.log', str(cm.exception))
        self.assertIn('line29', out.getvalue()); self.assertIn('line25', out.getvalue()); self.assertNotIn('line24\n', out.getvalue())

    def test_failure_output_shows_errors_then_tail_within_25_lines(self):
        log = ''.join('noise %d\n' % i for i in range(100)) + ''.join('Assets/A.cs(%d): error CS0103: nope\n' % i for i in range(40)) \
            + 'Exception: boom\n' + ''.join('tail %d\n' % i for i in range(30))
        with contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit): self.build(log)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 25)
        self.assertEqual(sum('error CS' in l for l in lines), 20); self.assertIn('tail 29', lines); self.assertIn('tail 25', lines)
        self.assertFalse(any(l.startswith('noise') for l in lines))

    def test_stale_log_deleted_before_run(self):
        with open(self.log, 'w') as fh: fh.write(self.OK)
        with self.assertRaises(SystemExit): self.build(None)
        self.assertFalse(self.seen['existed'])

    def test_no_tail_when_log_missing(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit): self.build(None)
        self.assertEqual(out.getvalue(), '')

class MainTests(unittest.TestCase):
    def test_module_made_absolute(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        apk = os.path.join(d, 'g.apk')
        with open(apk, 'w') as fh: fh.write('x')
        with mock.patch.object(runner, 'run', return_value=0) as run:
            runner.main(['run', apk, os.path.join(d, 'wd'), '--module', 'rel/mod'])
        self.assertEqual(run.call_args.args[0].module, os.path.abspath('rel/mod'))


    def test_missing_apk_rejected_before_workdir_created(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        wd = os.path.join(d, 'wd')
        with self.assertRaises(SystemExit) as cm: runner.main(['run', os.path.join(d, 'nope.apk'), wd])
        self.assertIn('apk not found', str(cm.exception)); self.assertFalse(os.path.exists(wd))

if __name__ == '__main__': unittest.main()
