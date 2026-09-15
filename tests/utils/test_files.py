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

class TestTestIncludeExcludeGlob:
    def test_basic_include_exclude_match(self, tmp_path):
        (tmp_path / "a.txt").write_text("1")
        (tmp_path / "b.log").write_text("2")
        (tmp_path / "c.txt").write_text("3")
        (tmp_path / ".hidden").write_text("4")

        # Include only .txt files
        assert files.test_include_exclude_glob("*.txt", None, str(tmp_path / "a.txt"), relative_to=str(tmp_path))
        assert not files.test_include_exclude_glob("*.txt", None, str(tmp_path / "b.log"), relative_to=str(tmp_path))

        # Exclude .log files
        assert not files.test_include_exclude_glob(None, "*.log", str(tmp_path / "b.log"), relative_to=str(tmp_path))
        assert files.test_include_exclude_glob(None, "*.log", str(tmp_path / "a.txt"), relative_to=str(tmp_path))

        # Include .txt and exclude .hidden
        assert files.test_include_exclude_glob("*.txt", ".hidden", str(tmp_path / "a.txt"), relative_to=str(tmp_path))
        assert not files.test_include_exclude_glob("*.txt", ".hidden", str(tmp_path / ".hidden"), relative_to=str(tmp_path))

    def test_include_exclude_with_relative_to(self, tmp_path):
        (tmp_path / "dir").mkdir()
        (tmp_path / "dir" / "node_modules").mkdir()
        (tmp_path / "dir" / "node_modules" / "file.js").write_text("console.log('hi');")
        (tmp_path / "dir" / "file.txt").write_text("hello")
        (tmp_path / "dir" / "a.txt").write_text("1")
        (tmp_path / "dir" / "b.log").write_text("2")

        # Test that the relative_to parameter does not affect the include/exclude logic when irrelevant
        assert files.test_include_exclude_glob("*.txt", None, str(tmp_path / "dir" / "file.txt"), relative_to=str(tmp_path / "dir"))
        assert files.test_include_exclude_glob("*.txt", None, str(tmp_path / "dir" / "file.txt"), relative_to=None)

        # Test that the relative_to parameter correctly affects the include/exclude logic
        assert files.test_include_exclude_glob(None, "node_modules", str(tmp_path / "dir" / "node_modules" / "file.js"), relative_to=None)
        assert files.test_include_exclude_glob(None, "node_modules", str(tmp_path / "dir" / "node_modules"), relative_to=None)
        assert not files.test_include_exclude_glob(None, "node_modules", str(tmp_path / "dir" / "node_modules"), relative_to=str(tmp_path / "dir"))
        assert not files.test_include_exclude_glob(None, "**/node_modules/**", str(tmp_path / "dir" / "node_modules" / "file.js"), relative_to=None)
        assert not files.test_include_exclude_glob(None, "node_modules/**", str(tmp_path / "dir" / "node_modules" / "file.js"), relative_to=str(tmp_path / "dir"))


    def test_include_exclude_with_multiple_patterns(self, tmp_path):
        (tmp_path / "dir").mkdir()
        (tmp_path / "dir" / "file1.txt").write_text("1")
        (tmp_path / "dir" / "file2.log").write_text("2")
        (tmp_path / "dir" / "file3.md").write_text("3")
        (tmp_path / "dir" / ".hidden").write_text("4")

        # Test multiple include patterns
        assert files.test_include_exclude_glob("*.txt|*.md", None, str(tmp_path / "dir" / "file1.txt"), relative_to=str(tmp_path))
        assert files.test_include_exclude_glob("*.txt|*.md", None, str(tmp_path / "dir" / "file3.md"), relative_to=str(tmp_path))
        assert not files.test_include_exclude_glob("*.txt|*.md", None, str(tmp_path / "dir" / "file2.log"), relative_to=str(tmp_path))

        # Test multiple exclude patterns
        assert not files.test_include_exclude_glob(None, "*.log|.hidden", str(tmp_path / "dir" / "file2.log"), relative_to=str(tmp_path))
        assert not files.test_include_exclude_glob(None, "*.log|.hidden", str(tmp_path / "dir" / ".hidden"), relative_to=str(tmp_path / "dir"))
        assert files.test_include_exclude_glob(None, "*.log|.hidden", str(tmp_path / "dir" / "file1.txt"), relative_to=str(tmp_path))