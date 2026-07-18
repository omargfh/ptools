"""Tests for ptools.utils.require decorators and helpers."""
import pytest

from ptools.utils import require
from ptools.utils.enums import LogicalOperators


class DictStore:
    """Minimal implementation of the ImplementsGet protocol for tests."""
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def test_require_library_present():
    require._require_library("json")  # stdlib, always present


def test_require_library_missing():
    with pytest.raises(ImportError):
        require._require_library("definitely_not_installed_xyz_1234")


def test_require_binary_present():
    require._require_binary("ls")


def test_require_binary_missing():
    with pytest.raises(ImportError):
        require._require_binary("definitely-missing-binary-xyz")


class TestRequireKey:
    def test_single_key_found(self):
        store = DictStore({"API_KEY": "secret"})
        result = require._require_key({"api": "API_KEY"}, [store])
        assert result == {"api": "secret"}

    def test_multiple_aliases_picks_first_available(self):
        store = DictStore({"ALT": "value"})
        result = require._require_key({"api": ["PRIMARY", "ALT"]}, [store])
        assert result == {"api": "value"}

    def test_missing_with_OR_raises_when_all_missing(self):
        with pytest.raises(ValueError):
            require._require_key(
                {"api": "API_KEY"},
                [DictStore({})],
                LogicalOperators.OR,
            )

    def test_OR_passes_when_any_present(self):
        result = require._require_key(
            {"api": "API_KEY", "other": "OTHER"},
            [DictStore({"API_KEY": "x"})],
            LogicalOperators.OR,
        )
        assert result["api"] == "x"
        assert result["other"] is None

    def test_AND_requires_all(self):
        with pytest.raises(ValueError):
            require._require_key(
                {"api": "API_KEY", "other": "OTHER"},
                [DictStore({"API_KEY": "x"})],
                LogicalOperators.AND,
            )

    def test_multiple_stores_searched_in_order(self):
        s1 = DictStore({})
        s2 = DictStore({"K": "from-s2"})
        result = require._require_key({"k": "K"}, [s1, s2])
        assert result == {"k": "from-s2"}


class TestDecorators:
    def test_library_decorator_allows_present(self):
        @require.library("json")
        def fn():
            return "ran"

        assert fn() == "ran"

    def test_library_decorator_raises_for_missing(self):
        @require.library("definitely_not_installed_xyz_1234")
        def fn():
            return "ran"

        with pytest.raises(ImportError):
            fn()

    def test_binary_decorator_passes_when_present(self):
        @require.binary("ls")
        def fn():
            return "ran"

        assert fn() == "ran"

    def test_binary_decorator_AND_raises_when_any_missing(self):
        @require.binary(["ls", "definitely-missing-binary-xyz"], LogicalOperators.AND)
        def fn():
            return "ran"

        with pytest.raises(ImportError):
            fn()

    def test_binary_decorator_OR_passes_if_any_found(self):
        @require.binary(
            ["definitely-missing-binary-xyz", "ls"],
            LogicalOperators.OR,
            key="found",
        )
        def fn(found=None):
            return found

        assert fn() == ["ls"]

    def test_key_decorator_injects_values(self):
        store = DictStore({"API_KEY": "secret"})

        @require.key({"api": "API_KEY"}, [store])
        def fn(api=None):
            return api

        assert fn() == "secret"


class TestOsDecorator:
    def test_announces_os_requirement(self):
        require.clear_announcements()

        @require.os(["definitely-not-a-real-os"])
        def fn():
            return "ran"

        announced = require.announced_requirements()
        assert len(announced) == 1
        assert isinstance(announced[0], require.OSRequirement)
        assert not isinstance(announced[0], require.BinaryRequirement)
        assert announced[0].names == ("definitely-not-a-real-os",)

    def test_raises_on_non_matching_os(self):
        @require.os(["definitely-not-a-real-os"])
        def fn():
            return "ran"

        with pytest.raises(ValueError):
            fn()

    def test_passes_on_matching_os(self):
        import platform

        @require.os([platform.system().lower()])
        def fn():
            return "ran"

        assert fn() == "ran"


class TestAnnounceDedup:
    def test_duplicate_requirement_recorded_once(self):
        require.clear_announcements()

        @require.os(["darwin"])
        def a():
            return "a"

        @require.os(["darwin"])
        def b():
            return "b"

        announced = require.announced_requirements()
        assert len(announced) == 1

    def test_first_seen_order_preserved(self):
        require.clear_announcements()

        @require.binary("git")
        def a():
            return "a"

        @require.binary("ls")
        def b():
            return "b"

        @require.binary("git")
        def c():
            return "c"

        announced = require.announced_requirements()
        assert [r.names for r in announced] == [("git",), ("ls",)]

    def test_distinct_requirements_sharing_a_name_are_kept(self):
        require.clear_announcements()

        require.announce(require.LibraryRequirement(module="foo"))
        require.announce(require.LibraryRequirement(module="foo", pypi_name="Foo-Alt"))

        announced = require.announced_requirements()
        assert len(announced) == 2

    def test_clear_announcements_resets_dedup_state(self):
        require.clear_announcements()
        require.announce(require.LibraryRequirement(module="foo"))
        require.clear_announcements()
        require.announce(require.LibraryRequirement(module="foo"))

        assert len(require.announced_requirements()) == 1


class TestOptionalLibrary:
    def test_available_when_importable(self):
        check = require.optional_library("json")
        assert check() is True

    def test_unavailable_when_missing(self):
        check = require.optional_library("definitely_not_installed_xyz_1234")
        assert check() is False

    def test_announces_into_registry(self):
        require.optional_library("some_optional_lib", pypi_name="some-optional-lib")
        announced = require.announced_requirements()
        assert any(
            isinstance(r, require.LibraryRequirement)
            and r.module == "some_optional_lib"
            and r.pip_name == "some-optional-lib"
            for r in announced
        )
