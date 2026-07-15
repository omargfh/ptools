"""Tests for ``ptools.settings`` -- the ptools-wide settings model/CLI.

Mirrors ``tests/test_touch.py``'s pattern for modules with import-time
side effects: pin ``$HOME`` to a fresh ``tmp_path`` and ``importlib.reload``
so each test gets its own isolated ``~/.ptools/settings.json``.

That isolation matters more here than usual: ``ConfigFile.__init__``
validates an *empty* dict against the model on first access, which
fills in every field's default and immediately persists the whole
thing to disk (see ``src/ptools/utils/config.py``). Reusing one home
directory across two different ``$EDITOR`` env-var scenarios would
silently keep whichever value was first persisted, so every scenario
below gets a brand new ``tmp_path``.
"""

import importlib

import pytest
from click.testing import CliRunner


def _reload_settings(monkeypatch, tmp_path, **env):
    """Reload ``ptools.settings`` against an isolated, empty $HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("EDITOR", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import ptools.settings as settings

    return importlib.reload(settings)


@pytest.fixture
def settings_module(monkeypatch, tmp_path):
    return _reload_settings(monkeypatch, tmp_path)


class TestEditorSetting:
    """``EDITOR`` follows the same env/persisted/default priority as PIP_EXECUTABLE."""

    def test_defaults_to_vim_when_editor_env_unset(self, settings_module):
        assert settings_module.EDITOR == "vim"
        assert settings_module.settings.typed.EDITOR == "vim"

    def test_respects_editor_env_var(self, monkeypatch, tmp_path):
        settings_mod = _reload_settings(monkeypatch, tmp_path, EDITOR="nano")
        assert settings_mod.EDITOR == "nano"
        assert settings_mod.settings.typed.EDITOR == "nano"

    def test_get_and_set_work_for_free_via_config_to_CLI(self, settings_module):
        """No hand-rolled CLI command needed: config_to_CLI already wires get/set."""
        runner = CliRunner()

        result = runner.invoke(settings_module.cli, ["set", "EDITOR", "nvim"])
        assert result.exit_code == 0, result.output
        assert "Set 'EDITOR' to 'nvim'." in result.output

        result = runner.invoke(settings_module.cli, ["get", "EDITOR"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "nvim"

    def test_persisted_value_survives_a_reload(self, settings_module, monkeypatch):
        runner = CliRunner()
        result = runner.invoke(settings_module.cli, ["set", "EDITOR", "emacs"])
        assert result.exit_code == 0, result.output

        reloaded = importlib.reload(settings_module)
        assert reloaded.EDITOR == "emacs"
        assert reloaded.settings.typed.EDITOR == "emacs"

    def test_editor_appears_in_settings_list_output(self, settings_module):
        runner = CliRunner()
        result = runner.invoke(settings_module.cli, ["list"])
        assert result.exit_code == 0, result.output
        assert "EDITOR" in result.output
        assert "vim" in result.output


class TestSettingsModelGenericFieldAddition:
    """A plain new ``str`` field on SettingsModel just works everywhere."""

    def test_editor_field_is_a_plain_string_with_a_hardcoded_fallback(self, settings_module):
        model = settings_module.SettingsModel()
        assert isinstance(model.EDITOR, str)
        assert model.EDITOR  # never blank -- hard-coded "vim" is the floor

    def test_editor_is_independent_of_the_other_settings_fields(self, monkeypatch, tmp_path):
        settings_mod = _reload_settings(monkeypatch, tmp_path, EDITOR="code")
        assert settings_mod.EDITOR == "code"
        # PIP_EXECUTABLE/PTOOLS_DEBUG are untouched by the EDITOR override.
        assert settings_mod.PTOOLS_DEBUG is False
        assert "pip" in settings_mod.PIP_EXECUTABLE
