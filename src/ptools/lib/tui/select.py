"""Vite-style interactive prompt primitives built on prompt_toolkit.

- :class:`SelectApp` - inline arrow-key single-select with a ``❯``
  pointer and colored highlight (enter confirms, escape cancels).
- :func:`ask_text` - single-line text prompt with a dim placeholder
  example.

Extracted from :mod:`ptools.literals` so other commands (e.g. the touch
wizard) can reuse the same flows.
"""

from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit import prompt as _pt_prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

__version__ = "0.2.0"

STYLE = Style.from_dict(
    {
        "qmark": "fg:ansigreen bold",
        "question": "bold",
        "hint": "fg:ansibrightblack",
        "pointer": "fg:ansicyan bold",
        # Not named "selected": that class exists in prompt_toolkit's
        # default UI style as "reverse" and would merge into ours.
        "highlight": "fg:ansicyan",
        "answer": "fg:ansicyan",
        "check": "fg:ansigreen bold",
        "cancel": "fg:ansired",
        "placeholder": "fg:ansibrightblack italic",
    }
)


class SelectApp:
    """Inline arrow-key single-select list.

    Renders a ``? message`` header with a dim key hint, a ``❯`` pointer on
    the highlighted row, and collapses to ``✔ message answer`` once a
    value is confirmed. ``items`` is a list of ``(value, label)`` or
    ``(value, label, description)`` tuples; descriptions render dim after
    the label. :meth:`run` returns the selected value, or a falsy value
    when the user cancels.

    Lists longer than ``max_visible`` scroll with the pointer and show
    dim ``↑/↓ N more`` indicators (page up/down jump a whole window).

    ``selected_text`` optionally overrides the confirmation line
    (``"{}"``-formatted with the selected value). ``input``/``output``
    are optional prompt_toolkit objects, mainly for headless testing
    with ``create_pipe_input``/``DummyOutput``.
    """

    def __init__(
        self,
        items,
        message="",
        selected_text=None,
        select_handler=None,
        selected=None,
        max_visible=12,
        input=None,
        output=None,
    ):
        self.items = [self._normalize(item) for item in items]
        values = [value for value, _label, _desc in self.items]
        self.index = values.index(selected) if selected in values else 0
        self.max_visible = max(1, max_visible)
        self.offset = 0
        self._follow_pointer()
        self.message = message
        self.selected_text = selected_text
        self.select_handler = select_handler
        self.selected = []

        kb = KeyBindings()
        kb.add("up")(self._move(-1))
        kb.add("down")(self._move(1))
        kb.add("pageup")(self._page(-1))
        kb.add("pagedown")(self._page(1))
        kb.add("enter")(self._accept)
        kb.add("escape")(self._cancel)
        kb.add("c-c")(self._cancel)

        self.app = Application(
            layout=Layout(
                Window(FormattedTextControl(self._fragments), always_hide_cursor=True)
            ),
            key_bindings=kb,
            style=STYLE,
            input=input,
            output=output,
        )

    @staticmethod
    def _normalize(item):
        value, label, *rest = item
        return (value, label, rest[0] if rest else "")

    def _follow_pointer(self):
        """Keep the highlighted row inside the visible window."""
        if self.index < self.offset:
            self.offset = self.index
        elif self.index >= self.offset + self.max_visible:
            self.offset = self.index - self.max_visible + 1

    def _move(self, delta):
        def handler(event):
            self.index = (self.index + delta) % len(self.items)
            self._follow_pointer()

        return handler

    def _page(self, direction):
        def handler(event):
            self.index = max(
                0,
                min(len(self.items) - 1, self.index + direction * self.max_visible),
            )
            self._follow_pointer()

        return handler

    def _fragments(self):
        frags = []
        if self.message:
            frags += [
                ("class:qmark", "? "),
                ("class:question", self.message),
                ("class:hint", "  (↑/↓ move, enter confirm, esc cancel)"),
                ("", "\n"),
            ]
        end = min(self.offset + self.max_visible, len(self.items))
        if self.offset > 0:
            frags.append(("class:hint", f"  ↑ {self.offset} more\n"))
        for i in range(self.offset, end):
            _value, label, description = self.items[i]
            if i == self.index:
                frags += [("class:pointer", "❯ "), ("class:highlight", label)]
            else:
                frags += [("", f"  {label}")]
            if description:
                frags.append(("class:hint", f"  {description}"))
            frags.append(("", "\n"))
        remaining = len(self.items) - end
        if remaining > 0:
            frags.append(("class:hint", f"  ↓ {remaining} more\n"))
        return frags

    def _final_fragments(self):
        if not self.selected:
            prefix = f"{self.message} " if self.message else ""
            return [("class:cancel", "✖ "), ("class:hint", f"{prefix}(cancelled)")]
        if self.selected_text is not None:
            return [("", self.selected_text.format(self.selected))]
        frags = [("class:check", "✔ ")]
        if self.message:
            frags.append(("class:question", f"{self.message} "))
        frags.append(("class:answer", str(self.selected)))
        return frags

    def _accept(self, event):
        self.selected = self.items[self.index][0]
        if self.select_handler:
            self.select_handler(self.selected)
        self._finish()

    def _cancel(self, event):
        self.selected = []
        self._finish()

    def _finish(self):
        self.app.layout = Layout(
            Window(
                FormattedTextControl(self._final_fragments()), always_hide_cursor=True
            )
        )
        self.app.invalidate()
        self.app.exit()

    def run(self):
        self.app.run()
        return self.selected


def ask_text(message: str, placeholder: str = "", default: str = "") -> str:
    """Single-line text prompt with a dim placeholder example."""
    return _pt_prompt(
        [("class:qmark", "? "), ("class:question", f"{message} ")],
        default=default,
        placeholder=[("class:placeholder", placeholder)] if placeholder else None,
        style=STYLE,
    )
