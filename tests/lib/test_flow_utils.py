"""Tests for ptools.lib.flow.utils — yield_scope and global scope builder."""
from ptools.lib.flow.utils import create_global_scope, yield_scope
from ptools.lib.flow.values import StreamValue


class TestYieldScope:
    def test_dict_yields_per_key(self):
        scopes = list(yield_scope({"a": 1, "b": 2}))
        assert len(scopes) == 2
        keys = {s["k"] for s in scopes}
        assert keys == {"a", "b"}
        for s in scopes:
            assert s["x"] == s["v"]
            assert s["obj"] == {"a": 1, "b": 2}

    def test_list_yields_per_index(self):
        scopes = list(yield_scope([10, 20, 30]))
        assert [s["x"] for s in scopes] == [10, 20, 30]
        assert [s["i"] for s in scopes] == [0, 1, 2]
        assert all(s["arr"] == [10, 20, 30] for s in scopes)

    def test_tuple(self):
        scopes = list(yield_scope((1, 2)))
        assert [s["x"] for s in scopes] == [1, 2]

    def test_scalar_wraps_in_single_scope(self):
        scopes = list(yield_scope(42))
        assert len(scopes) == 1
        assert scopes[0]["x"] == 42
        assert scopes[0]["arr"] == [42]

    def test_accepts_stream_value(self):
        sv = StreamValue("[1, 2]")
        scopes = list(yield_scope(sv))
        assert [s["x"] for s in scopes] == [1, 2]


class TestGlobalScope:
    def test_has_core_helpers(self):
        g = create_global_scope()
        for name in [
            "to_json",
            "from_json",
            "to_upper",
            "to_lower",
            "round",
            "sqrt",
            "mean",
            "median",
            "regex_match",
            "regex_search",
            "current_time",
            "random_choice",
            "random_string",
            "math",
            "re",
            "os",
            "Globals",
        ]:
            assert name in g

    def test_json_helpers_roundtrip(self):
        g = create_global_scope()
        assert g["from_json"](g["to_json"]({"a": 1})) == {"a": 1}

    def test_string_helpers(self):
        g = create_global_scope()
        assert g["to_upper"]("abc") == "ABC"
        assert g["to_lower"]("ABC") == "abc"

    def test_math_helpers(self):
        g = create_global_scope()
        assert g["sqrt"](16) == 4.0
        assert g["round"](3.14159, 2) == 3.14
        assert g["mean"]([1, 2, 3]) == 2
        assert g["median"]([1, 3, 5]) == 3

    def test_regex_helpers(self):
        g = create_global_scope()
        assert g["regex_match"](r"\d+", "123abc") is True
        assert g["regex_match"](r"\d+", "abc") is False
        assert g["regex_search"](r"\d+", "abc123") is True

    def test_random_string_length(self):
        g = create_global_scope()
        assert len(g["random_string"](12)) == 12

    def test_globals_dir_returns_names(self):
        g = create_global_scope()
        names = g["Globals"].dir()
        assert "to_json" in names
