"""Headless tests for ProcApp's Textual filter wizard (the 'f' key).

Drives ``ProcApp`` (and the ``FilterWizardScreen`` it pushes) the way
Textual apps are conventionally tested: ``app.run_test()`` as an async
context manager, driving input with ``pilot.press(...)``. Nothing here
touches a real terminal, prompt_toolkit, or an external editor -- the
one genuinely interactive bit (``$EDITOR``) is a standalone function
(``ptools.lib.proc.app._edit_expression``) that's monkeypatched out,
mirroring how ``tests/lib/test_proc_filter_wizard.py`` monkeypatches
``ptools.proc._select``/``_text`` for the CLI wizard.
"""

from contextlib import contextmanager

import pytest
from textual.widgets import Input, OptionList

import ptools.lib.proc.app as app_mod
from ptools.lib.proc import model
from ptools.lib.proc.app import FilterWizardScreen, ProcApp
from ptools.lib.proc.filter_wizard import operators_for_kind

ROWS = [
    {
        "pid": 100, "ppid": 1, "name": "Google Chrome", "user": "omar",
        "cpu": 55.0, "mem": 2 * 1024**3, "mem_pct": 6.3, "status": "running", "age": 7200.0,
    },
    {
        "pid": 200, "ppid": 150, "name": "node", "user": "omar",
        "cpu": 4.2, "mem": 300 * 1024**2, "mem_pct": 0.9, "status": "sleeping", "age": 90.0,
    },
]

SYSTEM_SNAPSHOT = {
    "cpu": 10.0, "ncpu": 8, "mem_pct": 40.0, "mem_used": 4 * 1024**3,
    "mem_total": 16 * 1024**3, "load": (1.0, 1.5, 2.0), "nproc": 2,
}


def _patch_sources(monkeypatch, rows=ROWS):
    """Stub sources.scan/system_snapshot so tests never touch the real process table."""
    monkeypatch.setattr(app_mod.sources, "scan", lambda joins=None: [dict(r) for r in rows])
    monkeypatch.setattr(app_mod.sources, "system_snapshot", lambda: dict(SYSTEM_SNAPSHOT))


def _select_option(option_list: OptionList, option_id: str) -> None:
    """Move an OptionList's highlight onto the option with id *option_id*.

    (Enter then selects whatever is currently highlighted.)
    """
    index = next(
        i for i in range(option_list.option_count)
        if option_list.get_option_at_index(i).id == option_id
    )
    option_list.highlighted = index


@pytest.mark.anyio
class TestFilterWizardKeybinding:
    async def test_f_key_pushes_filter_wizard_screen(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            assert isinstance(app.screen, FilterWizardScreen)

    def test_f_key_is_not_already_taken_by_another_binding(self):
        """Regression guard: 'f' must map only to the filter wizard.

        (The bindings audited in the PR: q s o t space r i k K ctrl+k z n
        y O P w : ? 1-9 -- 'f' was free.)
        """
        keys = [b.key for b in ProcApp.BINDINGS]
        assert keys.count("f") == 1
        matching = [b for b in ProcApp.BINDINGS if b.key == "f"]
        assert matching[0].action == "show_filter_wizard"


@pytest.mark.anyio
class TestFilterWizardScreenLayout:
    async def test_three_panels_are_simultaneously_present(self, monkeypatch):
        """Field/operator/value panels must all exist at once, not replace each other."""
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            # All three widgets are mounted together from the very first frame.
            assert screen.query_one("#field-list", OptionList) is not None
            assert screen.query_one("#operator-list", OptionList) is not None
            assert screen.query_one("#value-input", Input) is not None

    async def test_field_list_lists_every_model_field_with_title_and_help(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            field_list = app.screen.query_one("#field-list", OptionList)
            assert field_list.option_count == len(model.FIELDS)
            cpu_option = field_list.get_option_at_index(
                next(i for i in range(field_list.option_count)
                     if field_list.get_option_at_index(i).id == "cpu")
            )
            # CPU% has no help text -> label is just the title.
            assert str(cpu_option.prompt) == "CPU%"
            ports_option = field_list.get_option_at_index(
                next(i for i in range(field_list.option_count)
                     if field_list.get_option_at_index(i).id == "ports")
            )
            assert "Listening TCP/UDP ports" in str(ports_option.prompt)


@pytest.mark.anyio
class TestFilterWizardBuildsClauses:
    async def test_operator_list_depends_on_selected_field_kind(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            field_list = screen.query_one("#field-list", OptionList)

            _select_option(field_list, "name")  # STR kind
            await pilot.press("enter")
            await pilot.pause()

            op_list = screen.query_one("#operator-list", OptionList)
            op_ids = [op_list.get_option_at_index(i).id for i in range(op_list.option_count)]
            assert op_ids == operators_for_kind(model.STR)
            assert ">" not in op_ids and "<" not in op_ids

    async def test_building_and_committing_one_clause(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen

            field_list = screen.query_one("#field-list", OptionList)
            _select_option(field_list, "cpu")
            await pilot.press("enter")
            await pilot.pause()

            op_list = screen.query_one("#operator-list", OptionList)
            assert op_list.option_count == 6  # numeric kind: = != > >= < <=
            _select_option(op_list, ">")
            await pilot.press("enter")
            await pilot.pause()

            value_input = screen.query_one("#value-input", Input)
            assert value_input.has_focus
            await pilot.press(*"50")
            await pilot.press("enter")
            await pilot.pause()

            assert screen._clauses == ["cpu>50"]
            # Focus returns to the field list so another clause can be built
            # in the same three panels (not a fresh screen).
            assert screen.query_one("#field-list", OptionList).has_focus

    async def test_toggle_combinator_switches_and_or(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            assert screen._pending_combinator == "&"
            await pilot.press("o")
            await pilot.pause()
            assert screen._pending_combinator == "|"
            await pilot.press("o")
            await pilot.pause()
            assert screen._pending_combinator == "&"

    async def test_multi_clause_chain_uses_toggled_combinator(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            field_list = screen.query_one("#field-list", OptionList)
            op_list = screen.query_one("#operator-list", OptionList)

            _select_option(field_list, "cpu")
            await pilot.press("enter")
            await pilot.pause()
            _select_option(op_list, ">")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(*"50")
            await pilot.press("enter")
            await pilot.pause()

            await pilot.press("o")  # switch the next join to OR
            await pilot.pause()

            _select_option(field_list, "status")
            await pilot.press("enter")
            await pilot.pause()
            _select_option(op_list, "=")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(*"zombie")
            await pilot.press("enter")
            await pilot.pause()

            assert screen._clauses == ["cpu>50", "status=zombie"]
            assert screen._combinators == ["|"]

    async def test_committing_without_a_field_or_value_bells_without_crashing(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            screen.query_one("#value-input", Input).focus()
            await pilot.pause()
            await pilot.press("enter")  # nothing picked yet
            await pilot.pause()
            assert screen._clauses == []


@pytest.mark.anyio
class TestFilterWizardFinishAndCancel:
    async def test_finish_opens_editor_and_applies_via_set_where(self, monkeypatch):
        """The assembled expression reaches ProcApp._set_where, the same
        path the plain filter-bar Input uses -- no parallel filter path.
        """
        _patch_sources(monkeypatch)
        captured = {}

        def fake_edit_expression(app, expression):
            captured["expression"] = expression
            return expression

        monkeypatch.setattr(app_mod, "_edit_expression", fake_edit_expression)

        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            field_list = screen.query_one("#field-list", OptionList)
            _select_option(field_list, "cpu")
            await pilot.press("enter")
            await pilot.pause()
            op_list = screen.query_one("#operator-list", OptionList)
            _select_option(op_list, ">")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(*"50")
            await pilot.press("enter")
            await pilot.pause()

            await pilot.press("f2")
            await pilot.pause()

            assert captured["expression"] == "(cpu>50)"
            assert app.where_text == "(cpu>50)"
            assert not isinstance(app.screen, FilterWizardScreen)
            filter_bar = app.query_one("#filter-bar", Input)
            assert filter_bar.value == "(cpu>50)"
            assert filter_bar.has_class("visible")

    async def test_editor_modified_expression_is_what_actually_applies(self, monkeypatch):
        """Whatever the (stubbed) editor returns is applied, not the pre-edit build."""
        _patch_sources(monkeypatch)
        monkeypatch.setattr(app_mod, "_edit_expression", lambda app, expr: "cpu>1")

        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            field_list = screen.query_one("#field-list", OptionList)
            _select_option(field_list, "cpu")
            await pilot.press("enter")
            await pilot.pause()
            op_list = screen.query_one("#operator-list", OptionList)
            _select_option(op_list, ">")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(*"999")  # would match nothing on its own
            await pilot.press("enter")
            await pilot.pause()

            await pilot.press("f2")
            await pilot.pause()

            assert app.where_text == "cpu>1"

    async def test_finish_with_no_clauses_bells_and_stays_open(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, FilterWizardScreen)

    async def test_escape_cancels_without_changing_where(self, monkeypatch):
        _patch_sources(monkeypatch)
        app = ProcApp()
        async with app.run_test() as pilot:
            await pilot.press("f")
            await pilot.pause()
            screen = app.screen
            field_list = screen.query_one("#field-list", OptionList)
            _select_option(field_list, "cpu")
            await pilot.press("enter")
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen, FilterWizardScreen)
            assert app.where_text == ""


class TestEditExpressionHelper:
    """Unit tests for the standalone ``_edit_expression`` used by action_finish_wizard."""

    def test_suspends_the_app_and_calls_click_edit_with_the_editor_setting(self, monkeypatch):
        import click

        calls = {}

        class FakeApp:
            @contextmanager
            def suspend(self):
                calls["suspended"] = True
                yield

        def fake_click_edit(text, editor):
            calls["text"] = text
            calls["editor"] = editor
            return "cpu>1"

        monkeypatch.setattr(click, "edit", fake_click_edit)
        result = app_mod._edit_expression(FakeApp(), "(cpu>50)")

        assert result == "cpu>1"
        assert calls == {"suspended": True, "text": "(cpu>50)", "editor": app_mod.EDITOR}

    def test_falls_back_to_original_when_editor_makes_no_change(self, monkeypatch):
        import click

        class FakeApp:
            @contextmanager
            def suspend(self):
                yield

        monkeypatch.setattr(click, "edit", lambda text, editor: None)
        assert app_mod._edit_expression(FakeApp(), "(cpu>50)") == "(cpu>50)"
