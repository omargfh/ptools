"""Reusable Textual screens shared by ptools TUI apps.

Originally extracted from :mod:`ptools.lib.fs.file_tree_app` so that
other apps (e.g. the process explorer) can reuse the same message /
confirm / prompt flows.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

__version__ = "0.1.0"


class MessageScreen(Screen):
    """Show a message and dismiss on any key press."""

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Header(name="Message")
        yield Input(value=self.message, id="message-input", disabled=True)
        yield Input("Press any key to continue...", id="prompt-input", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#message-input", Input).focus()

    def on_key(self, event) -> None:
        event.stop()
        self.app.pop_screen()


class ConfirmScreen(Screen):
    """Ask the user to confirm an action with 'y'; any other key cancels.

    After the screen is dismissed the host app's ``action_refresh`` is
    invoked when it defines one (both the file tree and process apps
    want a rescan after a mutating action).
    """

    def __init__(
        self,
        message: str,
        on_confirm: Callable[[], None],
        refresh_after: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.message = message
        self.on_confirm = on_confirm
        self.refresh_after = refresh_after

    def compose(self) -> ComposeResult:
        yield Header(name="Confirm")
        yield Input(value=self.message, id="confirm-input", disabled=True)
        yield Input("Press 'y' to confirm, any other key to cancel.", id="prompt-input", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#confirm-input", Input).focus()

    def on_key(self, event) -> None:
        event.stop()
        app = self.app
        try:
            if event.key.lower() == "y":
                self.on_confirm()
            app.pop_screen()
            if self.refresh_after and hasattr(app, "action_refresh"):
                app.action_refresh()  # type: ignore[attr-defined]
        except Exception as e:
            app.pop_screen()
            app.bell()
            app.push_screen(MessageScreen(f"Error executing command: {e}"))


class InputScreen(Screen):
    """Prompt for a single line of input; enter submits, escape cancels."""

    def __init__(
        self,
        message: str,
        on_submit: Callable[[str], None],
        placeholder: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.message = message
        self.on_submit = on_submit
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Header(name="Input")
        yield Input(value=self.message, id="message-input", disabled=True)
        yield Input(placeholder=self.placeholder or "Type a value and press enter...", id="value-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#value-input", Input).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        app = self.app
        value = event.value
        app.pop_screen()
        try:
            self.on_submit(value)
        except Exception as e:
            app.bell()
            app.push_screen(MessageScreen(f"Error: {e}"))


class TextScreen(Screen):
    """Scrollable read-only content (detail views, help, profiler output).

    ``content`` may be a plain string or any Rich renderable (e.g. a
    :class:`rich.table.Table` / :class:`rich.console.Group`).
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    def __init__(self, title: str, content, markup: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.content = content
        self.markup = markup

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            if isinstance(self.content, str):
                yield Static(self.content, id="text-body", markup=self.markup)
            else:
                yield Static(self.content, id="text-body")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.title_text

    def action_close(self) -> None:
        self.app.pop_screen()
