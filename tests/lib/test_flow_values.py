"""Tests for ptools.lib.flow.values — StreamValue + OutputValue flavors."""
import json

import pytest

from ptools.lib.flow.values import (
    OutputFlavorKind,
    OutputJSONFlavor,
    OutputNoneFlavor,
    OutputPlainFlavor,
    OutputPythonFlavor,
    OutputUnflavoredFlavor,
    OutputValue,
    StreamValue,
)


class TestStreamValue:
    def test_parses_int(self):
        assert StreamValue("1").value == 1

    def test_parses_list(self):
        assert StreamValue("[1, 2]").value == [1, 2]

    def test_parses_dict(self):
        assert StreamValue("{1: 2}").value == {1: 2}

    def test_null_helper(self):
        assert StreamValue.Null().value is None

    def test_repr_shows_value(self):
        assert "42" in repr(StreamValue("42"))


class TestOutputFlavors:
    def test_plain_list(self):
        assert OutputPlainFlavor().format([1, 2, 3]) == "1\n2\n3"

    def test_plain_dict(self):
        out = OutputPlainFlavor().format({"a": 1, "b": 2})
        assert "a: 1" in out and "b: 2" in out

    def test_plain_scalar(self):
        assert OutputPlainFlavor().format(42) == "42"

    def test_json(self):
        assert json.loads(OutputJSONFlavor().format({"x": 1})) == {"x": 1}

    def test_python_repr(self):
        assert OutputPythonFlavor().format("hi") == "'hi'"

    def test_none_returns_empty(self):
        assert OutputNoneFlavor().format({"x": 1}) == ""

    def test_unflavored_str(self):
        assert OutputUnflavoredFlavor().format([1, 2]) == "[1, 2]"


class TestOutputValue:
    @pytest.mark.parametrize(
        "kind,cls_name",
        [
            (OutputFlavorKind.plain, "OutputPlainFlavor"),
            (OutputFlavorKind.json, "OutputJSONFlavor"),
            (OutputFlavorKind.python, "OutputPythonFlavor"),
            (OutputFlavorKind.none, "OutputNoneFlavor"),
            (OutputFlavorKind.unflavored, "OutputUnflavoredFlavor"),
        ],
    )
    def test_selects_flavor(self, kind, cls_name):
        ov = OutputValue(kind)
        assert type(ov.flavor).__name__ == cls_name

    def test_format_delegates(self):
        ov = OutputValue(OutputFlavorKind.json)
        assert json.loads(ov.format([1, 2])) == [1, 2]
