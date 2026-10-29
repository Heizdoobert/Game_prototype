def clip(node, n):
    """Truncate every string and dict key in a JSON-like tree to n chars (the kit's redact regex is quadratic on long runs)."""
    if isinstance(node, dict): return {(k[:n] if isinstance(k, str) else k): clip(v, n) for k, v in node.items()}
    if isinstance(node, list): return [clip(v, n) for v in node]
    return node[:n] if isinstance(node, str) else node

def is_il2cpp(engine_text):
    """The kit prints a line starting with IL2CPP for IL2CPP builds; its Mono line merely mentions "no IL2CPP step"."""
    return any(l.startswith('IL2CPP') for l in engine_text.splitlines())

NOT_SECRET = {'true', 'false', 'null', 'none', 'yes', 'no', '<redacted>'}

def secret_value(x):
    """x as a string if it is worth hunting for as a secret VALUE, else None.
    Eligible: len >= 8, or len >= 4 with a digit; never a bool/flag word or '<REDACTED>'; ints need >= 6 digits."""
    if isinstance(x, bool): return None
    s = x if isinstance(x, str) else str(x) if isinstance(x, int) else None
    if s is None or (not isinstance(x, str) and len(s) < 6): return None
    if not (len(s) >= 8 or (len(s) >= 4 and any(c.isdigit() for c in s))): return None
    return None if s.lower() in NOT_SECRET else s

NAME_KEYS, VALUE_KEYS = ('key', 'Key', 'name', 'Name'), ('value', 'Value')

def leaves(node):
    """every str/int/float leaf under node (bools and None skipped)"""
    if isinstance(node, dict):
        for v in node.values(): yield from leaves(v)
    elif isinstance(node, list):
        for v in node: yield from leaves(v)
    elif isinstance(node, (str, int, float)) and not isinstance(node, bool): yield node

def secret_pairs(node, pred):
    """(name, leaf) for every leaf under a dict key matching pred, or under the value of a {'key'|'name': <matching>, 'value': ...} pair"""
    if isinstance(node, dict):
        nm = next((node[k] for k in NAME_KEYS if isinstance(node.get(k), str) and pred(node[k])), None)
        if nm is not None:
            for k in VALUE_KEYS:
                for leaf in leaves(node.get(k)): yield nm, leaf
        for k, v in node.items():
            if isinstance(k, str) and pred(k):
                for leaf in leaves(v): yield k, leaf
            else: yield from secret_pairs(v, pred)
    elif isinstance(node, list):
        for v in node: yield from secret_pairs(v, pred)
