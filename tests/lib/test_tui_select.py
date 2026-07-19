"""Headless tests for the SelectApp arrow-key picker and its adapters.

Drives the prompt_toolkit application with pipe input and a dummy
output, so no terminal is required.
"""

from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.output.base import Output

from ptools.lib.tui.select import SelectApp, picker_output, select, text

ITEMS = [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")]


def run_with_keys(items, keys, **kwargs):
    with create_pipe_input() as pipe:
        pipe.send_text(keys)
        app = SelectApp(
            items, message="Pick one:", input=pipe, output=DummyOutput(), **kwargs
        )
        return app.run()


def test_enter_selects_first_item():
    assert run_with_keys(ITEMS, "\r") == "a"


def test_arrow_down_then_enter_selects_second_item():
    assert run_with_keys(ITEMS, "\x1b[B\r") == "b"


def test_arrow_up_wraps_to_last_item():
    assert run_with_keys(ITEMS, "\x1b[A\r") == "c"


def test_escape_cancels_with_falsy_result():
    assert not run_with_keys(ITEMS, "\x1b")


def test_ctrl_c_cancels_with_falsy_result():
    assert not run_with_keys(ITEMS, "\x03")


def test_select_handler_receives_value():
    received = []
    result = run_with_keys(ITEMS, "\x1b[B\x1b[B\r", select_handler=received.append)
    assert result == "c"
    assert received == ["c"]


def test_selected_preselects_value():
    assert run_with_keys(ITEMS, "\r", selected="b") == "b"


def test_three_tuple_items_carry_descriptions():
    items = [("a", "Alpha", "first letter"), ("b", "Beta", "second letter")]
    assert run_with_keys(items, "\x1b[B\r") == "b"


LONG = [(str(i), f"item {i}") for i in range(30)]


def test_long_list_scrolls_with_pointer():
    """Regression: lists longer than the window must stay navigable.

    The pre-scrolling rendering drew all rows flat, so on long lists
    (e.g. bare ``ptools lget``) the pointer walked off-screen.
    """
    assert run_with_keys(LONG, "\x1b[B" * 15 + "\r", max_visible=5) == "15"


def test_page_down_jumps_a_window():
    assert run_with_keys(LONG, "\x1b[6~\r", max_visible=5) == "5"


def test_fragments_window_and_indicators():
    with create_pipe_input() as pipe:
        app = SelectApp(LONG, max_visible=5, input=pipe, output=DummyOutput())

        text = "".join(t for _, t in app._fragments())
        assert "item 0" in text and "item 4" in text
        assert "item 5" not in text
        assert "↓ 25 more" in text and "↑" not in text

        for _ in range(7):
            app._move(1)(None)
        text = "".join(t for _, t in app._fragments())
        assert "❯ item 7" in text
        assert "↑ 3 more" in text and "↓ 22 more" in text


def test_preselected_value_scrolls_into_view():
    with create_pipe_input() as pipe:
        app = SelectApp(
            LONG, max_visible=5, selected="20", input=pipe, output=DummyOutput()
        )
        text = "".join(t for _, t in app._fragments())
        assert "❯ item 20" in text


class TestSelectAdapter:
    """``select()`` is the shared wrapper the four picker call sites use."""

    def test_returns_chosen_value(self):
        with create_pipe_input() as pipe:
            pipe.send_text("\x1b[B\r")
            result = select(ITEMS, "Pick one:", input=pipe, output=DummyOutput())
        assert result == "b"

    def test_cancel_returns_none(self):
        with create_pipe_input() as pipe:
            pipe.send_text("\x1b")
            result = select(ITEMS, "Pick one:", input=pipe, output=DummyOutput())
        assert result is None

    def test_selected_preselects_value(self):
        with create_pipe_input() as pipe:
            pipe.send_text("\r")
            result = select(
                ITEMS, "Pick one:", selected="c", input=pipe, output=DummyOutput()
            )
        assert result == "c"

    def test_max_visible_is_forwarded(self):
        """Regression: consolidating the adapter must not drop scrolling."""
        with create_pipe_input() as pipe:
            pipe.send_text("\x1b[B" * 15 + "\r")
            result = select(
                LONG, "Pick one:", max_visible=5, input=pipe, output=DummyOutput()
            )
        assert result == "15"

    def test_app_cls_hook_swaps_the_select_app_subclass(self):
        """``literals.LiteralsApp`` needs a different confirmation class,
        not just a different ``selected_text`` string."""

        class TaggedSelectApp(SelectApp):
            tagged = True

        seen = {}
        real_init = TaggedSelectApp.__init__

        def spy_init(self, *args, **kwargs):
            seen["used"] = True
            real_init(self, *args, **kwargs)

        TaggedSelectApp.__init__ = spy_init

        with create_pipe_input() as pipe:
            pipe.send_text("\r")
            result = select(
                ITEMS,
                "Pick one:",
                app_cls=TaggedSelectApp,
                input=pipe,
                output=DummyOutput(),
            )
        assert result == "a"
        assert seen.get("used") is True

    def test_default_app_cls_reads_select_app_dynamically(self, monkeypatch):
        """``app_cls`` isn't bound at import time: patching this module's
        ``SelectApp`` must still redirect every caller of ``select()``."""
        import ptools.lib.tui.select as select_module

        calls = []

        class FakeSelectApp:
            def __init__(self, items, message="", **kwargs):
                calls.append(message)

            def run(self):
                return "patched"

        monkeypatch.setattr(select_module, "SelectApp", FakeSelectApp)

        assert select(ITEMS, "Pick one:") == "patched"
        assert calls == ["Pick one:"]

    def test_three_tuple_options_are_accepted(self):
        items = [("a", "Alpha", "first letter"), ("b", "Beta", "second letter")]
        with create_pipe_input() as pipe:
            pipe.send_text("\x1b[B\r")
            result = select(items, "Pick one:", input=pipe, output=DummyOutput())
        assert result == "b"


class TestTextAdapter:
    """``text()`` is the shared wrapper over :func:`ask_text`."""

    def test_returns_typed_value(self):
        with create_pipe_input() as pipe:
            pipe.send_text("hello\r")
            result = text("Name:", input=pipe, output=DummyOutput())
        assert result == "hello"

    def test_default_is_used_when_nothing_is_typed(self):
        with create_pipe_input() as pipe:
            pipe.send_text("\r")
            result = text("Name:", default="fallback", input=pipe, output=DummyOutput())
        assert result == "fallback"

    def test_does_not_strip_or_none_the_result(self):
        """Folding ``.strip() or None`` in here would change behaviour for
        callers that don't want it (proc.py/touch.py/literals.py return
        the raw string today); config.py applies that at its call sites
        instead."""
        with create_pipe_input() as pipe:
            pipe.send_text("  \r")
            result = text("Name:", input=pipe, output=DummyOutput())
        assert result == "  "


def test_picker_output_returns_a_prompt_toolkit_output():
    output = picker_output()
    assert isinstance(output, Output)
