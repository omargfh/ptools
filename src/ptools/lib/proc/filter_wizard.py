"""Shell-agnostic building blocks for a picker-driven filter-clause builder.

Both the CLI wizard (``ptools proc list --wizard`` in :mod:`ptools.proc`)
and the Textual TUI's filter screen (:class:`ptools.lib.proc.app.FilterWizardScreen`)
pick a field from :data:`ptools.lib.proc.model.FIELDS`, an operator valid
for that field's ``kind``, and a value - then join clauses with ``&``/``|``.
The bits that don't care which UI toolkit is asking (which operators a
kind allows, how to quote a value, how to join clauses) live here so
neither caller has to duplicate them.

Nothing here talks to a terminal, prompt_toolkit, or Textual - it only
turns ``(field, operator, value)`` into strings that
:func:`ptools.lib.proc.query.compile_query` accepts.
"""

from __future__ import annotations

from ptools.lib.proc.model import DURATION, NUM, NUM_LIST, SIZE, STR, STR_LIST, Field

__version__ = "0.1.0"

# Kinds compared with ordering/equality operators (see query.py's
# _make_comparison); everything else is string-ish (=, !=, ~, !~).
NUMERIC_KINDS = (NUM, SIZE, DURATION, NUM_LIST)

OPERATOR_LABELS = {
    "=": "= (equals)",
    "!=": "!= (not equal)",
    ">": "> (greater than)",
    ">=": ">= (greater or equal)",
    "<": "< (less than)",
    "<=": "<= (less or equal)",
    "~": "~ (contains / regex)",
    "!~": "!~ (does not contain / regex)",
}

VALUE_PLACEHOLDERS = {
    NUM: "e.g. 50",
    SIZE: "e.g. 500MB",
    DURATION: "e.g. 30s, 5m, 2h",
    NUM_LIST: "e.g. 3000",
    STR: "e.g. node",
    STR_LIST: "e.g. /Users/me/project",
}


def operators_for_kind(kind: str) -> list[str]:
    """Operators valid for *kind*, mirroring query.py's own rules exactly."""
    if kind in NUMERIC_KINDS:
        return ["=", "!=", ">", ">=", "<", "<="]
    return ["=", "!=", "~", "!~"]


def quote_value(value: str) -> str:
    """Quote *value* if it contains syntax the query tokenizer would split on."""
    if not any(c in value for c in " \t\"'&|()<>=~!"):
        return value
    quote = "'" if '"' in value and "'" not in value else '"'
    return f"{quote}{value}{quote}"


def format_clause(field: Field, op: str, value: str) -> str:
    """Build one clause string (e.g. ``cpu>50``) from a field/operator/value."""
    return f"{field.key}{op}{quote_value(value)}"


def join_clauses(clauses: list[str], combinators: list[str]) -> str | None:
    """Join *clauses* with the ``&``/``|`` in *combinators*, parenthesizing each.

    ``combinators[i]`` joins ``clauses[i]`` and ``clauses[i + 1]``; any
    extra trailing combinator (e.g. the user picked "AND" then cancelled
    before completing one more clause) is silently dropped. Returns
    ``None`` if *clauses* is empty.
    """
    if not clauses:
        return None
    pieces = [f"({clauses[0]})"]
    for combinator, clause in zip(combinators, clauses[1:]):
        pieces.append(combinator)
        pieces.append(f"({clause})")
    return " ".join(pieces)
