import os, shutil, tempfile, unittest
from unittest import mock
from apk2proto import doctor

JDK = 'JDK 17 (JAVA_HOME or Unity bundled)'
FIX = 'install JDK 17 or set JAVA_HOME to it'

def fake_jdk(root, name, version):
    d = os.path.join(root, name); os.makedirs(d)
    with open(os.path.join(d, 'release'), 'w') as fh: fh.write('JAVA_VERSION="%s"\n' % version)
    return d

class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.sdk = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.sdk, ignore_errors=True)
        self.jvm = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.jvm, ignore_errors=True)
        self.old = dict(os.environ)
        os.environ['ANDROID_SDK_ROOT'] = self.sdk; os.environ.pop('JAVA_HOME', None)
        for p in (mock.patch.object(doctor, 'JVM_DIR', self.jvm),
                  mock.patch.object(doctor.paths, 'unity_editor', return_value=None)):
            p.start(); self.addCleanup(p.stop)
    def tearDown(self): os.environ.clear(); os.environ.update(self.old)

    def result(self, name):
        return next(ok for ok, n, _ in doctor.checks() if n == name)

    def test_cmdline_tools_rule(self):
        ct = os.path.join(self.sdk, 'cmdline-tools'); os.makedirs(os.path.join(ct, '16.0'))
        self.assertTrue(self.result('cmdline-tools has only 16.0'))
        os.makedirs(os.path.join(ct, '23.0'))
        self.assertFalse(self.result('cmdline-tools has only 16.0'))

    def test_symlink_latest_allowed(self):
        ct = os.path.join(self.sdk, 'cmdline-tools'); os.makedirs(os.path.join(ct, '16.0'))
        os.symlink('16.0', os.path.join(ct, 'latest'))
        self.assertTrue(self.result('cmdline-tools has only 16.0'))

    def test_ndk_and_env(self):
        self.assertFalse(self.result('NDK 27.2.12479018'))
        os.makedirs(os.path.join(self.sdk, 'ndk', '27.2.12479018'))
        self.assertTrue(self.result('NDK 27.2.12479018'))
        self.assertEqual(doctor.android_env()['ANDROID_NDK_ROOT'], os.path.join(self.sdk, 'ndk', '27.2.12479018'))

    def test_java_home_wins(self):
        fake_jdk(self.jvm, 'java-17-openjdk-amd64', '17.0.1')
        j = fake_jdk(self.sdk, 'mine', '17.0.9')
        os.environ['JAVA_HOME'] = j
        self.assertEqual(doctor.android_env()['JAVA_HOME'], j)
        self.assertTrue(self.result(JDK))

    def test_jdk17_found_under_jvm_dir(self):
        fake_jdk(self.jvm, 'java-25-openjdk-amd64', '25.0.1')
        j = fake_jdk(self.jvm, 'java-17-openjdk-amd64', '17.0.20.1')
        self.assertEqual(doctor.android_env()['JAVA_HOME'], j)
        self.assertTrue(self.result(JDK))

    def test_jdk25_only_fails(self):
        fake_jdk(self.jvm, 'java-25-openjdk-amd64', '25.0.1')
        self.assertFalse(self.result(JDK))
        self.assertNotIn('JAVA_HOME', doctor.android_env())
        self.assertEqual(next(f for ok, n, f in doctor.checks() if n == JDK), FIX)

    def test_no_jdk_no_java_home(self):
        self.assertFalse(self.result(JDK))
        self.assertNotIn('JAVA_HOME', doctor.android_env())

    def test_non17_java_home_not_exported(self):
        os.environ['JAVA_HOME'] = fake_jdk(self.sdk, 'j25', '25.0.1')
        self.assertFalse(self.result(JDK))
        self.assertNotIn('JAVA_HOME', doctor.android_env())

    def test_missing_release_file_fails(self):
        os.makedirs(os.path.join(self.jvm, 'java-17-openjdk-amd64'))
        self.assertFalse(self.result(JDK))

if __name__ == '__main__': unittest.main()
