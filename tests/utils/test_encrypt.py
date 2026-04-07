"""Tests for ptools.utils.encrypt — AES-GCM encryption against an in-memory keyring."""
import keyring
from keyring.backend import KeyringBackend

from ptools.utils.encrypt import DummyEncryption, Encryption


class InMemoryKeyring(KeyringBackend):
    """Minimal keyring backend so tests don't touch the real OS keychain."""
    priority = 1  # type: ignore[assignment]

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


def _install_backend(monkeypatch):
    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    # The module-level helpers keyring.get_password / set_password route through
    # the active backend, but some versions cache — patch them explicitly.
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    return backend


class TestEncryption:
    def test_roundtrip_string(self, monkeypatch):
        _install_backend(monkeypatch)
        enc = Encryption("com.ptools.test", user_name="tester")
        blob = enc.encrypt("hello world")
        assert set(blob) == {"nonce", "ciphertext", "tag"}
        assert enc.decrypt(blob) == "hello world"

    def test_roundtrip_bytes(self, monkeypatch):
        _install_backend(monkeypatch)
        enc = Encryption("com.ptools.test", user_name="tester")
        blob = enc.encrypt(b"binary-data")
        assert enc.decrypt(blob) == "binary-data"

    def test_key_persisted_between_instances(self, monkeypatch):
        _install_backend(monkeypatch)
        enc1 = Encryption("com.ptools.test2", user_name="tester")
        blob = enc1.encrypt("secret")
        enc2 = Encryption("com.ptools.test2", user_name="tester")
        assert enc2.decrypt(blob) == "secret"

    def test_distinct_nonces_per_encryption(self, monkeypatch):
        _install_backend(monkeypatch)
        enc = Encryption("com.ptools.test3", user_name="tester")
        a = enc.encrypt("same")
        b = enc.encrypt("same")
        assert a["nonce"] != b["nonce"]
        assert a["ciphertext"] != b["ciphertext"]


class TestDummyEncryption:
    def test_passes_through(self):
        dummy = DummyEncryption()
        assert dummy.encrypt("x") == "x"
        assert dummy.decrypt({"foo": "bar"}) == {"foo": "bar"}
