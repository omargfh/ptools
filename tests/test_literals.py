"""Tests for ptools.literals: the lget picker and the lget-add wizard."""
import json

import pytest


@pytest.fixture
def literals_module(isolated_home):
    """Import ptools.literals against an isolated, pre-seeded config file.

    ``ptools.literals`` builds its module-level ``ConfigFile`` at import
    time (it's not lazy like touch.py's), so $HOME must be pinned before
    the module is (re)imported. Writing the file ourselves — rather than
    letting it seed from the packaged starter — keeps the fixture data
    small and stable regardless of what starters/literals.json contains.
    """
    config_dir = isolated_home / ".ptools"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "literals.json").write_text(json.dumps({
        "encrypted": False,
        "data": {"colors": {"red": "#ff0000"}},
    }))

    import importlib

    import ptools.literals as literals

    return importlib.reload(literals)


def patch_selector(monkeypatch, module, answers):
    """Replace the shared ``select`` adapter with a fake that pops canned *answers*.

    Returns the list of ``(title, option_values, options)`` calls for
    assertions, mirroring tests/test_touch.py's helper.
    """
    remaining = list(answers)
    calls = []

    def fake(options, title="", **kwargs):
        calls.append((title, [option[0] for option in options], options))
        assert remaining, f"unexpected selector call: {title!r}"
        return remaining.pop(0)

    monkeypatch.setattr(module, "select", fake)
    return calls


def patch_text(monkeypatch, module, answers):
    """Replace the shared ``text`` adapter with a fake that pops canned *answers*."""
    remaining = list(answers)
    calls = []

    def fake(message, placeholder="", **kwargs):
        calls.append((message, placeholder))
        assert remaining, f"unexpected text prompt: {message!r}"
        return remaining.pop(0)

    monkeypatch.setattr(module, "text", fake)
    return calls


def read_persisted_data(isolated_home):
    """Re-instantiate ConfigFile to prove a write reached disk, not just memory."""
    from ptools.utils.config import ConfigFile

    fresh = ConfigFile("literals", quiet=True)
    return fresh.data


class TestAddCommand:
    """Tests for the `lget-add` wizard (``literals.add``)."""

    def _run(self, module, input_text=""):
        from click.testing import CliRunner

        runner = CliRunner()
        return runner.invoke(module.add, [], input=input_text)

    def test_add_to_existing_collection(self, literals_module, monkeypatch, isolated_home):
        calls = patch_selector(monkeypatch, literals_module, ["colors"])
        patch_text(monkeypatch, literals_module, ["blue", "#0000ff"])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "Added 'blue' to 'colors'" in result.output
        assert calls[0][1] == ["colors", literals_module.NEW_COLLECTION]

        data = read_persisted_data(isolated_home)
        assert data["colors"] == {"red": "#ff0000", "blue": "#0000ff"}

    def test_create_new_collection(self, literals_module, monkeypatch, isolated_home):
        patch_selector(monkeypatch, literals_module, [literals_module.NEW_COLLECTION])
        patch_text(monkeypatch, literals_module, ["shapes", "circle", "○"])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "Added 'circle' to 'shapes'" in result.output

        data = read_persisted_data(isolated_home)
        assert data["shapes"] == {"circle": "○"}
        # The pre-existing collection is untouched.
        assert data["colors"] == {"red": "#ff0000"}

    def test_duplicate_key_rejected_with_no_partial_write(
        self, literals_module, monkeypatch, isolated_home
    ):
        patch_selector(monkeypatch, literals_module, ["colors"])
        text_calls = patch_text(monkeypatch, literals_module, ["red"])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "already exists" in result.output
        # The value prompt must never fire once the key is rejected.
        assert [message for message, _ in text_calls] == ["Key:"]

        data = read_persisted_data(isolated_home)
        assert data["colors"] == {"red": "#ff0000"}

    def test_new_collection_name_matching_existing_collection_merges(
        self, literals_module, monkeypatch, isolated_home
    ):
        """Typing an existing collection's name via the '+ new collection'
        path targets that same collection, so duplicate-key rejection still
        applies -- it doesn't shadow the existing collection with a blank one.
        """
        patch_selector(monkeypatch, literals_module, [literals_module.NEW_COLLECTION])
        patch_text(monkeypatch, literals_module, ["colors", "red"])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "already exists" in result.output

        data = read_persisted_data(isolated_home)
        assert data["colors"] == {"red": "#ff0000"}

    def test_no_collection_selected_aborts(self, literals_module, monkeypatch, isolated_home):
        patch_selector(monkeypatch, literals_module, [None])
        patch_text(monkeypatch, literals_module, [])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "No collection selected" in result.output

        data = read_persisted_data(isolated_home)
        assert data == {"colors": {"red": "#ff0000"}}

    def test_no_collection_name_given_aborts(self, literals_module, monkeypatch, isolated_home):
        patch_selector(monkeypatch, literals_module, [literals_module.NEW_COLLECTION])
        patch_text(monkeypatch, literals_module, [""])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "No collection name given" in result.output

        data = read_persisted_data(isolated_home)
        assert data == {"colors": {"red": "#ff0000"}}

    def test_no_key_given_aborts(self, literals_module, monkeypatch, isolated_home):
        patch_selector(monkeypatch, literals_module, ["colors"])
        patch_text(monkeypatch, literals_module, [""])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "No key given" in result.output

        data = read_persisted_data(isolated_home)
        assert data == {"colors": {"red": "#ff0000"}}

    def test_no_value_given_aborts_without_write(self, literals_module, monkeypatch, isolated_home):
        patch_selector(monkeypatch, literals_module, ["colors"])
        patch_text(monkeypatch, literals_module, ["green", ""])

        result = self._run(literals_module)

        assert result.exit_code == 0, result.output
        assert "No value given" in result.output

        data = read_persisted_data(isolated_home)
        assert data == {"colors": {"red": "#ff0000"}}

    def test_collection_picker_offers_new_collection_option(
        self, literals_module, monkeypatch, isolated_home
    ):
        calls = patch_selector(monkeypatch, literals_module, ["colors"])
        patch_text(monkeypatch, literals_module, ["blue", "#0000ff"])

        self._run(literals_module)

        assert literals_module.NEW_COLLECTION in calls[0][1]

    def test_persisted_entry_visible_on_next_invocation(
        self, literals_module, monkeypatch, isolated_home
    ):
        """Regression guard: the entry must survive a fresh ConfigFile load,
        not just live on the in-memory config.data dict from this process.
        """
        patch_selector(monkeypatch, literals_module, ["colors"])
        patch_text(monkeypatch, literals_module, ["blue", "#0000ff"])

        result = self._run(literals_module)
        assert result.exit_code == 0, result.output

        # Simulate "next invocation" via a fresh ConfigFile instance,
        # entirely independent from literals_module.config.
        from ptools.utils.config import ConfigFile

        fresh = ConfigFile("literals", quiet=True)
        assert fresh.data["colors"]["blue"] == "#0000ff"

        # And via reloading the module, mirroring how a new process would
        # re-run literals.py's module-level `config = ConfigFile(...)`.
        import importlib

        reloaded = importlib.reload(literals_module)
        assert reloaded.config.data["colors"]["blue"] == "#0000ff"
