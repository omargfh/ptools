"""Shell compiler primitives.

Provides :class:`ShellVar`, :class:`ShellAlias`, :class:`ShellFunc`, and
:class:`ShellScript` - Python representations of shell constructs that can
be compiled (dumped) into one of the supported :class:`Dialect` targets:
``sh``, ``bash``, ``zsh``, or ``powershell``.

Functions are special: because sh-family and PowerShell syntax diverge
significantly, a :class:`ShellFunc` is constructed from *two* string bodies
- one for POSIX-ish shells and one for PowerShell - which are emitted
verbatim inside the appropriate function wrapper for the target dialect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence, Union

__version__ = "0.1.0"


class Dialect(str, Enum):
    """Target shell dialect for the compiler (POSIX-family or PowerShell)."""

    SH = "sh"
    BASH = "bash"
    ZSH = "zsh"
    POWERSHELL = "powershell"

    @property
    def is_posix(self) -> bool:
        """Whether this dialect uses POSIX-style syntax (sh/bash/zsh)."""
        return self in (Dialect.SH, Dialect.BASH, Dialect.ZSH)

    @property
    def shebang(self) -> str:
        """Return the canonical ``#!`` line for this dialect."""
        return {
            Dialect.SH: "#!/bin/sh",
            Dialect.BASH: "#!/usr/bin/env bash",
            Dialect.ZSH: "#!/usr/bin/env zsh",
            Dialect.POWERSHELL: "#!/usr/bin/env pwsh",
        }[self]

    @property
    def comment(self) -> str:
        """Return the line-comment character for this dialect."""
        return "#"  # all four use '#' for line comments


def _coerce_dialect(d: Union[str, Dialect]) -> Dialect:
    """Coerce a dialect name or enum value into a :class:`Dialect`."""
    if isinstance(d, Dialect):
        return d
    return Dialect(d.lower())


def _posix_single_quote(value: str) -> str:
    """Safely single-quote a string for POSIX shells."""
    return "'" + value.replace("'", "'\\''") + "'"


def _powershell_single_quote(value: str) -> str:
    """Safely single-quote a string for PowerShell (doubled single quotes)."""
    return "'" + value.replace("'", "''") + "'"


@dataclass
class ShellVar:
    """A shell variable / environment export."""

    name: str
    value: str
    export: bool = True

    def compile(self, dialect: Union[str, Dialect]) -> str:
        """Render this variable as source code for the given ``dialect``."""
        d = _coerce_dialect(dialect)
        if d.is_posix:
            q = _posix_single_quote(self.value)
            if self.export:
                return f"export {self.name}={q}"
            return f"{self.name}={q}"
        # PowerShell
        q = _powershell_single_quote(self.value)
        if self.export:
            return f"$env:{self.name} = {q}"
        return f"${self.name} = {q}"


@dataclass
class ShellAlias:
    """A shell alias."""

    name: str
    command: str

    def compile(self, dialect: Union[str, Dialect]) -> str:
        """Render this alias as source code for the given ``dialect``."""
        d = _coerce_dialect(dialect)
        if d.is_posix:
            return f"alias {self.name}={_posix_single_quote(self.command)}"
        # PowerShell: Set-Alias only works for single commands; for command
        # lines with arguments, define a function wrapper instead.
        if any(ch in self.command for ch in (" ", "\t", "|", ";", "&")):
            return (
                f"function {self.name} {{ {self.command} @args }}"
            )
        return f"Set-Alias -Name {self.name} -Value {self.command}"


@dataclass
class ShellFunc:
    """A shell function.

    ``posix_body`` is emitted inside a ``name() {{ ... }}`` wrapper for
    sh/bash/zsh. ``powershell_body`` is emitted inside a
    ``function name {{ ... }}`` wrapper for PowerShell. Bodies are inserted
    verbatim - the caller is responsible for their correctness.
    """

    name: str
    posix_body: str
    powershell_body: str

    def compile(self, dialect: Union[str, Dialect]) -> str:
        """Render the appropriate body wrapped in a function declaration for ``dialect``."""
        d = _coerce_dialect(dialect)
        if d.is_posix:
            body = _indent(self.posix_body.strip("\n"), "    ")
            return f"{self.name}() {{\n{body}\n}}"
        body = _indent(self.powershell_body.strip("\n"), "    ")
        return f"function {self.name} {{\n{body}\n}}"


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else line for line in text.splitlines())


Part = Union[ShellVar, ShellAlias, ShellFunc]


@dataclass
class ShellScript:
    """A collection of shell parts that can be compiled into a script file."""

    parts: list[Part] = field(default_factory=list)
    header: str | None = None

    def add(self, part: Part) -> "ShellScript":
        """Append ``part`` to the script and return ``self`` for chaining."""
        self.parts.append(part)
        return self

    def extend(self, parts: Iterable[Part]) -> "ShellScript":
        """Append multiple ``parts`` to the script and return ``self``."""
        self.parts.extend(parts)
        return self

    def compile(self, dialect: Union[str, Dialect]) -> str:
        """Render the entire script (shebang, header, sections) for ``dialect``."""
        d = _coerce_dialect(dialect)
        lines: list[str] = [d.shebang, ""]
        if self.header:
            for hl in self.header.splitlines():
                lines.append(f"{d.comment} {hl}" if hl else d.comment)
            lines.append("")

        vars_ = [p for p in self.parts if isinstance(p, ShellVar)]
        aliases = [p for p in self.parts if isinstance(p, ShellAlias)]
        funcs = [p for p in self.parts if isinstance(p, ShellFunc)]

        def _section(title: str, items: Sequence[Part], sep: str = "\n") -> None:
            if not items:
                return
            lines.append(f"{d.comment} {title}")
            for item in items:
                lines.append(item.compile(d))
            if sep:
                lines.append("")

        _section("Variables", vars_)
        _section("Aliases", aliases)
        if funcs:
            lines.append(f"{d.comment} Functions")
            for i, fn in enumerate(funcs):
                lines.append(fn.compile(d))
                if i != len(funcs) - 1:
                    lines.append("")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def write(
        self,
        path: Union[str, Path],
        dialect: Union[str, Dialect],
    ) -> Path:
        """Compile the script for ``dialect`` and write it to ``path``."""
        p = Path(path)
        p.write_text(self.compile(dialect))
        return p
