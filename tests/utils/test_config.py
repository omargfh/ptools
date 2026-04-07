"""Tests for ptools.utils.config.ConfigFile, LazyConfigFile, and DummyKeyValueStore."""
import json

import pytest
import yaml

from ptools.utils.config import ConfigFile, DummyKeyValueStore, LazyConfigFile


CONFIG_CLASSES = pytest.mark.parametrize(
    "cfg_cls", [ConfigFile, LazyConfigFile], ids=["eager", "lazy"]
)
FORMATS = pytest.mark.parametrize("fmt", ["json", "yaml"])


@pytest.fixture
def make_cfg():
    """Factory fixture — call with overrides, get a config instance."""
    def _make(cfg_cls=ConfigFile, name="unit_test", tmp_path=None, fmt="json", **kw):
        kw.setdefault("quiet", True)
        return cfg_cls(name=name, path=str(tmp_path), format=fmt, **kw)
    return _make


def _read_disk(tmp_path, name, fmt):
    ext = "yaml" if fmt == "yaml" else "json"
    path = tmp_path / f"{name}.{ext}"
    with path.open() as f:
        return yaml.safe_load(f) if fmt == "yaml" else json.load(f)


@CONFIG_CLASSES
@FORMATS
class TestConfigFile:
    def test_creates_file_on_init(self, tmp_path, cfg_cls, fmt):
        c = cfg_cls(name="init", path=str(tmp_path), quiet=True, format=fmt)
        if cfg_cls is LazyConfigFile:
            c._initialize()
        ext = "yaml" if fmt == "yaml" else "json"
        assert (tmp_path / f"init.{ext}").exists()

    def test_init_data_empty(self, tmp_path, cfg_cls, fmt):
        c = cfg_cls(name="init", path=str(tmp_path), quiet=True, format=fmt)
        assert c.data == {}

    def test_set_and_get(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("foo", "bar")
        assert c.get("foo") == "bar"
        assert c["foo"] == "bar"

    def test_set_persists_to_disk(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("key", {"nested": 1})
        content = _read_disk(tmp_path, "unit_test", fmt)
        assert content["encrypted"] is False
        assert content["data"]["key"] == {"nested": 1}

    def test_delete(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("a", 1)
        c.delete("a")
        assert c.get("a") is None

    def test_delete_missing_is_noop(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.delete("never-set")  # should not raise

    def test_exists(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("present", 1)
        assert c.exists("present") is True
        assert c.exists("missing") is False

    def test_contains(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("a", 1)
        assert "a" in c
        assert "b" not in c

    def test_upsert(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.upsert("x", 1)
        c.upsert("x", 2)
        assert c.get("x") == 2

    def test_clear(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert c.data == {}

    def test_replace(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("old", 1)
        c.replace({"new": 2})
        assert c.data == {"new": 2}

    def test_replace_requires_dict(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        with pytest.raises(TypeError):
            c.replace(["not", "a", "dict"])  # type: ignore[arg-type]

    def test_len(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c.set("a", 1)
        c.set("b", 2)
        assert len(c) == 2

    def test_callable_getter_setter(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        c("k", "v")
        assert c("k") == "v"

    def test_callable_requires_valid_arity(self, tmp_path, make_cfg, cfg_cls, fmt):
        c = make_cfg(cfg_cls=cfg_cls, tmp_path=tmp_path, fmt=fmt)
        with pytest.raises(TypeError):
            c(1, 2, 3)

    def test_reload_from_existing_file(self, tmp_path, cfg_cls, fmt):
        c1 = cfg_cls(name="reload", path=str(tmp_path), quiet=True, format=fmt)
        c1.set("persisted", {"v": 42})
        c2 = cfg_cls(name="reload", path=str(tmp_path), quiet=True, format=fmt)
        assert c2.get("persisted") == {"v": 42}


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