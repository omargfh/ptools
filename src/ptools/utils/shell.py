"""Shell utilities for ptools."""
from functools import wraps
from enum import Enum

from ptools.utils.lazy import Lazy
from ptools.utils.print import PrintUtils

__version__ = "0.0.1"

def detect_shell() -> str:
    """Detect the current shell executable."""
    import os

    if os.name == "nt":
        return os.environ.get("COMSPEC", "cmd.exe")
    else:
        return os.environ.get("SHELL", "/bin/sh")

class ShellKind(Enum):
    """Enum for supported shell types."""
    SH = "sh"
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    CMD = "cmd"
    POWERSHELL = "powershell"
    UNKNOWN = "unknown"

def detect_shell_kind(shell: str | None = None) -> ShellKind:
    """Detect the kind of the current shell.

    Order matters: ``bash``/``zsh``/``fish``/``powershell`` all contain the
    substring ``sh``, so the bare ``sh`` check must come last as a fallback.
    """
    shell = shell or detect_shell()
    if "bash" in shell:
        return ShellKind.BASH
    elif "zsh" in shell:
        return ShellKind.ZSH
    elif "fish" in shell:
        return ShellKind.FISH
    elif "powershell" in shell:
        return ShellKind.POWERSHELL
    elif "cmd" in shell:
        return ShellKind.CMD
    elif "sh" in shell:
        return ShellKind.SH
    else:
        return ShellKind.UNKNOWN

def detect_shell_config() -> str:
    """Detect the shell configuration file based on the current shell."""
    import os

    shell = detect_shell_kind()
    if shell == ShellKind.SH:
        return os.path.expanduser("~/.profile")
    elif shell == ShellKind.BASH:
        return os.path.expanduser("~/.bashrc")
    elif shell == ShellKind.ZSH:
        return os.path.expanduser("~/.zshrc")
    elif shell == ShellKind.FISH:
        return os.path.expanduser("~/.config/fish/config.fish")
    elif shell == ShellKind.CMD:
        return os.path.expanduser("~/_cmdrc")
    elif shell == ShellKind.POWERSHELL:
        return os.path.expanduser("~/Documents/WindowsPowerShell/profile.ps1")
    else:
        return os.path.expanduser("~/.profile")  # Default to .profile for unknown shells
