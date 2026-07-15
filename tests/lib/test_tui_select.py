"""Headless tests for the SelectApp arrow-key picker.

Drives the prompt_toolkit application with pipe input and a dummy
output, so no terminal is required.
"""

from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from ptools.lib.tui.select import SelectApp

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
