import glob, os, re, shutil
from . import paths

NDK = '27.2.12479018'
JVM_DIR = '/usr/lib/jvm'
JDK_FIX = 'install JDK 17 or set JAVA_HOME to it'

def _sdk(): return os.environ.get('ANDROID_SDK_ROOT') or os.path.expanduser('~/Android/Sdk')

def _jdk():
    """JAVA_HOME, else the Unity-bundled OpenJDK, else the first system JDK 17. Not version-checked."""
    if os.environ.get('JAVA_HOME'): return os.environ['JAVA_HOME']
    ed = paths.unity_editor()
    if ed:
        bundled = os.path.join(os.path.dirname(ed), 'Data', 'PlaybackEngines', 'AndroidPlayer', 'OpenJDK')
        if os.path.isdir(bundled): return bundled
    found = sorted(glob.glob(os.path.join(JVM_DIR, 'java-17-*')))
    return found[0] if found else None

def _is_jdk17(jdk):
    # Unity 6 Android needs 17 (not 25); read <jdk>/release
    try:
        with open(os.path.join(jdk, 'release')) as fh: text = fh.read()
    except (OSError, TypeError): return False
    m = re.search(r'^JAVA_VERSION="(\d+)', text, re.M)
    return bool(m) and m.group(1) == '17'

def android_env():
    sdk, jdk = _sdk(), _jdk()
    env = {'ANDROID_SDK_ROOT': sdk, 'ANDROID_NDK_ROOT': os.path.join(sdk, 'ndk', NDK)}
    if jdk and _is_jdk17(jdk): env['JAVA_HOME'] = jdk
    return env

def checks():
    sdk, out = _sdk(), []
    add = lambda name, ok, fix: out.append((bool(ok), name, fix))
    ct = os.path.join(sdk, 'cmdline-tools')
    real = sorted(d for d in (os.listdir(ct) if os.path.isdir(ct) else []) if not os.path.islink(os.path.join(ct, d)))
    add('dotnet', shutil.which('dotnet'), 'install dotnet 8')
    add('unzip', shutil.which('unzip'), 'install unzip')
    add('adb', shutil.which('adb'), 'install adb (needed for the install stage)')
    add('Unity Editor + Android module', paths.unity_editor(), 'install Unity 6000.6.7f1 with Android Build Support via Unity Hub')
    add('cmdline-tools has only 16.0', real == ['16.0'],
        'move every other cmdline-tools folder away: Unity picks the last folder and cannot parse newer sdkmanager output')
    add('NDK ' + NDK, os.path.isdir(os.path.join(sdk, 'ndk', NDK)), 'sdkmanager "ndk;%s"' % NDK)
    add('JDK 17 (JAVA_HOME or Unity bundled)', _is_jdk17(_jdk()), JDK_FIX)
    return out

def main():
    bad = 0
    for ok, name, fix in checks():
        print(('ok   ' if ok else 'MISS ') + name + ('' if ok else '  -> ' + fix)); bad |= (not ok)
    return 1 if bad else 0
