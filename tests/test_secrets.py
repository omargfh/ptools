"""Tests for ``ptools secrets`` -- exit codes and error reporting.

``SecretsConfig`` always builds an encrypted ``ConfigFile``
(``secrets.py:16``), which routes through the system keyring. Every test
here isolates ``$HOME`` (the shared ``isolated_home`` fixture) and installs
an in-memory keyring backend so nothing in this file ever reads, writes, or
prompts against the developer's real macOS keychain or real ``~/.ptools``.
"""
import keyring
import pytest
from click.testing import CliRunner
from keyring.backend import KeyringBackend

import ptools.secrets as secrets_cli


class InMemoryKeyring(KeyringBackend):
    """Minimal in-memory keyring backend; mirrors tests/utils/test_encrypt.py."""
    priority = 1  # type: ignore[assignment]

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


@pytest.fixture
def secrets_keyring(monkeypatch):
    """Install an in-memory keyring so encrypted config writes never reach
    the real system keychain."""
    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    # secrets.py routes through Encryption, which calls the module-level
    # keyring.get_password/set_password helpers directly.
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    return backend


@pytest.fixture
def secrets_env(isolated_home, secrets_keyring):
    """Isolated $HOME + in-memory keyring: the baseline for every secrets
    CLI test in this file."""
    return isolated_home


def _set(runner, key, value):
    result = runner.invoke(secrets_cli.cli, ["set", key, value])
    assert result.exit_code == 0, result.output
    return result


class TestGetMissingKey:
    def test_plain_exits_nonzero_with_single_error_line(self, secrets_env):
        runner = CliRunner()
        result = runner.invoke(secrets_cli.cli, ["get", "MISSING"])

        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert result.output.count("Error:") == 1
        assert "Secret 'MISSING' not found." in result.output

    def test_quiet_exits_nonzero_and_writes_nothing_to_stdout(self, secrets_env):
        runner = CliRunner()
        result = runner.invoke(secrets_cli.cli, ["get", "MISSING", "--quiet"])

        assert result.exit_code != 0
        assert result.stdout == ""

    def test_message_emitted_once_not_as_warning_and_exception(self, secrets_env):
        runner = CliRunner()
        result = runner.invoke(secrets_cli.cli, ["get", "MISSING"])

        assert result.exit_code != 0
        assert result.output.lower().count("not found") == 1


class TestGetExistingKey:
    def test_plain_prints_formatted_success_and_exits_zero(self, secrets_env):
        runner = CliRunner()
        _set(runner, "API_TOKEN", "test-token")

        result = runner.invoke(secrets_cli.cli, ["get", "API_TOKEN"])

        assert result.exit_code == 0, result.output
        assert "Secret 'API_TOKEN': test-token" in result.output

    def test_quiet_prints_bare_value_and_exits_zero(self, secrets_env):
        runner = CliRunner()
        _set(runner, "API_TOKEN", "test-token")

        result = runner.invoke(secrets_cli.cli, ["get", "API_TOKEN", "--quiet"])

        assert result.exit_code == 0, result.output
        assert result.stdout.strip() == "test-token"
