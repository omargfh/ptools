"""Tests for the ``ptools dev doctor`` command.

These tests monkeypatch ``ptools.utils.require.announced_requirements``
(and stub out the package-wide import walk) so the reporting/exit-code
logic is exercised against a small, deterministic requirement set
instead of whatever happens to be installed on the machine running the
suite.
"""
from click.testing import CliRunner

import ptools.dev as dev
from ptools.utils.require import BinaryRequirement, KeyRequirement, LibraryRequirement


def _patch_registry(monkeypatch, requirements):
    """Make ``doctor`` see exactly ``requirements`` without walking ptools."""
    monkeypatch.setattr(dev, "_import_all_ptools_submodules", lambda: [])
    monkeypatch.setattr(
        "ptools.utils.require.announced_requirements", lambda: list(requirements)
    )


def test_doctor_all_satisfied(monkeypatch):
    _patch_registry(monkeypatch, [
        LibraryRequirement(module="os"),
        BinaryRequirement(names=("ls",), logical_operator="and"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code == 0
    assert "[MISSING]" not in result.output
    assert "[ok]      os" in result.output
    assert "[ok]      ls" in result.output
    assert "All checked requirements are satisfied." in result.output


def test_doctor_reports_missing_library(monkeypatch):
    _patch_registry(monkeypatch, [
        LibraryRequirement(module="definitely_not_a_real_package_xyz"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code != 0
    assert "[MISSING] definitely_not_a_real_package_xyz" in result.output
    assert "pip install definitely_not_a_real_package_xyz" in result.output


def test_doctor_uses_pypi_name_for_install_hint(monkeypatch):
    _patch_registry(monkeypatch, [
        LibraryRequirement(module="definitely_not_a_real_package_xyz", pypi_name="TotallyFake"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code != 0
    assert "pip install TotallyFake" in result.output


def test_doctor_reports_missing_binary(monkeypatch):
    _patch_registry(monkeypatch, [
        BinaryRequirement(names=("definitely-missing-binary-xyz",), logical_operator="and"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code != 0
    assert "[MISSING] definitely-missing-binary-xyz" in result.output


def test_doctor_binary_or_satisfied_if_any_present(monkeypatch):
    _patch_registry(monkeypatch, [
        BinaryRequirement(names=("definitely-missing-binary-xyz", "ls"), logical_operator="or"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code == 0
    assert "[ok]" in result.output


def test_doctor_binary_and_fails_if_any_missing(monkeypatch):
    _patch_registry(monkeypatch, [
        BinaryRequirement(names=("ls", "definitely-missing-binary-xyz"), logical_operator="and"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code != 0
    assert "[MISSING]" in result.output


def test_doctor_key_requirement_reported_but_not_verified(monkeypatch):
    _patch_registry(monkeypatch, [
        LibraryRequirement(module="os"),
        KeyRequirement(name="api", aliases=("API_KEY", "API_TOKEN"), logical_operator="or"),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    # Key requirements can't be generically verified, so they must not
    # affect the exit code even though they're surfaced in the report.
    assert result.exit_code == 0
    assert "cannot verify" in result.output.lower()
    assert "API_KEY" in result.output
    assert "API_TOKEN" in result.output


def test_doctor_dedupes_library_by_module_name(monkeypatch):
    _patch_registry(monkeypatch, [
        LibraryRequirement(module="os"),
        LibraryRequirement(module="os", pypi_name="something-else", prompt_install=True),
    ])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code == 0
    assert result.output.count("os") == 1


def test_doctor_no_announced_requirements(monkeypatch):
    _patch_registry(monkeypatch, [])

    runner = CliRunner()
    result = runner.invoke(dev.cli, ["doctor"])

    assert result.exit_code == 0
    assert result.output.count("(none announced)") == 3
    assert "All checked requirements are satisfied." in result.output


class TestEditCommand:
    """``ptools dev edit`` (renamed from ``code``) opens ``$EDITOR``, not a
    hardcoded VSCode binary -- see ``ptools.settings.EDITOR``."""

    def test_code_command_no_longer_exists(self):
        assert "code" not in dev.cli.commands
        assert "edit" in dev.cli.commands

    def test_edit_project_uses_the_editor_setting(self, monkeypatch):
        monkeypatch.setattr(dev, "EDITOR", "nano")
        calls = []
        monkeypatch.setattr(dev.os, "system", lambda cmd: calls.append(cmd))

        runner = CliRunner()
        result = runner.invoke(dev.cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert calls == [f"nano {dev.get_project_root()}"]

    def test_edit_config_target_opens_the_ptools_config_dir(self, monkeypatch):
        monkeypatch.setattr(dev, "EDITOR", "nano")
        calls = []
        monkeypatch.setattr(dev.os, "system", lambda cmd: calls.append(cmd))

        runner = CliRunner()
        result = runner.invoke(dev.cli, ["edit", "--target", "config"])

        assert result.exit_code == 0, result.output
        assert len(calls) == 1
        assert calls[0].startswith("nano ")
        assert calls[0].endswith(".ptools")

    def test_edit_respects_a_different_editor_setting(self, monkeypatch):
        monkeypatch.setattr(dev, "EDITOR", "code")
        calls = []
        monkeypatch.setattr(dev.os, "system", lambda cmd: calls.append(cmd))

        runner = CliRunner()
        result = runner.invoke(dev.cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert calls == [f"code {dev.get_project_root()}"]

    def test_edit_help_mentions_the_editor_setting(self):
        runner = CliRunner()
        result = runner.invoke(dev.cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "EDITOR" in result.output
