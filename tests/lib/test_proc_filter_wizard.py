"""Tests for the interactive filter-builder wizard (``ptools proc list --wizard``).

Mirrors how ``tests/test_touch.py`` headlessly drives ``touch wizard``:
``_select``/``_text`` (the same calling convention as ``touch._select``/
``touch._text``) are monkeypatched to pop canned answers instead of running
a real prompt_toolkit UI. The shell-agnostic operator/clause-building logic
(``operators_for_kind``, ``format_clause``, ``join_clauses``) lives in
``ptools.lib.proc.filter_wizard`` so it's shared with the Textual TUI's own
filter-wizard screen (see ``tests/lib/test_proc_app_filter_wizard.py``);
``ptools.proc`` re-imports those helpers by name, so ``proc.operators_for_kind``
and ``ptools.lib.proc.filter_wizard.operators_for_kind`` are the same function.
"""

import json

from click.testing import CliRunner

import ptools.proc as proc
from ptools.lib.proc import filter_wizard, model
from ptools.lib.proc.query import compile_query


def patch_selector(monkeypatch, answers):
    """Replace ``proc._select`` with a fake that pops canned *answers*.

    Returns the list of ``(title, option_values)`` calls for assertions.
    """
    remaining = list(answers)
    calls = []

    def fake(options, title, selected=None):
        calls.append((title, [option[0] for option in options]))
        assert remaining, f"unexpected selector call: {title!r}"
        return remaining.pop(0)

    monkeypatch.setattr(proc, "_select", fake)
    return calls


def patch_text(monkeypatch, answers):
    """Replace ``proc._text`` with a fake that pops canned *answers*.

    Returns the list of ``(message, placeholder)`` calls for assertions.
    """
    remaining = list(answers)
    calls = []

    def fake(message, placeholder=""):
        calls.append((message, placeholder))
        assert remaining, f"unexpected text prompt: {message!r}"
        return remaining.pop(0)

    monkeypatch.setattr(proc, "_text", fake)
    return calls


class TestOperatorsForKind:
    """Operator choices must be derived from Field.kind, not one static list.

    Exercised through ``ptools.lib.proc.filter_wizard`` directly (the
    shared module) as well as ``proc.operators_for_kind`` (the name
    ``ptools.proc`` imports it under), to guard against the CLI module
    quietly drifting from the shared implementation.
    """

    def test_string_kind_excludes_ordering_operators(self):
        ops = filter_wizard.operators_for_kind(model.STR)
        assert ops == ["=", "!=", "~", "!~"]
        assert ">" not in ops and "<" not in ops and ">=" not in ops and "<=" not in ops

    def test_str_list_kind_matches_str_kind(self):
        assert filter_wizard.operators_for_kind(model.STR_LIST) == filter_wizard.operators_for_kind(model.STR)

    def test_numeric_kinds_offer_ordering_but_not_regex_operators(self):
        for kind in (model.NUM, model.SIZE, model.DURATION, model.NUM_LIST):
            ops = filter_wizard.operators_for_kind(kind)
            assert ops == ["=", "!=", ">", ">=", "<", "<="]
            assert "~" not in ops and "!~" not in ops

    def test_every_offered_operator_is_accepted_by_compile_query(self):
        """Guards against the wizard's operator table drifting from query.py."""
        numeric_kinds = (model.NUM, model.SIZE, model.DURATION, model.NUM_LIST)
        for field in model.FIELDS:
            value = "50" if field.kind in numeric_kinds else "x"
            for op in filter_wizard.operators_for_kind(field.kind):
                compile_query(f"{field.key}{op}{value}")  # must not raise QueryError

    def test_proc_module_shares_the_same_operator_table(self):
        """``ptools.proc`` must reuse the shared table, not a local duplicate."""
        assert proc.operators_for_kind is filter_wizard.operators_for_kind


class TestSharedFilterWizardHelpers:
    """Direct coverage of the format/quote/join helpers both UIs share."""

    def test_format_clause_builds_field_key_op_value(self):
        field = model.FIELD_MAP["cpu"]
        assert filter_wizard.format_clause(field, ">", "50") == "cpu>50"

    def test_format_clause_quotes_values_with_spaces(self):
        field = model.FIELD_MAP["name"]
        assert filter_wizard.format_clause(field, "=", "Google Chrome") == 'name="Google Chrome"'

    def test_quote_value_leaves_plain_values_unquoted(self):
        assert filter_wizard.quote_value("node") == "node"

    def test_quote_value_prefers_single_quotes_when_value_has_a_double_quote(self):
        assert filter_wizard.quote_value('say "hi"') == '\'say "hi"\''

    def test_join_clauses_returns_none_for_no_clauses(self):
        assert filter_wizard.join_clauses([], []) is None

    def test_join_clauses_single_clause_is_just_parenthesized(self):
        assert filter_wizard.join_clauses(["cpu>50"], []) == "(cpu>50)"

    def test_join_clauses_ignores_extra_trailing_combinator(self):
        # More combinators than gaps between clauses (e.g. the user picked
        # a combinator then cancelled the next clause) must not leak in.
        assert filter_wizard.join_clauses(["cpu>50"], ["&"]) == "(cpu>50)"


class TestBuildWizardClause:
    def test_builds_simple_numeric_clause(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", ">"])
        patch_text(monkeypatch, ["50"])
        assert proc._build_wizard_clause() == "cpu>50"

    def test_quotes_values_containing_spaces(self, monkeypatch):
        patch_selector(monkeypatch, ["name", "="])
        patch_text(monkeypatch, ["Google Chrome"])
        clause = proc._build_wizard_clause()
        assert clause == 'name="Google Chrome"'
        compile_query(clause)  # must not raise

    def test_size_and_duration_kinds_accept_humanized_values(self, monkeypatch):
        patch_selector(monkeypatch, ["mem", ">"])
        patch_text(monkeypatch, ["500MB"])
        assert proc._build_wizard_clause() == "mem>500MB"

        patch_selector(monkeypatch, ["age", "<"])
        patch_text(monkeypatch, ["5m"])
        assert proc._build_wizard_clause() == "age<5m"

    def test_cancelling_field_pick_returns_none(self, monkeypatch):
        patch_selector(monkeypatch, [None])
        patch_text(monkeypatch, [])
        assert proc._build_wizard_clause() is None

    def test_cancelling_operator_pick_returns_none(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", None])
        patch_text(monkeypatch, [])
        assert proc._build_wizard_clause() is None

    def test_blank_value_returns_none(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", ">"])
        patch_text(monkeypatch, ["   "])
        assert proc._build_wizard_clause() is None

    def test_operator_choices_passed_to_selector_match_field_kind(self, monkeypatch):
        calls = patch_selector(monkeypatch, ["status", "="])
        patch_text(monkeypatch, ["zombie"])
        proc._build_wizard_clause()
        _field_call, op_call = calls
        assert op_call[0] == "Operator for St:"
        assert op_call[1] == ["=", "!=", "~", "!~"]


class TestRunFilterWizard:
    """Multi-clause chaining with &/| must produce a compile_query-ready string."""

    def test_single_clause_no_chaining(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", ">", "done"])
        patch_text(monkeypatch, ["50"])
        assert proc._run_filter_wizard() == "(cpu>50)"

    def test_and_chaining_produces_parseable_expression(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", ">", "&", "mem", ">", "done"])
        patch_text(monkeypatch, ["50", "500MB"])
        expr = proc._run_filter_wizard()
        assert expr == "(cpu>50) & (mem>500MB)"
        compile_query(expr)  # must not raise

    def test_or_chaining_produces_parseable_expression(self, monkeypatch):
        patch_selector(monkeypatch, ["status", "=", "|", "status", "=", "done"])
        patch_text(monkeypatch, ["zombie", "running"])
        expr = proc._run_filter_wizard()
        assert expr == "(status=zombie) | (status=running)"
        compile_query(expr)  # must not raise

    def test_three_clause_chain(self, monkeypatch):
        patch_selector(
            monkeypatch,
            ["cpu", ">", "&", "mem", ">", "|", "status", "=", "done"],
        )
        patch_text(monkeypatch, ["50", "500MB", "zombie"])
        expr = proc._run_filter_wizard()
        assert expr == "(cpu>50) & (mem>500MB) | (status=zombie)"
        compile_query(expr)  # must not raise

    def test_cancelling_before_any_clause_returns_none(self, monkeypatch):
        patch_selector(monkeypatch, [None])
        patch_text(monkeypatch, [])
        assert proc._run_filter_wizard() is None

    def test_cancelling_second_clause_keeps_completed_first_clause(self, monkeypatch):
        patch_selector(monkeypatch, ["cpu", ">", "&", None])
        patch_text(monkeypatch, ["50"])
        expr = proc._run_filter_wizard()
        assert expr == "(cpu>50)"
        compile_query(expr)  # dangling '&' must not leak into the expression


class TestEditWizardExpression:
    """The CLI wizard's last step: freeform-edit the assembled expression."""

    def test_returns_edited_text_when_editor_saves(self, monkeypatch):
        monkeypatch.setattr(proc.click, "edit", lambda text, editor: "cpu>90")
        assert proc._edit_wizard_expression("(cpu>50)") == "cpu>90"

    def test_falls_back_to_original_when_editor_makes_no_change(self, monkeypatch):
        # click.edit returns None when the file wasn't saved/modified.
        monkeypatch.setattr(proc.click, "edit", lambda text, editor: None)
        assert proc._edit_wizard_expression("(cpu>50)") == "(cpu>50)"

    def test_passes_expression_and_editor_setting_through(self, monkeypatch):
        calls = {}

        def fake_edit(text, editor):
            calls["text"] = text
            calls["editor"] = editor
            return None

        monkeypatch.setattr(proc.click, "edit", fake_edit)
        proc._edit_wizard_expression("(cpu>50)")
        assert calls == {"text": "(cpu>50)", "editor": proc.EDITOR}

    def test_strips_whitespace_from_edited_result(self, monkeypatch):
        monkeypatch.setattr(proc.click, "edit", lambda text, editor: "  cpu>90  \n")
        assert proc._edit_wizard_expression("(cpu>50)") == "cpu>90"


def _patch_sources(monkeypatch, rows):
    """Stub sources.prime/scan so tests never touch the real process table."""
    from ptools.lib.proc import sources

    monkeypatch.setattr(sources, "prime", lambda joins=None: None)
    monkeypatch.setattr(sources, "scan", lambda joins=None: [dict(r) for r in rows])


def bypass_editor(monkeypatch):
    """Skip the real $EDITOR launch for tests that don't care about editing.

    The editor step itself (``_edit_wizard_expression``) is covered
    separately in ``TestEditWizardExpression``.
    """
    monkeypatch.setattr(proc, "_edit_wizard_expression", lambda expr: expr)


def _strip_filter_line(output: str) -> str:
    lines = output.splitlines()
    if lines and lines[0].startswith("Filter:"):
        lines = lines[1:]
    return "\n".join(lines)


ROWS = [
    {
        "pid": 100, "ppid": 1, "name": "Google Chrome", "comm": "Google Chrome",
        "cmd": "", "user": "omar", "cpu": 55.0, "mem": 2 * 1024**3, "mem_pct": 6.3,
        "status": "running", "threads": 1, "nice": 0, "age": 7200.0, "started": "",
        "bundle": "Google Chrome", "kind": "app", "label": "",
    },
    {
        "pid": 200, "ppid": 150, "name": "node", "comm": "node",
        "cmd": "node vite.js", "user": "omar", "cpu": 4.2, "mem": 300 * 1024**2,
        "mem_pct": 0.9, "status": "sleeping", "threads": 1, "nice": 0, "age": 90.0,
        "started": "", "bundle": "", "kind": "", "label": "",
    },
]


class TestWizardReachesSameCodePathAsTypedWhere:
    """The wizard must feed compile_query/_scan_rows -- no parallel filter path."""

    def test_wizard_output_matches_equivalent_typed_where(self, monkeypatch):
        _patch_sources(monkeypatch, ROWS)
        bypass_editor(monkeypatch)
        runner = CliRunner()

        typed = runner.invoke(proc.cli, ["list", "--where", "cpu>50", "--flavor", "json"])
        assert typed.exit_code == 0, typed.output

        patch_selector(monkeypatch, ["cpu", ">", "done"])
        patch_text(monkeypatch, ["50"])
        wizard = runner.invoke(proc.cli, ["list", "--wizard", "--flavor", "json"])
        assert wizard.exit_code == 0, wizard.output

        typed_rows = json.loads(typed.output)
        wizard_rows = json.loads(_strip_filter_line(wizard.output))
        assert wizard_rows == typed_rows
        assert [r["name"] for r in wizard_rows] == ["Google Chrome"]

    def test_wizard_with_positional_query_combines_via_and(self, monkeypatch):
        """--wizard alongside a typed query combines both with '&', like --where does."""
        _patch_sources(monkeypatch, ROWS)
        bypass_editor(monkeypatch)
        runner = CliRunner()

        patch_selector(monkeypatch, ["status", "=", "done"])
        patch_text(monkeypatch, ["running"])
        result = runner.invoke(
            proc.cli, ["list", "cpu>1", "--wizard", "--flavor", "json"]
        )
        assert result.exit_code == 0, result.output
        rows = json.loads(_strip_filter_line(result.output))
        assert [r["name"] for r in rows] == ["Google Chrome"]

    def test_invalid_wizard_value_surfaces_query_error_cleanly(self, monkeypatch):
        """A bad value (e.g. non-numeric for a NUM field) must not crash the CLI."""
        _patch_sources(monkeypatch, ROWS)
        bypass_editor(monkeypatch)
        runner = CliRunner()

        patch_selector(monkeypatch, ["cpu", ">", "done"])
        patch_text(monkeypatch, ["not-a-number"])
        result = runner.invoke(proc.cli, ["list", "--wizard"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit) or result.exception is None
        assert "Invalid --where expression" in result.output

    def test_wizard_applies_editor_modified_expression(self, monkeypatch):
        """The *edited* expression is what actually gets compiled and applied.

        The wizard alone would build ``cpu>999`` (matches nothing); the
        stubbed editor rewrites it to ``cpu>1`` (matches both rows), and
        the CLI's filtered output must reflect the edited text.
        """
        _patch_sources(monkeypatch, ROWS)
        runner = CliRunner()

        patch_selector(monkeypatch, ["cpu", ">", "done"])
        patch_text(monkeypatch, ["999"])
        monkeypatch.setattr(proc.click, "edit", lambda text, editor: "cpu>1")

        result = runner.invoke(proc.cli, ["list", "--wizard", "--flavor", "json"])
        assert result.exit_code == 0, result.output
        assert "Filter: cpu>1" in result.output
        rows = json.loads(_strip_filter_line(result.output))
        assert {r["name"] for r in rows} == {"Google Chrome", "node"}

    def test_cancelled_wizard_matches_everything_like_no_filter(self, monkeypatch):
        _patch_sources(monkeypatch, ROWS)
        runner = CliRunner()

        patch_selector(monkeypatch, [None])
        patch_text(monkeypatch, [])
        result = runner.invoke(proc.cli, ["list", "--wizard", "--flavor", "json"])
        assert result.exit_code == 0, result.output
        rows = json.loads(result.output)
        assert {r["name"] for r in rows} == {"Google Chrome", "node"}
