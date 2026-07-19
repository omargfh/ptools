"""Tests for ``ptools.vault`` -- file encryption/decryption commands.

Round-trip coverage for all four commands (seal/unseal password-based,
bury/dig keyring-based), plus the wrong-password failure path. By
default, every command overwrites INPUT_FILE in place when OUTPUT_FILE
is omitted; setting ``VAULT_IN_PLACE=false`` (``ptools.settings``)
switches that same omitted-OUTPUT_FILE case to printing the result to
stdout and leaving INPUT_FILE untouched instead. Every fixture here
creates its own throwaway file under ``tmp_path`` -- an in-place write
can never touch anything outside a test's own sandbox.
"""
from click.testing import CliRunner

import keyring
from keyring.backend import KeyringBackend

from ptools.vault import cli


class InMemoryKeyring(KeyringBackend):
    """Minimal keyring backend so bury/dig never touch the real OS keychain."""
    priority = 1  # type: ignore[assignment]

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


def _install_fake_keyring(monkeypatch):
    """Route all keyring calls to an in-memory backend, never the real one."""
    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    return backend


PLAINTEXT = b"the quick brown fox jumps over the lazy dog\x00\x01\x02"
PASSWORD = "correct-horse-battery-staple"


class TestSealUnsealRoundTrip:
    """Password-based seal/unseal round trips."""

    def test_explicit_output_file_round_trips(self, tmp_path):
        runner = CliRunner()
        input_file = tmp_path / "plain.txt"
        input_file.write_bytes(PLAINTEXT)
        sealed_file = tmp_path / "sealed.vault"
        recovered_file = tmp_path / "recovered.txt"

        result = runner.invoke(cli, ["seal", str(input_file), str(sealed_file), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        assert sealed_file.read_bytes() != PLAINTEXT
        assert input_file.read_bytes() == PLAINTEXT  # explicit output leaves input untouched

        result = runner.invoke(cli, ["unseal", str(sealed_file), str(recovered_file), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        assert recovered_file.read_bytes() == PLAINTEXT

    def test_in_place_round_trips(self, tmp_path):
        runner = CliRunner()
        target = tmp_path / "in_place.txt"
        target.write_bytes(PLAINTEXT)

        result = runner.invoke(cli, ["seal", str(target), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        assert target.read_bytes() != PLAINTEXT  # overwritten in place with ciphertext

        result = runner.invoke(cli, ["unseal", str(target), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        assert target.read_bytes() == PLAINTEXT  # restored in place

    def test_vault_in_place_false_prints_to_stdout_and_leaves_input_untouched(self, tmp_path):
        runner = CliRunner()
        target = tmp_path / "in_place.txt"
        target.write_bytes(PLAINTEXT)

        result = runner.invoke(
            cli, ["seal", str(target), "-p", PASSWORD], env={"VAULT_IN_PLACE": "0"}
        )
        assert result.exit_code == 0, result.output
        assert "'nonce'" in result.output  # the encrypted dict repr, printed
        assert target.read_bytes() == PLAINTEXT  # input left byte-identical

        # Seal for real (default, in-place) so unseal has a vault file to read.
        result = runner.invoke(cli, ["seal", str(target), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        sealed_bytes = target.read_bytes()

        result = runner.invoke(
            cli, ["unseal", str(target), "-p", PASSWORD], env={"VAULT_IN_PLACE": "0"}
        )
        assert result.exit_code == 0, result.output
        assert result.output.encode("utf-8").rstrip(b"\n") == PLAINTEXT
        assert target.read_bytes() == sealed_bytes  # input left byte-identical

    def test_explicit_output_file_wins_over_vault_in_place_false(self, tmp_path):
        """An explicit OUTPUT_FILE always writes to disk, setting notwithstanding."""
        runner = CliRunner()
        input_file = tmp_path / "plain.txt"
        input_file.write_bytes(PLAINTEXT)
        sealed_file = tmp_path / "sealed.vault"

        result = runner.invoke(
            cli,
            ["seal", str(input_file), str(sealed_file), "-p", PASSWORD],
            env={"VAULT_IN_PLACE": "0"},
        )
        assert result.exit_code == 0, result.output
        assert sealed_file.read_bytes() != PLAINTEXT
        assert input_file.read_bytes() == PLAINTEXT


class TestWrongPassword:
    """A wrong password must fail loudly and leave the input file untouched.

    This pins the load-bearing ordering: ``decrypt`` raises before
    ``open(output_file, "wb")`` runs, so a mistyped password on an
    in-place unseal cannot truncate the ciphertext. The error is a
    single ``click.ClickException`` line, not a raw traceback, and it
    names wrong-password-or-corrupt-file as the cause without claiming
    to know which -- GCM's MAC check can't distinguish the two.
    """

    def test_wrong_password_leaves_file_untouched(self, tmp_path):
        runner = CliRunner()
        target = tmp_path / "in_place.txt"
        target.write_bytes(PLAINTEXT)

        result = runner.invoke(cli, ["seal", str(target), "-p", PASSWORD])
        assert result.exit_code == 0, result.output
        sealed_bytes = target.read_bytes()

        result = runner.invoke(cli, ["unseal", str(target), "-p", "wrong-password"])
        assert result.exit_code != 0
        assert result.output.count("Error:") == 1
        assert "wrong password or corrupted file" in result.output
        assert "Traceback" not in result.output
        assert target.read_bytes() == sealed_bytes


class TestCodePayloadIsNotExecuted:
    """Vault files are parsed with ``ast.literal_eval``, which can only ever
    produce Python literals -- it never calls, imports, or executes
    anything. A file crafted to look like a call must fail to parse
    rather than run; the raised error alone proves it, so these tests
    assert on the failure and do not check for any executed side effect.

    ``vault.py`` catches the parse failure and re-raises it as a
    ``click.ClickException``, which Click's runner renders as a single
    ``Error:`` line and a clean exit rather than a traceback.
    """

    PAYLOAD = '__import__("os").system("echo PWNED")'

    def test_unseal_rejects_a_code_payload(self, tmp_path):
        runner = CliRunner()
        target = tmp_path / "malicious.vault"
        target.write_text(self.PAYLOAD)

        result = runner.invoke(cli, ["unseal", str(target), "-p", "irrelevant"])

        assert result.exit_code != 0
        assert result.output.count("Error:") == 1
        assert "not a valid vault file" in result.output

    def test_dig_rejects_a_code_payload(self, tmp_path, monkeypatch):
        _install_fake_keyring(monkeypatch)
        runner = CliRunner()
        target = tmp_path / "malicious.vault"
        target.write_text(self.PAYLOAD)

        result = runner.invoke(cli, ["dig", str(target)])

        assert result.exit_code != 0
        assert result.output.count("Error:") == 1
        assert "not a valid vault file" in result.output


class TestMalformedVaultFile:
    """A syntactically valid literal missing required vault fields is not
    an execution risk (see ``TestCodePayloadIsNotExecuted``) but is still
    a malformed vault file: ``decrypt`` raises ``KeyError``, which must
    also become a clean ``ClickException`` rather than a traceback.
    """

    def test_unseal_rejects_a_dict_missing_required_fields(self, tmp_path):
        runner = CliRunner()
        target = tmp_path / "malformed.vault"
        target.write_text("{'nonce': 'ab', 'ciphertext': 'cd'}")  # no 'tag'/'salt'

        result = runner.invoke(cli, ["unseal", str(target), "-p", "irrelevant"])

        assert result.exit_code != 0
        assert result.output.count("Error:") == 1
        assert "Traceback" not in result.output


class TestBuryDigRoundTrip:
    """Keyring-based bury/dig, exercised against a monkeypatched keyring only."""

    def test_explicit_output_file_round_trips(self, tmp_path, monkeypatch):
        _install_fake_keyring(monkeypatch)
        runner = CliRunner()
        input_file = tmp_path / "plain.txt"
        input_file.write_bytes(PLAINTEXT)
        buried_file = tmp_path / "buried.vault"
        recovered_file = tmp_path / "recovered.txt"

        result = runner.invoke(cli, ["bury", str(input_file), str(buried_file)])
        assert result.exit_code == 0, result.output
        assert buried_file.read_bytes() != PLAINTEXT

        result = runner.invoke(cli, ["dig", str(buried_file), str(recovered_file)])
        assert result.exit_code == 0, result.output
        assert recovered_file.read_bytes() == PLAINTEXT

    def test_in_place_round_trips(self, tmp_path, monkeypatch):
        _install_fake_keyring(monkeypatch)
        runner = CliRunner()
        target = tmp_path / "in_place.txt"
        target.write_bytes(PLAINTEXT)

        result = runner.invoke(cli, ["bury", str(target)])
        assert result.exit_code == 0, result.output
        assert target.read_bytes() != PLAINTEXT

        result = runner.invoke(cli, ["dig", str(target)])
        assert result.exit_code == 0, result.output
        assert target.read_bytes() == PLAINTEXT

    def test_vault_in_place_false_prints_to_stdout_and_leaves_input_untouched(
        self, tmp_path, monkeypatch
    ):
        _install_fake_keyring(monkeypatch)
        runner = CliRunner()
        target = tmp_path / "in_place.txt"
        target.write_bytes(PLAINTEXT)

        result = runner.invoke(cli, ["bury", str(target)], env={"VAULT_IN_PLACE": "0"})
        assert result.exit_code == 0, result.output
        assert "'nonce'" in result.output  # the encrypted dict repr, printed
        assert target.read_bytes() == PLAINTEXT  # input left byte-identical

        # Bury for real (default, in-place) so dig has a vault file to read.
        result = runner.invoke(cli, ["bury", str(target)])
        assert result.exit_code == 0, result.output
        buried_bytes = target.read_bytes()

        result = runner.invoke(cli, ["dig", str(target)], env={"VAULT_IN_PLACE": "0"})
        assert result.exit_code == 0, result.output
        assert result.output.encode("utf-8").rstrip(b"\n") == PLAINTEXT
        assert target.read_bytes() == buried_bytes  # input left byte-identical
