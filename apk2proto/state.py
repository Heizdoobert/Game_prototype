import contextlib, fcntl, hashlib, json, os

class Workdir:
    def __init__(self, path):
        self.path = os.path.abspath(path); os.makedirs(self.path, exist_ok=True)
        self.file = os.path.join(self.path, 'state.json')
        if os.path.exists(self.file):
            with open(self.file) as fh: self.state = json.load(fh)
        else: self.state = {}

    def p(self, *parts): return os.path.join(self.path, *parts)
    def is_done(self, stage, key): return self.state.get(stage) == key

    def mark(self, stage, key):
        self.state[stage] = key
        tmp = self.file + '.tmp'
        with open(tmp, 'w') as fh: json.dump(self.state, fh, indent=1)
        os.replace(tmp, self.file)

    @contextlib.contextmanager
    def lock(self):                       # one heavy stage at a time (low-RAM machine)
        with open(self.p('.lock'), 'w') as f:   # closing f releases the flock
            try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise SystemExit('another apk2proto stage is running in ' + self.path)
            yield

def fingerprint(*paths, suffixes=None):
    """suffixes: only hash files whose name ends with one of them (ignores generated .meta etc.)."""
    h = hashlib.sha1()
    keep = lambda name: suffixes is None or name.endswith(tuple(suffixes))
    for p in paths:
        if os.path.isfile(p):
            if not keep(p): continue
            st = os.stat(p); h.update(f'{p}:{st.st_size}:{int(st.st_mtime)}'.encode())
        elif os.path.isdir(p):
            for dp, _, fs in sorted(os.walk(p)):
                for f in sorted(fs):
                    if not keep(f): continue
                    fp = os.path.join(dp, f); st = os.stat(fp)
                    h.update(f'{os.path.relpath(fp, p)}:{st.st_size}:{int(st.st_mtime)}'.encode())
        else: h.update(f'missing:{p}'.encode())
    return h.hexdigest()
