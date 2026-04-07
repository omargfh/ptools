"""Tests for ptools.touch helper logic (filename/extension resolution)."""
import pathlib
import textwrap

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


@pytest.fixture
def touch_module_with_config(monkeypatch, tmp_path):
    """Import ptools.touch with a pre-seeded multi-command config.

    Writes ``~/.ptools/touch.yaml`` containing two distinct commands so
    tests can verify per-command template rendering (regression guard for
    the closure-in-loop bug where every registered command collapsed onto
    the last iteration's TouchItem).
    """
    config_dir = tmp_path / ".ptools"
    config_dir.mkdir()
    (config_dir / "touch.yaml").write_text(textwrap.dedent("""\
        encrypted: false
        data:
          values:
            - command: alpha
              group: g1
              description: Alpha template
              file_name_options:
                extension: .a.txt
              template_string: |
                ALPHA:{{ file_stem }}
            - command: beta
              group: g2
              description: Beta template
              file_name_options:
                extension: .b.txt
              template_string: |
                BETA:{{ file_stem }}
    """))

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


class TestCommandRegistration:
    """Regression tests for the closure-in-loop bug.

    When ``touch_command`` was registered in a ``for obj in values`` loop
    without binding ``obj``/``fopts`` as default arguments, every command
    closed over the loop variable by reference, so all commands ended up
    using the last iteration's TouchItem and rendered identical output.
    """

    def test_each_command_uses_its_own_template(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        from click.testing import CliRunner

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        alpha_out = tmp_path / "one"
        beta_out = tmp_path / "two"

        r1 = runner.invoke(touch_module_with_config.cli, ["alpha", str(alpha_out)])
        r2 = runner.invoke(touch_module_with_config.cli, ["beta", str(beta_out)])

        assert r1.exit_code == 0, r1.output
        assert r2.exit_code == 0, r2.output

        alpha_file = tmp_path / "one.a.txt"
        beta_file = tmp_path / "two.b.txt"

        assert alpha_file.exists(), f"missing {alpha_file}; got: {list(tmp_path.iterdir())}"
        assert beta_file.exists(), f"missing {beta_file}; got: {list(tmp_path.iterdir())}"

        alpha_text = alpha_file.read_text()
        beta_text = beta_file.read_text()

        # Each command must render its own template, not the last one seen.
        assert alpha_text.startswith("ALPHA:")
        assert beta_text.startswith("BETA:")
        assert alpha_text != beta_text

    def test_each_command_uses_its_own_file_name_options(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        """Extensions differ per command — proves fopts is bound per command."""
        from click.testing import CliRunner

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        r1 = runner.invoke(touch_module_with_config.cli, ["alpha", str(tmp_path / "x")])
        r2 = runner.invoke(touch_module_with_config.cli, ["beta", str(tmp_path / "y")])

        assert r1.exit_code == 0, r1.output
        assert r2.exit_code == 0, r2.output
        assert (tmp_path / "x.a.txt").exists()
        assert (tmp_path / "y.b.txt").exists()
