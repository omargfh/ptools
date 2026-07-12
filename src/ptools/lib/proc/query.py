"""Filter expression language for process rows.

Examples::

    cpu>50 & mem>500MB
    port=3000 | port=8080
    name~node & user=me
    files~/Users/me/project & !status=zombie
    (cpu>10 | fds>500) & user=me
    vscode                      # bare word: substring over name/cmd/label/...

Operators: ``=  !=  ~  !~  >  >=  <  <=`` combined with ``&``/``and``,
``|``/``or``, ``!``/``not`` and parentheses. Values may be quoted when
they contain spaces or operator characters. Field kinds (see
:mod:`ptools.lib.proc.model`) drive coercion: sizes accept ``500MB``,
durations accept ``30s/5m/2h/1d/1w``, and ``user=me`` expands to the
current user.

:func:`compile_query` raises :class:`QueryError` on any syntax problem;
callers that want forgiving behavior (the TUI filter bar) fall back to
:func:`substring_query`.
"""

from __future__ import annotations

import re
from typing import Callable

from ptools.lib.proc import model
from ptools.utils.read import FromHumanized

__version__ = "0.1.0"

Row = dict
Matcher = Callable[[Row], bool]


class QueryError(ValueError):
    """Raised when a filter expression cannot be parsed or compiled."""


# ----------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------

_PUNCT = "&|()"
_OP_CHARS = "<>=~!"
# Characters that terminate a bare (unquoted) atom.
_ATOM_BREAK = set(_PUNCT) | set(_OP_CHARS) | set(" \t\r\n") | {'"', "'"}

_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


class _Token:
    __slots__ = ("type", "value", "quoted")

    def __init__(self, type_: str, value: str, quoted: bool = False):
        self.type = type_    # 'punct' | 'op' | 'atom'
        self.value = value
        self.quoted = quoted

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"_Token({self.type!r}, {self.value!r})"


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c in _PUNCT:
            tokens.append(_Token("punct", c))
            i += 1
        elif c in "<>":
            if i + 1 < n and text[i + 1] == "=":
                tokens.append(_Token("op", c + "="))
                i += 2
            else:
                tokens.append(_Token("op", c))
                i += 1
        elif c == "!":
            if i + 1 < n and text[i + 1] in "=~":
                tokens.append(_Token("op", c + text[i + 1]))
                i += 2
            else:
                tokens.append(_Token("punct", "!"))
                i += 1
        elif c in "=~":
            tokens.append(_Token("op", c))
            i += 1
        elif c in "\"'":
            end = text.find(c, i + 1)
            if end < 0:
                raise QueryError(f"Unterminated quote in: {text!r}")
            tokens.append(_Token("atom", text[i + 1:end], quoted=True))
            i = end + 1
        else:
            j = i
            while j < n and text[j] not in _ATOM_BREAK:
                j += 1
            tokens.append(_Token("atom", text[i:j]))
            i = j
    return tokens


# ----------------------------------------------------------------------
# Parser (precedence: | < & < ! < atoms/parens)
# ----------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens: list[_Token], current_user: str | None):
        self.tokens = tokens
        self.pos = 0
        self.current_user = current_user
        self.fields_used: set[str] = set()

    def _peek(self) -> _Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> _Token:
        token = self._peek()
        if token is None:
            raise QueryError("Unexpected end of expression")
        self.pos += 1
        return token

    def _is_word(self, token: _Token | None, word: str) -> bool:
        return (
            token is not None
            and token.type == "atom"
            and not token.quoted
            and token.value.lower() == word
        )

    def parse(self) -> Matcher:
        node = self._parse_or()
        if self._peek() is not None:
            raise QueryError(f"Unexpected token: {self._peek().value!r}")
        return node

    def _parse_or(self) -> Matcher:
        left = self._parse_and()
        parts = [left]
        while True:
            token = self._peek()
            if (token and token.type == "punct" and token.value == "|") or self._is_word(token, "or"):
                self._next()
                parts.append(self._parse_and())
            else:
                break
        if len(parts) == 1:
            return parts[0]
        return lambda row: any(p(row) for p in parts)

    def _parse_and(self) -> Matcher:
        parts = [self._parse_not()]
        while True:
            token = self._peek()
            if (token and token.type == "punct" and token.value == "&") or self._is_word(token, "and"):
                self._next()
                parts.append(self._parse_not())
            else:
                break
        if len(parts) == 1:
            return parts[0]
        return lambda row: all(p(row) for p in parts)

    def _parse_not(self) -> Matcher:
        token = self._peek()
        if (token and token.type == "punct" and token.value == "!") or self._is_word(token, "not"):
            self._next()
            inner = self._parse_not()
            return lambda row: not inner(row)
        return self._parse_primary()

    def _parse_primary(self) -> Matcher:
        token = self._next()
        if token.type == "punct" and token.value == "(":
            inner = self._parse_or()
            closing = self._next()
            if not (closing.type == "punct" and closing.value == ")"):
                raise QueryError("Expected ')'")
            return inner
        if token.type != "atom":
            raise QueryError(f"Unexpected token: {token.value!r}")

        nxt = self._peek()
        if nxt is not None and nxt.type == "op":
            op = self._next().value
            value = self._next()
            if value.type != "atom":
                raise QueryError(f"Expected a value after '{op}', got {value.value!r}")
            return self._make_comparison(token.value, op, value)

        # Bare word: substring match across the usual identity fields.
        return _bare_matcher(token.value)

    # ------------------------------------------------------------------
    # Comparison compilation
    # ------------------------------------------------------------------

    def _make_comparison(self, field_name: str, op: str, value_token: _Token) -> Matcher:
        field = model.FIELD_MAP.get(field_name.lower())
        if field is None:
            known = ", ".join(sorted({f.key for f in model.FIELDS}))
            raise QueryError(f"Unknown field {field_name!r}. Known fields: {known}")
        self.fields_used.add(field.key)

        raw = value_token.value
        key = field.key

        if field.kind in (model.NUM, model.SIZE, model.DURATION, model.NUM_LIST):
            if op in ("~", "!~"):
                raise QueryError(f"Operator {op!r} is not valid for numeric field {key!r}")
            target = _coerce_number(field.kind, raw)
            if field.kind == model.NUM_LIST:
                return _num_list_matcher(key, op, target)
            return _number_matcher(key, op, target)

        # String-ish fields
        if op in (">", ">=", "<", "<="):
            raise QueryError(f"Operator {op!r} is not valid for text field {key!r}")
        if key == "user" and raw == "me" and not value_token.quoted and self.current_user:
            raw = self.current_user
        if field.kind == model.STR_LIST:
            return _str_list_matcher(key, op, raw)
        return _string_matcher(key, op, raw)


def _coerce_number(kind: str, raw: str) -> float:
    text = raw.strip().rstrip("%")
    try:
        return float(text)
    except ValueError:
        pass
    if kind == model.SIZE:
        try:
            return float(FromHumanized.from_humanized_size(raw))
        except ValueError:
            raise QueryError(f"Expected a number or size (e.g. 500MB), got {raw!r}")
    if kind == model.DURATION:
        unit = raw[-1:].lower()
        if unit in _DURATION_UNITS:
            try:
                return float(raw[:-1]) * _DURATION_UNITS[unit]
            except ValueError:
                pass
        raise QueryError(f"Expected a duration (e.g. 30s, 5m, 2h), got {raw!r}")
    raise QueryError(f"Expected a number, got {raw!r}")


def _compare(op: str, actual: float, target: float) -> bool:
    if op == "=":
        return actual == target
    if op == "!=":
        return actual != target
    if op == ">":
        return actual > target
    if op == ">=":
        return actual >= target
    if op == "<":
        return actual < target
    if op == "<=":
        return actual <= target
    raise QueryError(f"Unsupported operator: {op!r}")


def _number_matcher(key: str, op: str, target: float) -> Matcher:
    def match(row: Row) -> bool:
        actual = row.get(key)
        if actual is None:
            return False
        return _compare(op, float(actual), target)
    return match


def _num_list_matcher(key: str, op: str, target: float) -> Matcher:
    def match(row: Row) -> bool:
        values = row.get(key) or []
        if op == "!=":
            return all(float(v) != target for v in values)
        return any(_compare(op, float(v), target) for v in values)
    return match


def _text_predicate(op: str, raw: str) -> Callable[[str], bool]:
    """Build an element-level text predicate for =, !=, ~ and !~."""
    lowered = raw.lower()
    if op in ("=", "!="):
        base = lambda s: s.lower() == lowered
    else:  # ~ / !~ : regex when valid, substring otherwise
        try:
            pattern = re.compile(raw, re.IGNORECASE)
            base = lambda s: pattern.search(s) is not None
        except re.error:
            base = lambda s: lowered in s.lower()
    if op.startswith("!"):
        return lambda s: not base(s)
    return base


def _string_matcher(key: str, op: str, raw: str) -> Matcher:
    predicate = _text_predicate(op, raw)
    return lambda row: predicate(str(row.get(key) or ""))


def _str_list_matcher(key: str, op: str, raw: str) -> Matcher:
    predicate = _text_predicate(op, raw)
    if op.startswith("!"):
        # Negated ops must hold for every element (and an empty list passes).
        return lambda row: all(predicate(str(v)) for v in (row.get(key) or []))
    return lambda row: any(predicate(str(v)) for v in (row.get(key) or []))


def _bare_matcher(word: str) -> Matcher:
    needle = word.lower()

    def match(row: Row) -> bool:
        for key in model.BARE_MATCH_FIELDS:
            if needle in str(row.get(key) or "").lower():
                return True
        return False
    return match


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

class Query:
    """A compiled filter: ``query.match(row)`` -> bool."""

    def __init__(self, matcher: Matcher, text: str, fields_used: set[str]):
        self._matcher = matcher
        self.text = text
        self.fields_used = fields_used

    def match(self, row: Row) -> bool:
        return self._matcher(row)

    def required_joins(self) -> set[str]:
        return model.required_joins(self.fields_used)


def compile_query(text: str | None, current_user: str | None = None) -> Query:
    """Compile ``text`` into a :class:`Query`; empty text matches everything.

    :raises QueryError: on any syntax or type problem.
    """
    text = (text or "").strip()
    if not text:
        return Query(lambda row: True, "", set())
    if current_user is None:
        import getpass
        try:
            current_user = getpass.getuser()
        except Exception:
            current_user = None
    parser = _Parser(_tokenize(text), current_user)
    matcher = parser.parse()
    return Query(matcher, text, parser.fields_used)


def substring_query(text: str) -> Query:
    """Forgiving fallback: match ``text`` as a plain substring."""
    text = (text or "").strip()
    if not text:
        return Query(lambda row: True, "", set())
    return Query(_bare_matcher(text), text, set())
