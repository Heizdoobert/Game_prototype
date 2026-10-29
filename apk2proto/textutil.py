def clip(node, n):
    """Truncate every string and dict key in a JSON-like tree to n chars (the kit's redact regex is quadratic on long runs)."""
    if isinstance(node, dict): return {(k[:n] if isinstance(k, str) else k): clip(v, n) for k, v in node.items()}
    if isinstance(node, list): return [clip(v, n) for v in node]
    return node[:n] if isinstance(node, str) else node
