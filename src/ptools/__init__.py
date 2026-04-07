"""ptools - Omar Ibrahim's personal power tools.

``ptools`` is a collection of command-line utilities and small Python
libraries used to speed up day-to-day developer workflows. The package
exposes a single top-level :command:`ptools` CLI (see :mod:`ptools.main`)
that lazily dispatches to a set of subcommand modules such as
:mod:`ptools.rsync`, :mod:`ptools.flow`, :mod:`ptools.llm`,
:mod:`ptools.shell`, :mod:`ptools.time`, and several others.

In addition to the CLI, the :mod:`ptools.utils` package provides
reusable helpers (caching, config, file utilities, formatting, etc.)
that can be imported directly from Python code.
"""
