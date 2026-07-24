"""Shared TUI building blocks for ptools apps.

- :mod:`ptools.lib.tui.charts`  - pure-string terminal chart primitives
  (sparklines, gauges) usable in any Rich/Textual cell or plain CLI output.
- :mod:`ptools.lib.tui.screens` - reusable Textual screens (message,
  confirm, input prompt, scrollable text).
- :mod:`ptools.lib.tui.select`  - inline prompt_toolkit arrow-key
  single-select picker.
"""

def get_terminal_width() -> int:
    """Get the current terminal width in characters."""
    import shutil
    return shutil.get_terminal_size((80, 20)).columns