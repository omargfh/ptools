"""Tests for ptools.utils.cache.disk_cache."""
import json
import time

from ptools.utils.cache import disk_cache


def test_caches_identical_calls(tmp_path):
    calls = []

    @disk_cache(cache_dir=tmp_path, max_cache_age=3600)
    def expensive(x, y=0):
        calls.append((x, y))
        return x + y

    assert expensive(1, 2) == 3
    assert expensive(1, 2) == 3
    assert calls == [(1, 2)]


def test_distinguishes_args(tmp_path):
    calls = []

    @disk_cache(cache_dir=tmp_path, max_cache_age=3600)
    def fn(x):
        calls.append(x)
        return x * 2

    fn(1)
    fn(2)
    fn(1)
    assert calls == [1, 2]


def test_expires_old_entries(tmp_path):
    calls = []

    @disk_cache(cache_dir=tmp_path, max_cache_age=0)
    def fn(x):
        calls.append(x)
        return x

    fn(1)
    # With max_cache_age=0, a second call should be considered expired.
    time.sleep(0.001)
    fn(1)
    assert len(calls) == 2


def test_flush_writes_disk(tmp_path):
    @disk_cache(cache_dir=tmp_path, max_cache_age=3600)
    def fn(x):
        return {"value": x}

    fn("alpha")
    fn.flush()  # type: ignore[attr-defined]

    cache_file = tmp_path / "fn.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert len(data) == 1
    # One entry with "r" (result) and "t" (timestamp) shorts.
    entry = next(iter(data.values()))
    assert entry["r"] == {"value": "alpha"}
    assert isinstance(entry["t"], (int, float))


def test_cache_persists_across_decorations(tmp_path):
    @disk_cache(cache_dir=tmp_path, max_cache_age=3600)
    def fn(x):
        return x * 10

    fn(5)
    fn.flush()  # type: ignore[attr-defined]

    # A freshly decorated function with the same name+dir should read the
    # cache written above instead of re-executing.
    call_count = [0]

    @disk_cache(cache_dir=tmp_path, max_cache_age=3600)
    def fn(x):  # noqa: F811 - intentional rebind to simulate fresh decoration
        call_count[0] += 1
        return x * 10

    assert fn(5) == 50
    assert call_count[0] == 0
