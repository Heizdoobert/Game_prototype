import contextlib, fcntl, hashlib, json, os

class Workdir:
    def __init__(self, path):
        self.path = os.path.abspath(path); os.makedirs(self.path, exist_ok=True)
        self.file = os.path.join(self.path, 'state.json')
        self.state = json.load(open(self.file)) if os.path.exists(self.file) else {}

    def p(self, *parts): return os.path.join(self.path, *parts)
    def is_done(self, stage, key): return self.state.get(stage) == key

    def mark(self, stage, key):
        self.state[stage] = key
        tmp = self.file + '.tmp'; json.dump(self.state, open(tmp, 'w'), indent=1); os.replace(tmp, self.file)

    @contextlib.contextmanager
    def lock(self):                       # one heavy stage at a time (low-RAM machine)
        f = open(self.p('.lock'), 'w')
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise SystemExit('another apk2proto stage is running in ' + self.path)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN); f.close()

def fingerprint(*paths):
    h = hashlib.sha1()
    for p in paths:
        if os.path.isfile(p):
            st = os.stat(p); h.update(f'{p}:{st.st_size}:{int(st.st_mtime)}'.encode())
        elif os.path.isdir(p):
            for dp, _, fs in sorted(os.walk(p)):
                for f in sorted(fs):
                    fp = os.path.join(dp, f); st = os.stat(fp)
                    h.update(f'{os.path.relpath(fp, p)}:{st.st_size}:{int(st.st_mtime)}'.encode())
        else: h.update(f'missing:{p}'.encode())
    return h.hexdigest()
