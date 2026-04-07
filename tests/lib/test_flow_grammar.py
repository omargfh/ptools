"""Tests for ptools.lib.flow.grammar — Lark parser + StreamTransformer."""
import pytest

from ptools.lib.flow.grammar import AttributeDict, StreamTransformer, parser


def _parse(text):
    return StreamTransformer().transform(parser.parse(text))


class TestNumbers:
    def test_int(self):
        assert _parse("42") == 42

    def test_negative_int(self):
        assert _parse("-7") == -7

    def test_float(self):
        assert _parse("3.14") == 3.14

    def test_scientific(self):
        assert _parse("1e3") == 1000.0


class TestBooleans:
    def test_true(self):
        assert _parse("true") is True

    def test_false_case_insensitive(self):
        assert _parse("False") is False


class TestNull:
    @pytest.mark.parametrize("src", ["null", "None", "NONE"])
    def test_null(self, src):
        assert _parse(src) is None


class TestCollections:
    def test_empty_list(self):
        assert _parse("[]") == []

    def test_list(self):
        assert _parse("[1, 2, 3]") == [1, 2, 3]

    def test_tuple(self):
        assert _parse("(1, 2)") == (1, 2)

    def test_empty_tuple(self):
        assert _parse("()") == ()

    def test_empty_dict(self):
        assert _parse("{}") == {}

    def test_dict(self):
        result = _parse("{1: 2, 3: 4}")
        assert result == {1: 2, 3: 4}
        assert isinstance(result, AttributeDict)


class TestAttributeDict:
    def test_attribute_access(self):
        d = AttributeDict({"foo": "bar"})
        assert d.foo == "bar"

    def test_attribute_assignment(self):
        d = AttributeDict()
        d.x = 1
        assert d["x"] == 1

    def test_missing_attribute_raises(self):
        d = AttributeDict()
        with pytest.raises(AttributeError):
            _ = d.missing

    def test_del_attribute(self):
        d = AttributeDict({"k": "v"})
        del d.k
        assert "k" not in d

    def test_del_missing_raises(self):
        d = AttributeDict()
        with pytest.raises(AttributeError):
            del d.nope


class TestQuoted:
    def test_double_quoted(self):
        assert _parse('"hello"') == "hello"

    def test_single_quoted(self):
        assert _parse("'world'") == "world"

    def test_backtick_quoted(self):
        assert _parse("`code`") == "code"
