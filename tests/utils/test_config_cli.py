"""Tests for value/key validation in ``ptools.utils.config.config_to_CLI``.

A model-backed config declares field types, but the CLI hands over raw
strings; these cover the coercion and rejection that happens before a
value reaches the disk.
"""

import pytest
from click.testing import CliRunner
from pydantic import BaseModel, Field

from ptools.utils.config import ConfigFile, config_to_CLI


class DemoModel(BaseModel):
    """Two typed fields plus one that's only ever left at its default."""

    NAME: str = "demo"
    DEBUG: bool = False
    NOTE: str = Field(default="", description="a free-form note")


@pytest.fixture
def cfg(tmp_path):
    return ConfigFile(name="demo", path=str(tmp_path), quiet=True, model=DemoModel)


@pytest.fixture
def plain_cfg(tmp_path):
    """A config with no model -- a free-form key/value store."""
    return ConfigFile(name="plain", path=str(tmp_path), quiet=True)


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
