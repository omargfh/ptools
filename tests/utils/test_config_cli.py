"""Tests for ``ptools.utils.config.config_to_CLI``'s interactive commands.

``get``/``set``/``delete`` take their key as an optional argument and fall
back to a picker, and ``edit`` is a browse/mutate loop. The picker
primitives are imported *inside* the command bodies, so these tests patch
them on their defining module (``ptools.lib.tui.select``) -- the same
place the runtime import resolves them from.
"""

import types

import pytest
from click.testing import CliRunner
from pydantic import BaseModel, Field

import ptools.utils.config as config_module
from ptools.utils.config import ConfigFile, _key_options, config_to_CLI


class DemoModel(BaseModel):
    """Two typed fields plus one that's only ever left at its default."""

    NAME: str = "demo"
    DEBUG: bool = False
    NOTE: str = Field(default="", description="a free-form note")


@pytest.fixture
def tty(monkeypatch):
    """Make ``require_tty`` believe stdin is a terminal.

    ``CliRunner`` installs a non-tty stdin, so without this every
    interactive path short-circuits to a usage error.
    """
    monkeypatch.setattr(
        config_module, "sys", types.SimpleNamespace(stdin=types.SimpleNamespace(isatty=lambda: True))
    )
    # Never reach for a real /dev/tty from the test process.
    monkeypatch.setattr(config_module, "_picker_output", lambda: None)


@pytest.fixture
def cfg(tmp_path):
    return ConfigFile(name="demo", path=str(tmp_path), quiet=True, model=DemoModel)


@pytest.fixture
def plain_cfg(tmp_path):
    """A config with no model -- a free-form key/value store."""
    return ConfigFile(name="plain", path=str(tmp_path), quiet=True)


def patch_select(monkeypatch, answers):
    """Replace ``SelectApp`` with a fake popping one canned answer per use."""
    import ptools.lib.tui.select as select_module

    remaining = list(answers)
    calls = []

    class FakeSelectApp:
        def __init__(self, items, message="", **kwargs):
            calls.append((message, [i[0] for i in items], items))

        def run(self):
            assert remaining, "unexpected extra SelectApp invocation"
            return remaining.pop(0)

    monkeypatch.setattr(select_module, "SelectApp", FakeSelectApp)
    return calls


def patch_ask_text(monkeypatch, answers):
    """Replace ``ask_text`` with a fake popping one canned answer per use."""
    import ptools.lib.tui.select as select_module

    remaining = list(answers)

    def fake_ask_text(message, placeholder="", default="", input=None, output=None):
        assert remaining, "unexpected extra ask_text invocation"
        return remaining.pop(0)

    monkeypatch.setattr(select_module, "ask_text", fake_ask_text)


class TestTypedValueCoercion:
    """A model-backed config validates values before they reach the disk."""

    def test_bool_field_is_stored_as_a_real_bool(self, cfg):
        cli = config_to_CLI(cfg, name="demo")
        result = CliRunner().invoke(cli, ["set", "DEBUG", "true"])

        assert result.exit_code == 0, result.output
        assert cfg.get("DEBUG") is True

    def test_unparseable_value_is_rejected_before_it_is_written(self, cfg):
        cli = config_to_CLI(cfg, name="demo")
        result = CliRunner().invoke(cli, ["set", "DEBUG", "not-a-bool"])

        assert result.exit_code == 2
        assert "Invalid value for 'DEBUG'" in result.output
        assert cfg.get("DEBUG") is False

    def test_rejected_value_leaves_the_config_readable(self, cfg, tmp_path):
        """Regression: a bad typed value used to brick the config.

        ``_validate`` runs on every read, so an unparseable value written
        to disk made *every* later command -- including the ``delete``
        that would undo it -- raise on load.
        """
        cli = config_to_CLI(cfg, name="demo")
        CliRunner().invoke(cli, ["set", "DEBUG", "not-a-bool"])

        reopened = ConfigFile(name="demo", path=str(tmp_path), quiet=True, model=DemoModel)
        assert reopened.get("DEBUG") is False

    def test_string_field_passes_through_unchanged(self, cfg):
        cli = config_to_CLI(cfg, name="demo")
        result = CliRunner().invoke(cli, ["set", "NAME", "renamed"])

        assert result.exit_code == 0, result.output
        assert cfg.get("NAME") == "renamed"

    def test_config_without_a_model_stores_raw_strings(self, plain_cfg):
        cli = config_to_CLI(plain_cfg, name="plain")
        result = CliRunner().invoke(cli, ["set", "anything", "true"])

        assert result.exit_code == 0, result.output
        assert plain_cfg.get("anything") == "true"

    def test_key_the_model_does_not_declare_is_rejected(self, cfg):
        """Otherwise the write reports success and vanishes on next read."""
        cli = config_to_CLI(cfg, name="demo")
        result = CliRunner().invoke(cli, ["set", "NOPE", "x"])

        assert result.exit_code == 2
        assert "not a valid key" in result.output
        assert "DEBUG, NAME, NOTE" in result.output

    def test_undeclared_key_is_not_written_to_disk(self, cfg, tmp_path):
        cli = config_to_CLI(cfg, name="demo")
        CliRunner().invoke(cli, ["set", "NOPE", "x"])

        reopened = ConfigFile(name="demo", path=str(tmp_path), quiet=True, model=DemoModel)
        assert "NOPE" not in reopened.data


class TestPickerOptions:
    """``_key_options`` builds the rows the picker renders."""

    def _fake_config(self, data, model=None, encryption=None):
        return types.SimpleNamespace(data=data, model=model, encryption=encryption)

    def test_stored_keys_are_described_by_their_value(self):
        options = _key_options(self._fake_config({"A": "one"}))
        assert options == [("A", "A", "one")]

    def test_long_values_are_elided_to_one_row(self):
        options = _key_options(self._fake_config({"A": "x" * 200}))
        _value, _label, description = options[0]

        assert description.endswith("…")
        assert len(description) <= config_module._PREVIEW_MAX

    def test_multiline_values_are_collapsed(self):
        options = _key_options(self._fake_config({"A": "one\ntwo"}))
        assert options[0][2] == "one two"

    def test_encrypted_values_are_masked(self):
        options = _key_options(self._fake_config({"A": "s3cret"}, encryption=object()))
        assert options[0][2] == "hidden"
        assert "s3cret" not in str(options)

    def test_unset_model_fields_are_offered_with_their_description(self, cfg):
        cfg.data = {"NAME": "demo"}
        options = _key_options(cfg, include_unset=True)
        rows = {value: description for value, _label, description in options}

        assert rows["NOTE"] == "a free-form note"
        assert rows["DEBUG"] == "unset"

    def test_new_key_row_is_offered_only_without_a_model(self, cfg, plain_cfg):
        """A model drops undeclared keys on read, so inventing one is a trap."""
        with_model = _key_options(cfg, allow_new=True)
        assert config_module._NEW_KEY not in [v for v, _l, _d in with_model]

        plain_cfg.data = {"A": "one"}
        without_model = _key_options(plain_cfg, allow_new=True)
        assert config_module._NEW_KEY in [v for v, _l, _d in without_model]


class TestInteractiveFallbacks:
    """Omitting the KEY argument opens the picker."""

    def test_get_prints_the_picked_value(self, cfg, tty, monkeypatch):
        calls = patch_select(monkeypatch, ["NAME"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["get"])

        assert result.exit_code == 0, result.output
        assert result.output.strip() == "demo"
        assert calls[0][0] == "Select a key:"

    def test_get_exits_nonzero_when_the_picker_is_cancelled(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, [None])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["get"])

        assert result.exit_code == 1

    def test_set_picks_a_key_then_prompts_for_a_value(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["NAME"])
        patch_ask_text(monkeypatch, ["picked-value"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["set"])

        assert result.exit_code == 0, result.output
        assert cfg.get("NAME") == "picked-value"

    def test_set_still_validates_a_value_typed_into_the_prompt(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["DEBUG"])
        patch_ask_text(monkeypatch, ["not-a-bool"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["set"])

        assert result.exit_code == 2
        assert "Invalid value for 'DEBUG'" in result.output

    def test_delete_confirms_before_removing_the_picked_key(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["NAME"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["delete"], input="y\n")

        assert result.exit_code == 0, result.output
        assert "NAME" not in cfg.data

    def test_declining_the_delete_confirmation_keeps_the_key(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["NAME"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["delete"], input="n\n")

        assert result.exit_code != 0
        assert "NAME" in cfg.data

    def test_an_explicit_key_never_opens_the_picker(self, cfg, tty, monkeypatch):
        import ptools.lib.tui.select as select_module

        class ExplodingSelectApp:
            def __init__(self, *a, **kw):
                raise AssertionError("picker opened despite an explicit KEY")

        monkeypatch.setattr(select_module, "SelectApp", ExplodingSelectApp)
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["get", "NAME"])

        assert result.exit_code == 0, result.output


class TestNonInteractiveUse:
    """Scripted use is unaffected: prompts degrade to usage errors."""

    @pytest.mark.parametrize("args", [["get"], ["set"], ["delete"], ["edit"]])
    def test_omitting_a_key_without_a_tty_is_a_usage_error(self, cfg, args):
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), args)

        assert result.exit_code == 2
        assert "interactive" in result.output

    def test_explicit_arguments_still_work_without_a_tty(self, cfg):
        cli = config_to_CLI(cfg, name="demo")
        runner = CliRunner()

        assert runner.invoke(cli, ["set", "NAME", "scripted"]).exit_code == 0
        assert runner.invoke(cli, ["get", "NAME"]).output.strip() == "scripted"


class TestEditLoop:
    """``edit`` re-shows the picker after each change until cancelled."""

    def test_setting_a_value_then_cancelling(self, cfg, tty, monkeypatch):
        # key picker -> action menu -> key picker again (cancel)
        patch_select(monkeypatch, ["NAME", "set", None])
        patch_ask_text(monkeypatch, ["edited"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["edit"])

        assert result.exit_code == 0, result.output
        assert cfg.get("NAME") == "edited"

    def test_deleting_a_key_then_cancelling(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["NAME", "delete", None])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["edit"])

        assert result.exit_code == 0, result.output
        assert "NAME" not in cfg.data

    def test_back_leaves_the_key_untouched(self, cfg, tty, monkeypatch):
        patch_select(monkeypatch, ["NAME", "back", None])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["edit"])

        assert result.exit_code == 0, result.output
        assert cfg.get("NAME") == "demo"

    def test_an_invalid_value_keeps_the_loop_alive(self, cfg, tty, monkeypatch):
        """A typo reports the error and returns to the picker, not the shell."""
        patch_select(monkeypatch, ["DEBUG", "set", None])
        patch_ask_text(monkeypatch, ["not-a-bool"])
        result = CliRunner().invoke(config_to_CLI(cfg, name="demo"), ["edit"])

        assert result.exit_code == 0, result.output
        assert "Invalid value for 'DEBUG'" in result.output
        assert cfg.get("DEBUG") is False
