"""Tests for ptools.touch helper logic (filename/extension resolution)."""
import os
import pathlib
import textwrap

import pytest


@pytest.fixture
def touch_module(monkeypatch, tmp_path):
    """Import ptools.touch pointing its config dir at an explicitly empty config.

    The module has import-time side effects (loads config.get('values') and
    registers CLI commands from them). Pin $HOME and write an empty config —
    a *missing* config would be seeded from the packaged starter templates.
    """
    config_dir = tmp_path / ".ptools"
    config_dir.mkdir()
    (config_dir / "touch.yaml").write_text("encrypted: false\ndata:\n  values: []\n")

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
              name: Alpha File
              group: g1
              description: Alpha template
              example: notes/my-note
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
            - command: gamma
              group: g2
              description: Gamma template
              file_name_options:
                extension: .c.txt
              arguments:
                tag:
                  help: Tag name
                  example: v1.0
                greeting:
                  help: Greeting word
                  default: hello
              template_string: |
                GAMMA:{{ greeting }}:{{ tag }}
          groups_meta:
            g1:
              name: Group One
              description: First group
            g2:
              description: Second group
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
        out = touch_module.set_extension(pathlib.Path("note.md"), opts)
        assert out.name == "note.txt"

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


def patch_selector(monkeypatch, module, answers):
    """Replace the shared ``select`` adapter with a fake that pops canned *answers*.

    Returns the list of ``(title, option_values, options)`` calls for
    assertions.
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
    """Replace the shared ``text`` adapter with a fake that pops canned *answers*.

    Returns the list of ``(message, placeholder)`` calls for assertions.
    """
    remaining = list(answers)
    calls = []

    def fake(message, placeholder="", **kwargs):
        calls.append((message, placeholder))
        assert remaining, f"unexpected text prompt: {message!r}"
        return remaining.pop(0)

    monkeypatch.setattr(module, "text", fake)
    return calls


class TestSelectItem:
    """Unit tests for the two-step group -> template selection."""

    def _items(self, module, specs):
        return [
            module.TouchItem(command=c, group=g, description=f"{c} desc", template_string="X")
            for c, g in specs
        ]

    def test_two_step_selection(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g2"), ("c", "g2")])
        calls = patch_selector(monkeypatch, touch_module, ["g2", "c"])

        selected = touch_module._select_item(items, {})

        assert selected is items[2]
        # First step shows the groups alone; second only g2's templates.
        assert calls[0][1] == ["g1", "g2"]
        assert calls[1][1] == ["b", "c"]

    def test_group_options_carry_counts_and_descriptions(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g2"), ("c", "g2")])
        groups_meta = {"g1": touch_module.GroupMeta(description="First group")}
        calls = patch_selector(monkeypatch, touch_module, ["g2", "c"])

        touch_module._select_item(items, groups_meta)

        assert calls[0][2] == [
            ("g1", "g1 (1)", "First group"),
            ("g2", "g2 (2)", ""),
        ]
        # Template descriptions render as the dim third element.
        assert calls[1][2] == [("b", "b", "b desc"), ("c", "c", "c desc")]

    def test_display_names_override_keys_in_labels(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g2")])
        items[0].name = "Pretty A"
        groups_meta = {"g1": touch_module.GroupMeta(name="Group One")}
        calls = patch_selector(monkeypatch, touch_module, ["g1", "a"])

        selected = touch_module._select_item(items, groups_meta)

        assert selected is items[0]
        # Values stay the group key / command; labels use display names.
        assert calls[0][2] == [("g1", "Group One (1)", ""), ("g2", "g2 (1)", "")]
        assert calls[1][0] == "Select a template (Group One):"
        assert calls[1][2] == [("a", "Pretty A", "a desc")]

    def test_single_group_skips_group_step(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g1")])
        calls = patch_selector(monkeypatch, touch_module, ["b"])

        selected = touch_module._select_item(items, {})

        assert selected is items[1]
        assert len(calls) == 1
        assert calls[0][1] == ["a", "b"]

    def test_cancelling_group_step_returns_none(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g2")])
        patch_selector(monkeypatch, touch_module, [None])

        assert touch_module._select_item(items, {}) is None

    def test_cancelling_template_step_returns_none(self, touch_module, monkeypatch):
        items = self._items(touch_module, [("a", "g1"), ("b", "g2")])
        patch_selector(monkeypatch, touch_module, ["g1", None])

        assert touch_module._select_item(items, {}) is None


class TestWizard:
    """Tests for the interactive ``touch wizard`` subcommand.

    Selection (group, template, casing) is arrow-key driven via the
    shared ``select`` adapter and text questions (output path, template
    variables) go through ``text``, so both are monkeypatched here. Only
    the final write confirmation still reads CliRunner's ``input``.
    """

    def _run(self, module, wizard_input, command="wizard"):
        from click.testing import CliRunner

        runner = CliRunner()
        return runner.invoke(module.cli, [command], input=wizard_input)

    def test_creates_file_after_group_and_template_selection(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        calls = patch_selector(
            monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"]
        )
        patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        created = tmp_path / "note.a.txt"
        assert created.exists(), result.output
        assert created.read_text().startswith("ALPHA:note")
        assert calls[0][1] == ["g1", "g2"]
        assert calls[1][1] == ["alpha"]
        assert calls[2][1] == ["keep", "camel", "snake", "kebab", "pascal"]

    def test_cancelling_selection_exits_cleanly(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        patch_selector(monkeypatch, touch_module_with_config, [None])
        patch_text(monkeypatch, touch_module_with_config, [])

        result = self._run(touch_module_with_config, "")

        assert result.exit_code == 0, result.output
        assert "No template selected" in result.output
        assert not list(tmp_path.glob("*.txt"))

    def test_cancelling_casing_selection_exits_cleanly(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", None])
        patch_text(monkeypatch, touch_module_with_config, [str(out)])

        result = self._run(touch_module_with_config, "")

        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output
        assert not (tmp_path / "note.a.txt").exists()

    def test_argument_answer_overrides_derived_value(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        patch_text(monkeypatch, touch_module_with_config, [str(out), "Custom"])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        assert (tmp_path / "note.a.txt").read_text().startswith("ALPHA:Custom")

    def test_shows_preview_before_writing(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        assert "Preview of" in result.output
        assert "ALPHA:note" in result.output

    def test_declining_confirmation_writes_nothing(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "n\n")

        assert result.exit_code != 0
        assert not (tmp_path / "note.a.txt").exists()

    def test_empty_output_path_reprompts(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        patch_text(monkeypatch, touch_module_with_config, ["", "  ", str(out), ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        assert (tmp_path / "note.a.txt").exists()

    def test_warns_when_no_templates_configured(self, touch_module, monkeypatch):
        patch_selector(monkeypatch, touch_module, [])
        patch_text(monkeypatch, touch_module, [])

        result = self._run(touch_module, "")

        assert result.exit_code == 0, result.output
        assert "No touch templates configured" in result.output

    def test_w_alias_is_registered(self, touch_module_with_config, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "\n", command="w")

        assert result.exit_code == 0, result.output
        assert (tmp_path / "note.a.txt").exists()

    def test_group_picker_shows_configured_descriptions(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        calls = patch_selector(
            monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"]
        )
        patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        assert calls[0][2] == [
            ("g1", "Group One (1)", "First group"),
            ("g2", "g2 (2)", "Second group"),
        ]

    def test_output_placeholder_uses_item_example(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "note"
        patch_selector(monkeypatch, touch_module_with_config, ["g1", "alpha", "keep"])
        text_calls = patch_text(monkeypatch, touch_module_with_config, [str(out), ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        assert ("Output path:", "e.g. notes/my-note") in text_calls

    def test_argument_placeholders_show_default_and_example(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "release"
        patch_selector(monkeypatch, touch_module_with_config, ["g2", "gamma", "keep"])
        text_calls = patch_text(monkeypatch, touch_module_with_config, [str(out), "", ""])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        # No item example -> generic extension-based output placeholder.
        assert ("Output path:", "e.g. my-file.c.txt") in text_calls
        assert ("greeting:", "default: hello") in text_calls
        assert ("tag:", "e.g. v1.0") in text_calls

    def test_blank_argument_answer_takes_configured_default(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "release"
        patch_selector(monkeypatch, touch_module_with_config, ["g2", "gamma", "keep"])
        patch_text(monkeypatch, touch_module_with_config, [str(out), "", "v2.0"])

        result = self._run(touch_module_with_config, "\n")

        assert result.exit_code == 0, result.output
        content = (tmp_path / "release.c.txt").read_text()
        assert content.startswith("GAMMA:hello:v2.0")

    def test_builtin_function_vars_are_not_prompted(self, touch_module, monkeypatch):
        item = touch_module.TouchItem(
            command="x",
            description="uses builtins",
            template_string="{{ convert_case(file_stem, 'pascal') }}:{{ env('USER') }}",
        )
        text_calls = patch_text(monkeypatch, touch_module, ["Widget"])

        args = touch_module._prompt_arguments(item)

        assert [message for message, _ in text_calls] == ["file_stem:"]
        assert args == {"file_stem": "Widget"}


class TestHighlightPreview:
    """Optional pygments highlighting for the wizard preview."""

    def test_highlights_when_lexer_matches_filename(self, touch_module):
        out = touch_module._highlight_preview("key: value\n", "deploy.yaml")
        assert "\x1b[" in out
        assert "key" in out

    def test_plain_when_no_lexer_for_filename(self, touch_module):
        code = "some content\n"
        assert touch_module._highlight_preview(code, "file.no-such-ext") == code

    def test_plain_when_pygments_unavailable(self, touch_module, monkeypatch):
        monkeypatch.setattr(touch_module, "_pygments_available", lambda: False)
        code = "key: value\n"
        assert touch_module._highlight_preview(code, "deploy.yaml") == code


class TestArgumentSpec:
    """Argument metadata: string shorthand, rich form, and CLI defaults."""

    def test_string_shorthand_becomes_help(self, touch_module):
        item = touch_module.TouchItem(
            command="x",
            description="d",
            template_string="{{ tag }}",
            arguments={"tag": "Tag name"},
        )
        assert item.arguments["tag"].help == "Tag name"
        assert item.arguments["tag"].default == ""

    def test_discovered_vars_get_default_spec(self, touch_module):
        item = touch_module.TouchItem(
            command="x", description="d", template_string="{{ tag }}"
        )
        assert item.arguments["tag"].help == "<value>"

    def test_cli_uses_configured_default(
        self, touch_module_with_config, tmp_path, monkeypatch
    ):
        from click.testing import CliRunner

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            touch_module_with_config.cli, ["gamma", str(tmp_path / "rel")]
        )

        assert result.exit_code == 0, result.output
        assert (tmp_path / "rel.c.txt").read_text().startswith("GAMMA:hello:")

    def test_cli_help_shows_argument_help_text(self, touch_module_with_config):
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(touch_module_with_config.cli, ["gamma", "--help"])

        assert result.exit_code == 0
        assert "Tag name" in result.output
        assert "Greeting word" in result.output


def make_fake_file_editor(monkeypatch, module, append=None, replace_with=None):
    """Monkeypatch ``click.edit`` to simulate editing the seeded file in place.

    Real ``click.edit(filename=...)`` edits that file in place and always
    returns ``None`` (see ``touch._author_template_body``'s docstring), so
    tests drive it by mutating the file the wizard already created and
    seeded, exactly like a real editor session would, rather than relying
    on a return value. ``append`` writes text after the existing (seeded)
    content; ``replace_with`` overwrites it entirely (e.g. to simulate the
    author clearing the file, or leaving only comment text). Passing
    neither simulates a pure no-op edit (file left exactly as seeded).
    Returns a list that the fake's calls append their ``filename`` to, so
    tests can assert on the path the wizard opened.
    """
    captured_filenames: list[str] = []

    def fake_edit(filename=None, editor=None, **kwargs):
        captured_filenames.append(filename)
        if replace_with is not None:
            pathlib.Path(filename).write_text(replace_with)
        elif append is not None:
            with open(filename, "a") as f:
                f.write(append)
        return None

    monkeypatch.setattr(module.click, "edit", fake_edit)
    return captured_filenames


class TestNewCommand:
    """Tests for the interactive ``touch new`` template-authoring wizard.

    Follows the same headless-driving pattern as ``TestWizard``: ``select``
    and ``text`` are monkeypatched to pop canned answers. ``click.edit``
    (the multi-line template-body editor) is monkeypatched via
    :func:`make_fake_file_editor`, which edits the real seeded temp file in
    place rather than returning text - matching how ``click.edit(filename=...)``
    actually behaves (its text-returning mode only applies without
    ``filename``, so the return value here is always ``None``).
    """

    def _run(self, module, tmp_cwd):
        from click.testing import CliRunner

        runner = CliRunner()
        return runner.invoke(module.cli, ["new"])

    def test_happy_path_appends_and_is_immediately_selectable(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        select_calls = patch_selector(monkeypatch, module, ["g2"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["rfc", "RFC Doc", "An RFC template", "md"],
        )
        make_fake_file_editor(monkeypatch, module, append="Hello {{ file_stem }}\n")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert "Added new template 'rfc'" in result.output

        # Existing groups plus the "new group" sentinel are offered.
        assert select_calls[0][1] == ["g1", "g2", module._NEW_GROUP]

        values = module.config.typed.values
        commands = [item.command for item in values]
        assert commands == ["alpha", "beta", "gamma", "rfc"]

        new_item = values[-1]
        assert new_item.group == "g2"
        assert new_item.name == "RFC Doc"
        assert new_item.description == "An RFC template"
        assert new_item.file_name_options.extension == ".md"
        # The seeded comment stays in the saved template (harmless - Jinja
        # ignores it at render time) alongside the real, authored body.
        assert "Hello {{ file_stem }}" in new_item.template_string
        assert new_item.template_string.startswith("{#")
        # Undeclared Jinja2 vars were auto-discovered, not hand-registered.
        assert "file_stem" in new_item.arguments

        # Immediately selectable from a subsequent wizard invocation.
        patch_selector(monkeypatch, module, ["g2", "rfc"])
        selected = module._select_item(values, module.config.typed.groups_meta)
        assert selected is new_item

    def test_editor_opens_file_named_after_command(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        """The edited file's basename comes from the command, not an anonymous temp name."""
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["rfc", "RFC Doc", "desc", "md"],
        )
        captured = make_fake_file_editor(monkeypatch, module, append="body\n")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert len(captured) == 1
        assert os.path.basename(captured[0]) == "rfc.jinja"

    def test_editor_seed_mentions_derived_vars_and_builtins(
        self, touch_module, monkeypatch
    ):
        """The seed comment teaches Jinja2 basics without hand-authoring anything."""
        seed = touch_module._template_seed("rfc")
        assert seed.startswith("{#")
        assert seed.rstrip().endswith("#}")
        assert "{{ file_stem }}" in seed
        assert "convert_case" in seed
        assert "env" in seed
        # Comments are stripped before undeclared-variable discovery, so the
        # illustrative vars in the seed must not register as real template
        # arguments.
        item = touch_module.TouchItem(
            command="x", description="d", template_string=seed
        )
        assert item.arguments == {}

    def test_new_group_falls_through_to_text_prompt(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        patch_selector(monkeypatch, module, [module._NEW_GROUP])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["newcmd", "docs-extra", "New Cmd", "A new command", "txt"],
        )
        make_fake_file_editor(monkeypatch, module, append="body\n")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        new_item = module.config.typed.values[-1]
        assert new_item.command == "newcmd"
        assert new_item.group == "docs-extra"

    def test_extension_without_leading_dot_is_normalized(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["ext-test", "Ext Test", "desc", "yaml"],
        )
        make_fake_file_editor(monkeypatch, module, append="body\n")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        new_item = module.config.typed.values[-1]
        assert new_item.file_name_options.extension == ".yaml"

    def test_command_collision_rejected_before_editor_opens(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        before = list(module.config.typed.values)

        # Neither the group selector nor the editor should ever be reached.
        patch_selector(monkeypatch, module, [])
        patch_text(module=module, monkeypatch=monkeypatch, answers=["alpha"])

        def unexpected_edit(**kwargs):
            raise AssertionError("click.edit should not be invoked on a collision")

        monkeypatch.setattr(module.click, "edit", unexpected_edit)

        result = self._run(module, tmp_cwd)

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert [item.command for item in module.config.typed.values] == [
            item.command for item in before
        ]

    def test_cancelled_group_selection_writes_nothing(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        patch_selector(monkeypatch, module, [None])
        patch_text(module=module, monkeypatch=monkeypatch, answers=["freshcmd"])

        def unexpected_edit(**kwargs):
            raise AssertionError("click.edit should not be invoked when cancelled")

        monkeypatch.setattr(module.click, "edit", unexpected_edit)

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output
        assert [item.command for item in module.config.typed.values] == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_unchanged_editor_file_aborts_without_mutating_config(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        """A no-op edit (file left exactly as seeded) counts as cancelled.

        ``click.edit(filename=...)`` always returns ``None`` regardless of
        whether the file changed, so cancellation must be detected by
        inspecting the file's content rather than the return value.
        """
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["freshcmd", "Fresh", "desc", "txt"],
        )
        make_fake_file_editor(monkeypatch, module)  # no append/replace: pure no-op

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output
        assert [item.command for item in module.config.typed.values] == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_blank_editor_file_aborts_without_mutating_config(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["freshcmd", "Fresh", "desc", "txt"],
        )
        make_fake_file_editor(monkeypatch, module, replace_with="   \n\t  ")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output
        assert [item.command for item in module.config.typed.values] == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_comment_only_edit_aborts_without_mutating_config(
        self, touch_module_with_config, tmp_cwd, monkeypatch
    ):
        """Editing only the seeded comment (no real body) still cancels.

        Distinct from the unchanged-file case: the content differs from
        the original seed, but stripping Jinja `{# #}` comments still
        leaves nothing behind, so it must be treated as cancelled too.
        """
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["freshcmd", "Fresh", "desc", "txt"],
        )
        make_fake_file_editor(
            monkeypatch, module, replace_with="{# just a tweaked comment, no body #}"
        )

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        assert "Cancelled" in result.output
        assert [item.command for item in module.config.typed.values] == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_new_config_written_to_disk(
        self, touch_module_with_config, tmp_cwd, monkeypatch, tmp_path
    ):
        """The appended entry is persisted to touch.yaml, not just in-memory."""
        module = touch_module_with_config
        patch_selector(monkeypatch, module, ["g1"])
        patch_text(
            module=module,
            monkeypatch=monkeypatch,
            answers=["ondisk", "On Disk", "desc", "txt"],
        )
        make_fake_file_editor(monkeypatch, module, append="content\n")

        result = self._run(module, tmp_cwd)

        assert result.exit_code == 0, result.output
        on_disk = (tmp_path / ".ptools" / "touch.yaml").read_text()
        assert "ondisk" in on_disk
        # The live Jinja2 Template object must never leak into the YAML.
        assert "!!python" not in on_disk
