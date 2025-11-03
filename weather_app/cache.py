import time
from typing import Any, Dict, Tuple


_store: Dict[str, Tuple[float, Any]] = {}


def cache_get(key: str):
    now = time.time()
    item = _store.get(key)
    if not item:
        return None
    exp, val = item
    if now > exp:
        _store.pop(key, None)
        return None
    return val


def cache_set(key: str, value: Any, ttl: int = 300):
    exp = time.time() + ttl
    _store[key] = (exp, value)