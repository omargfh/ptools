"""Shell compiler: Python representations of shell primitives that can be
compiled to sh/bash/zsh or PowerShell script files.
"""

__version__ = "0.1.0"

from ptools.lib.shellc.compiler import (
    ShellVar,
    ShellAlias,
    ShellFunc,
    ShellScript,
    Dialect,
)

__all__ = [
    "ShellVar",
    "ShellAlias",
    "ShellFunc",
    "ShellScript",
    "Dialect",
]
