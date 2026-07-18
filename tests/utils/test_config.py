"""Tests for ptools.utils.config.ConfigFile, LazyConfigFile, and DummyKeyValueStore."""
import json
import os

import pytest
import yaml

from ptools.utils.config import ConfigFile, DummyKeyValueStore, LazyConfigFile


CONFIG_CLASSES = pytest.mark.parametrize(
    "cfg_cls", [ConfigFile, LazyConfigFile], ids=["eager", "lazy"]
)
FORMATS = pytest.mark.parametrize("fmt", ["json", "yaml"])


@pytest.fixture
def make_cfg():
    """Factory fixture - call with overrides, get a config instance."""
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

class TestStarterSeeding:
    """Missing configs are seeded from packaged starters in ptools/starters."""

    def test_starter_file_lookup(self):
        from ptools.utils.config import starter_file

        assert starter_file("touch.yaml") is not None
        assert starter_file("literals.json") is not None
        assert starter_file("no-such-starter.yaml") is None

    def test_missing_touch_config_seeded_from_starter(self, tmp_path):
        c = ConfigFile(name="touch", path=str(tmp_path), quiet=True, format="yaml")

        assert (tmp_path / "touch.yaml").exists()
        assert len(c.data["values"]) > 0
        assert "groups_meta" in c.data

    def test_missing_literals_config_seeded_from_starter(self, tmp_path):
        c = ConfigFile(name="literals", path=str(tmp_path), quiet=True, format="json")

        assert "cli_emojis" in c.data

    def test_existing_config_is_not_overwritten(self, tmp_path):
        (tmp_path / "touch.yaml").write_text(
            "encrypted: false\ndata:\n  values: []\n"
        )
        c = ConfigFile(name="touch", path=str(tmp_path), quiet=True, format="yaml")

        assert c.data["values"] == []

    def test_name_without_starter_creates_empty_config(self, tmp_path):
        c = ConfigFile(name="no_starter_here", path=str(tmp_path), quiet=True)

        assert c.data == {}
        assert (tmp_path / "no_starter_here.json").exists()

    def test_seeded_starter_preserves_yaml_comments(self, tmp_path):
        ConfigFile(name="touch", path=str(tmp_path), quiet=True, format="yaml")

        assert "#" in (tmp_path / "touch.yaml").read_text()


class TestAtomicWrites:
    """A failure part-way through a write must not truncate/corrupt the file.

    ``_writes`` is patched on the *class* (not the instance) because
    ``ConfigFile.__setattr__`` treats any non-reserved instance
    attribute as config data to persist (see ``RESERVED_CONFIG_KEYS``) -
    ``instance._writes = ...`` would silently try to write a function
    into the config itself.
    """

    @pytest.mark.parametrize(
        "method, args",
        [
            ("set", ("b", 2)),
            ("delete", ("a",)),
            ("clear", ()),
            ("replace", ({"new": 1},)),
        ],
    )
    def test_write_failure_leaves_file_byte_identical(
        self, tmp_path, make_cfg, monkeypatch, method, args
    ):
        c = make_cfg(tmp_path=tmp_path)
        c.set("a", 1)
        before = (tmp_path / "unit_test.json").read_bytes()

        def boom(self, f, data):
            f.write("partial-garbage")  # proves this landed in the temp file
            raise RuntimeError("writes exploded")

        monkeypatch.setattr(ConfigFile, "_writes", boom)

        with pytest.raises(RuntimeError):
            getattr(c, method)(*args)

        assert (tmp_path / "unit_test.json").read_bytes() == before

    def test_temp_file_does_not_survive_a_failed_write(self, tmp_path, make_cfg, monkeypatch):
        c = make_cfg(tmp_path=tmp_path)
        c.set("a", 1)

        def boom(self, f, data):
            raise RuntimeError("writes exploded")

        monkeypatch.setattr(ConfigFile, "_writes", boom)

        with pytest.raises(RuntimeError):
            c.set("b", 2)

        assert not (tmp_path / "unit_test.json.tmp").exists()

    def test_first_run_creation_failure_leaves_no_partial_file(self, tmp_path, monkeypatch):
        """The :124 site (first-run seed write) fails atomically too."""

        def boom(self, f, data):
            f.write("partial-garbage")
            raise RuntimeError("writes exploded")

        monkeypatch.setattr(ConfigFile, "_writes", boom)

        with pytest.raises(RuntimeError):
            ConfigFile(name="fresh", path=str(tmp_path), quiet=True)

        assert not (tmp_path / "fresh.json").exists()
        assert not (tmp_path / "fresh.json.tmp").exists()

    def test_encrypted_store_write_failure_leaves_prior_ciphertext_intact(
        self, tmp_path, monkeypatch
    ):
        import keyring
        from keyring.backend import KeyringBackend

        from ptools.utils.encrypt import Encryption

        class InMemoryKeyring(KeyringBackend):
            """Minimal in-process keyring so the test never touches the real OS keychain."""

            priority = 1  # type: ignore[assignment]

            def __init__(self):
                self._store: dict[tuple[str, str], str] = {}

            def get_password(self, service, username):
                return self._store.get((service, username))

            def set_password(self, service, username, password):
                self._store[(service, username)] = password

            def delete_password(self, service, username):
                self._store.pop((service, username), None)

        backend = InMemoryKeyring()
        monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
        monkeypatch.setattr(keyring, "get_password", backend.get_password)
        monkeypatch.setattr(keyring, "set_password", backend.set_password)

        c = ConfigFile(name="secret", path=str(tmp_path), quiet=True, encrypt=True)
        c.set("token", "s3cret")
        before = (tmp_path / "secret.json").read_bytes()

        def boom(self, value):
            raise RuntimeError("keyring unavailable")

        monkeypatch.setattr(Encryption, "encrypt", boom)

        with pytest.raises(RuntimeError):
            c.set("token", "new-secret")

        assert (tmp_path / "secret.json").read_bytes() == before
        assert not (tmp_path / "secret.json.tmp").exists()

        # The prior ciphertext is still readable, not just byte-identical.
        reopened = ConfigFile(name="secret", path=str(tmp_path), quiet=True, encrypt=True)
        assert reopened.get("token") == "s3cret"

    def test_write_preserves_existing_permissions(self, tmp_path, make_cfg):
        c = make_cfg(tmp_path=tmp_path)
        c.set("a", 1)
        path = tmp_path / "unit_test.json"
        os.chmod(path, 0o600)

        c.set("b", 2)

        assert (os.stat(path).st_mode & 0o777) == 0o600
