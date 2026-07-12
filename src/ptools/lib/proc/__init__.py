"""Process explorer internals for ``ptools proc``.

- :mod:`ptools.lib.proc.model`   - field registry shared by DSL, CLI and TUI
- :mod:`ptools.lib.proc.query`   - filter expression language (``cpu>50 & name~node``)
- :mod:`ptools.lib.proc.names`   - human-friendly process name resolution
- :mod:`ptools.lib.proc.sources` - psutil core scan + join providers (lsof, launchd, docker, rusage)
- :mod:`ptools.lib.proc.history` - rolling per-process / system sample window
- :mod:`ptools.lib.proc.actions` - kill / renice / sample / etc, shared by CLI and TUI
- :mod:`ptools.lib.proc.app`     - the live Textual TUI
"""
