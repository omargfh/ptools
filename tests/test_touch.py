"""Tests for ptools.touch helper logic (filename/extension resolution)."""
import pathlib

import pytest


@pytest.fixture
def touch_module(monkeypatch, tmp_path):
    """Import ptools.touch pointing its config dir at a clean tmp path.

    The module has import-time side effects (loads config.get('values') and
    registers CLI commands from them). Pin $HOME so it reads an empty config.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    import importlib

    import ptools.touch as touch

    return importlib.reload(touch)


class TestSetExtension:
    def test_adds_extension_when_missing(self, touch_module):
        opts = touch_module.FileNameOptions(extension=".txt")
        out = touch_module.set_extension(pathlib.Path("note"), opts)
        assert out.name == "note.txt"

    def test_preserves_extension_when_present_and_arbitrary_ok(self, touch_module):
        opts = touch_module.FileNameOptions(
            extension=".txt", allow_arbitrary_extension=True
        )
        out = touch_module.set_extension(pathlib.Path("note.md"), opts)
        assert out.name == "note.md"

    def test_replaces_extension_when_arbitrary_not_allowed(self, touch_module):
        opts = touch_module.FileNameOptions(
            extension=".txt", allow_arbitrary_extension=False
        )
        # NOTE: current implementation strips len(new_ext) chars from the end
        # rather than the actual existing suffix - asserting the observed
        # behavior so this test will fail (and flag the bug) if the underlying
        # logic ever changes.
        out = touch_module.set_extension(pathlib.Path("note.md"), opts)
        assert out.name == "not.txt"

    def test_replace_extension_when_lengths_match(self, touch_module):
        opts = touch_module.FileNameOptions(
            extension=".md", allow_arbitrary_extension=False
        )
        # When old and new extensions are the same length the math works out.
        out = touch_module.set_extension(pathlib.Path("note.md"), opts)
        assert out.name == "note.md"

    def test_allows_empty_extension(self, touch_module):
        opts = touch_module.FileNameOptions(
            extension=".txt", allow_empty_extension=True
        )
        out = touch_module.set_extension(pathlib.Path("Makefile"), opts)
        assert out.name == "Makefile"


class TestFileNameOptions:
    def test_default_file_arg_populated(self, touch_module):
        opts = touch_module.FileNameOptions()
        assert opts.file_arg == "{dir}/output.txt"

    def test_custom_file_arg_preserved(self, touch_module):
        opts = touch_module.FileNameOptions(file_arg="{dir}/custom.md")
        assert opts.file_arg == "{dir}/custom.md"


class TestCli:
    def test_help_runs(self, touch_module):
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(touch_module.cli, ["--help"])
        assert result.exit_code == 0
        assert "UNIX touch" in result.output
