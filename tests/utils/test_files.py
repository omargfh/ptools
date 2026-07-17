"""Tests for ptools.utils.files.get_size, notably trailing-slash handling."""
import pytest

from ptools.utils import files


@pytest.fixture
def uncached(monkeypatch):
    """Bypass the disk cache so tests never touch ~/.ptools/.cache."""
    monkeypatch.setattr(files, "_get_size_cached", files._get_size)


class TestGetSizeTrailingSlash:
    def test_file_with_trailing_slash_returns_size(self, uncached, tmp_path):
        """Regression: 'file/' failed the isfile check and crashed in scandir."""
        f = tmp_path / "a.txt"
        f.write_text("hello")

        assert files.get_size(str(f) + "/") == 5

    def test_dir_with_and_without_trailing_slash_agree(self, uncached, tmp_path):
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.txt").write_text("world!")

        assert files.get_size(str(tmp_path) + "/") == files.get_size(str(tmp_path)) == 11

    def test_spellings_share_one_cache_key(self, monkeypatch, tmp_path):
        """'dir', 'dir/', and 'dir//' must reach the cache as the same path."""
        seen = []

        def spy(path, ignore_hidden=False):
            seen.append(path)
            return 0

        monkeypatch.setattr(files, "_get_size_cached", spy)

        files.get_size(str(tmp_path))
        files.get_size(str(tmp_path) + "/")
        files.get_size(str(tmp_path) + "//")

        assert len(set(seen)) == 1


class TestGetSizeBasics:
    def test_file_size(self, uncached, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("12345678")
        assert files.get_size(str(f)) == 8

    def test_directory_recurses(self, uncached, tmp_path):
        (tmp_path / "a.txt").write_text("123")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("4567")
        assert files.get_size(str(tmp_path)) == 7

    def test_ignore_hidden_skips_dot_entries(self, uncached, tmp_path):
        (tmp_path / "a.txt").write_text("123")
        (tmp_path / ".hidden").write_text("456789")
        assert files.get_size(str(tmp_path), ignore_hidden=True) == 3
        assert files.get_size(str(tmp_path), ignore_hidden=False) == 9


class TestGetSizeNoCache:
    """--no-cache (use_cache=False) must recompute fresh and never touch the cache."""

    def test_use_cache_false_bypasses_stale_cache(self, monkeypatch, tmp_path):
        # A fake cache that always claims a directory is empty (stale).
        stale = {}

        def fake_cached(path, ignore_hidden=False):
            return stale.get(path, 0)

        monkeypatch.setattr(files, "_get_size_cached", fake_cached)

        (tmp_path / "a.txt").write_text("hello")  # 5 real bytes on disk

        # use_cache=True consults the (stale) cache -> 0
        assert files.get_size(str(tmp_path), use_cache=True) == 0
        # use_cache=False bypasses it and measures disk -> 5
        assert files.get_size(str(tmp_path), use_cache=False) == 5

    def test_use_cache_false_never_calls_cache(self, monkeypatch, tmp_path):
        called = []
        monkeypatch.setattr(
            files, "_get_size_cached",
            lambda *a, **k: called.append(a) or 0,
        )

        (tmp_path / "a.txt").write_text("1234")
        assert files.get_size(str(tmp_path), use_cache=False) == 4
        assert called == []  # the cache wrapper was never invoked

    def test_bypass_propagates_into_subdirectories(self, monkeypatch, tmp_path):
        """A bypassed parent must not sum cached (stale) child sizes."""
        called = []
        monkeypatch.setattr(
            files, "_get_size_cached",
            lambda *a, **k: called.append(a) or 999,
        )

        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("abc")  # 3 bytes, nested one level down

        assert files.get_size(str(tmp_path), use_cache=False) == 3
        assert called == []  # neither the parent nor the child hit the cache
