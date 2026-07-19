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
import json

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
        # The env override is not baked into the persisted/hard-coded
        # tier -- only the resolved value (get()/the module constant) sees it.
        assert settings_mod.settings.typed.EDITOR == "vim"

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


class TestEnvOverridesPersistedValue:
    """Regression coverage for the env-over-file precedence bug.

    Previously a key present in ``settings.json`` won permanently -- an
    env var could never override it, and env values got baked into the
    field defaults at import time. ``get()`` now resolves env, then the
    persisted file, then the hard-coded default, on every call.
    """

    def _seed(self, tmp_path, **data):
        config_dir = tmp_path / ".ptools"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "settings.json").write_text(json.dumps({
            "encrypted": False,
            "data": data,
        }))

    def test_env_overrides_a_stored_value(self, monkeypatch, tmp_path):
        self._seed(tmp_path, EDITOR="stored-nano")
        settings_mod = _reload_settings(monkeypatch, tmp_path, EDITOR="env-code")

        assert settings_mod.get("EDITOR") == "env-code"

    def test_stored_value_used_when_env_is_unset(self, monkeypatch, tmp_path):
        self._seed(tmp_path, EDITOR="stored-nano")
        settings_mod = _reload_settings(monkeypatch, tmp_path)

        assert settings_mod.get("EDITOR") == "stored-nano"

    def test_hardcoded_default_when_neither_env_nor_stored(self, monkeypatch, tmp_path):
        settings_mod = _reload_settings(monkeypatch, tmp_path)

        assert settings_mod.get("EDITOR") == "vim"

    def test_env_mutation_after_import_changes_the_next_get_call(self, monkeypatch, tmp_path):
        settings_mod = _reload_settings(monkeypatch, tmp_path)
        assert settings_mod.get("EDITOR") == "vim"

        monkeypatch.setenv("EDITOR", "code")
        assert settings_mod.get("EDITOR") == "code"

    def test_env_var_is_not_persisted_to_disk(self, monkeypatch, tmp_path):
        """A one-off env override must not get baked into the config file."""
        _reload_settings(monkeypatch, tmp_path, EDITOR="one-off-editor")

        on_disk = json.loads((tmp_path / ".ptools" / "settings.json").read_text())
        assert on_disk["data"]["EDITOR"] == "vim"

    def test_ptools_debug_env_var_truthiness_is_exact(self, monkeypatch, tmp_path):
        """Only \"1\" is true -- matches the historical field-default rule."""
        settings_mod = _reload_settings(monkeypatch, tmp_path, PTOOLS_DEBUG="1")
        assert settings_mod.get("PTOOLS_DEBUG") is True

        monkeypatch.setenv("PTOOLS_DEBUG", "true")
        assert settings_mod.get("PTOOLS_DEBUG") is False

        monkeypatch.setenv("PTOOLS_DEBUG", "0")
        assert settings_mod.get("PTOOLS_DEBUG") is False

    @pytest.mark.parametrize(
        "field_name, env_var_name",
        [
            ("PIP_EXECUTABLE", "PIP_EXECUTABLE"),
            ("PTOOLS_DEBUG", "PTOOLS_DEBUG"),
            ("EDITOR", "EDITOR"),
            ("SHELL_EXECUTABLE", "PTOOLS_SHELL"),
            ("SHELL_CONFIG", "PTOOLS_SHELL_CONFIG"),
        ],
    )
    def test_env_var_names_match_the_documented_mapping(
        self, monkeypatch, tmp_path, field_name, env_var_name
    ):
        settings_mod = _reload_settings(monkeypatch, tmp_path, **{env_var_name: "probe-value"})

        if field_name == "PTOOLS_DEBUG":
            assert settings_mod.get(field_name) is False  # "probe-value" != "1"
        else:
            assert settings_mod.get(field_name) == "probe-value"


class TestGetAndSetFunctions:
    """``get``/``set`` are the documented API (``settings.py:11-16``)."""

    def test_get_and_set_exist(self, settings_module):
        assert hasattr(settings_module, "get")
        assert hasattr(settings_module, "set")

    def test_docstring_example_runs(self, settings_module):
        """``settings.set("PIP_EXECUTABLE", "uv pip")`` from the module docstring."""
        settings_module.set("PIP_EXECUTABLE", "uv pip")
        assert settings_module.get("PIP_EXECUTABLE") == "uv pip"

    def test_set_persists_to_the_config_file(self, settings_module, tmp_path):
        settings_module.set("EDITOR", "helix")

        on_disk = json.loads((tmp_path / ".ptools" / "settings.json").read_text())
        assert on_disk["data"]["EDITOR"] == "helix"


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
