from functools import wraps
from enum import Enum

from ptools.utils.lazy import Lazy
from ptools.utils.print import PrintUtils

class Short(Enum):
    Timestamp = "t"
    Result = "r"

def disk_cache(cache_dir=None, max_cache_age=3600,  hex_length=32):
    import os, json, hashlib, time, atexit
    from pathlib import Path

    cache_dir = cache_dir or Path(os.path.expanduser("~/.ptools/.cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    def decorator(func):
        cache_file_path = cache_dir / f"{func.__name__}.json"
        dirty = False

        def get_cache_from_disk() -> dict:
            if cache_file_path.exists():
                try:
                    with open(cache_file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return {}
            return {}

        l_persisted = Lazy(lambda: get_cache_from_disk())

        def make_key(args, kwargs):
            key_str = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
            return hashlib.sha256(key_str.encode()).hexdigest()[:hex_length]

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal dirty

            cache_key = make_key(args, kwargs)
            now = time.time()
            persisted = l_persisted.value

            if cache_key in persisted:
                entry = persisted[cache_key]
                if now - entry[Short.Timestamp.value] < max_cache_age:
                    return entry[Short.Result.value]
                else:
                    del persisted[cache_key]
                    dirty = True

            result = func(*args, **kwargs)
            persisted[cache_key] = {Short.Result.value: result, Short.Timestamp.value: now}
            dirty = True
            return result

        def _flush():
            nonlocal dirty
            if not dirty:
                return

            persisted = l_persisted.value
            now = time.time()
            to_write = {
                k: v for k, v in persisted.items()
                if now - v[Short.Timestamp.value] < max_cache_age
            }

            try:
                tmp = str(cache_file_path) + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(to_write, f)
                os.replace(tmp, cache_file_path)
            except Exception:
                pass

        atexit.register(_flush)
        wrapper.flush = _flush # type: ignore

        return wrapper

    return decorator