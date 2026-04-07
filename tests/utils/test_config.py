"""Tests for ptools.utils.config.ConfigFile and DummyKeyValueStore."""
import json

import pytest

from ptools.utils.config import ConfigFile, DummyKeyValueStore


@pytest.fixture
def cfg(tmp_path):
    return ConfigFile(name="unit_test", path=str(tmp_path), quiet=True, format="json")


class TestConfigFile:
    def test_creates_file_on_init(self, tmp_path):
        c = ConfigFile(name="init", path=str(tmp_path), quiet=True)
        assert (tmp_path / "init.json").exists()
        assert c.data == {}

    def test_set_and_get(self, cfg):
        cfg.set("foo", "bar")
        assert cfg.get("foo") == "bar"
        assert cfg["foo"] == "bar"

    def test_set_persists_to_disk(self, cfg, tmp_path):
        cfg.set("key", {"nested": 1})
        with (tmp_path / "unit_test.json").open() as f:
            content = json.load(f)
        # The on-disk format wraps data: {"encrypted": False, "data": {...}}
        assert content["encrypted"] is False
        assert content["data"]["key"] == {"nested": 1}

    def test_delete(self, cfg):
        cfg.set("a", 1)
        cfg.delete("a")
        assert cfg.get("a") is None

    def test_delete_missing_is_noop(self, cfg):
        cfg.delete("never-set")  # should not raise

    def test_exists(self, cfg):
        cfg.set("present", 1)
        assert cfg.exists("present") is True
        assert cfg.exists("missing") is False

    def test_contains(self, cfg):
        cfg.set("a", 1)
        assert "a" in cfg
        assert "b" not in cfg

    def test_upsert(self, cfg):
        cfg.upsert("x", 1)
        cfg.upsert("x", 2)
        assert cfg.get("x") == 2

    def test_clear(self, cfg):
        cfg.set("a", 1)
        cfg.set("b", 2)
        cfg.clear()
        assert cfg.data == {}

    def test_replace(self, cfg):
        cfg.set("old", 1)
        cfg.replace({"new": 2})
        assert cfg.data == {"new": 2}

    def test_replace_requires_dict(self, cfg):
        with pytest.raises(TypeError):
            cfg.replace(["not", "a", "dict"])  # type: ignore[arg-type]

    def test_len(self, cfg):
        cfg.set("a", 1)
        cfg.set("b", 2)
        assert len(cfg) == 2

    def test_callable_getter_setter(self, cfg):
        cfg("k", "v")
        assert cfg("k") == "v"

    def test_callable_requires_valid_arity(self, cfg):
        with pytest.raises(TypeError):
            cfg(1, 2, 3)

    def test_reload_from_existing_file(self, tmp_path):
        c1 = ConfigFile(name="reload", path=str(tmp_path), quiet=True)
        c1.set("persisted", {"v": 42})
        c2 = ConfigFile(name="reload", path=str(tmp_path), quiet=True)
        assert c2.get("persisted") == {"v": 42}

    def test_yaml_format(self, tmp_path):
        c = ConfigFile(name="ycfg", path=str(tmp_path), quiet=True, format="yaml")
        c.set("color", "red")
        assert (tmp_path / "ycfg.yaml").exists()

        c2 = ConfigFile(name="ycfg", path=str(tmp_path), quiet=True, format="yaml")
        assert c2.get("color") == "red"


class TestDummyKeyValueStore:
    def test_no_ops(self):
        d = DummyKeyValueStore()
        assert d.get("k") is None
        assert d.get("k", "default") == "default"
        assert d.set("k", 1) == 1
        assert d.exists("k") is False
        assert d.list() == {}
        assert d.clear() == {}
        d.close()  # should not raise
