"""Tests for ptools.utils.serial serializer/deserializer factory."""
import io

import pytest

from ptools.utils.serial import (
    JSONSerializerDeserializer,
    SerializerDeserializerFactory,
    YAMLSerializerDeserializer,
)


class TestJSON:
    def test_roundtrip_dumps_loads(self):
        data = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
        text = JSONSerializerDeserializer.dumps(data)
        assert JSONSerializerDeserializer.loads(text) == data

    def test_roundtrip_dump_load_file(self, tmp_path):
        path = tmp_path / "data.json"
        data = {"k": "v"}
        with path.open("w") as f:
            JSONSerializerDeserializer.dump(data, f)
        with path.open("r") as f:
            assert JSONSerializerDeserializer.load(f) == data

    def test_invalid_raises_decode_error(self):
        with pytest.raises(JSONSerializerDeserializer.DecodeError):
            JSONSerializerDeserializer.loads("{not json}")


class TestYAML:
    def test_roundtrip(self):
        data = {"name": "ptools", "list": [1, 2], "flag": True}
        text = YAMLSerializerDeserializer.dumps(data)
        assert YAMLSerializerDeserializer.loads(text) == data

    def test_block_style_by_default(self):
        text = YAMLSerializerDeserializer.dumps({"a": 1, "b": 2})
        # Block style uses one key per line.
        assert "a: 1" in text
        assert "b: 2" in text


class TestFactory:
    @pytest.mark.parametrize(
        "fmt,expected",
        [
            ("json", JSONSerializerDeserializer),
            ("JSON", JSONSerializerDeserializer),
            ("yaml", YAMLSerializerDeserializer),
            ("yml", YAMLSerializerDeserializer),
        ],
    )
    def test_get(self, fmt, expected):
        assert SerializerDeserializerFactory.get(fmt) is expected

    def test_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            SerializerDeserializerFactory.get("toml")
