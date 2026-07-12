"""Human-friendly process name resolution.

Raw process names are often useless on macOS ("Virtualizatio", a bare
"node", sixteen identical "Google Chrome He" helpers). This module
resolves a display name from, in priority order:

1. a user-configured watcher label (``ptools fs watchers labels``),
2. an interpreter + script form, e.g. ``node (vite.js)`` or
   ``python3 (manage.py)``,
3. the innermost macOS ``.app`` bundle name on the executable path,
4. the raw process name.
"""

from __future__ import annotations

import os
import re
from typing import Callable

__version__ = "0.1.0"

_BUNDLE_RE = re.compile(r"/([^/]+)\.app(?:/|$)")
_HELPER_HINTS = ("Helper", "XPC", "PlugIn", "Plugin", "Agent")
_VERSION_SUFFIX_RE = re.compile(r"[\d.]+$")

#: Interpreters whose first script argument is more informative than the binary.
INTERPRETERS = {
    "python", "node", "nodejs", "ruby", "perl", "php", "java",
    "deno", "bun", "sh", "bash", "zsh", "fish", "rscript", "lua",
}


def default_label_resolver(path: str) -> str | None:
    """Resolve a label from the shared watcher-labels config."""
    from ptools.lib.fs.watchers import _resolve_label
    return _resolve_label(path)


def _script_of(cmdline: list[str]) -> str | None:
    """First 'script-like' argument of an interpreter command line."""
    args = cmdline[1:]
    for i, arg in enumerate(args):
        if arg in ("-c", "-e"):
            return None  # inline code string, not a script path
        if arg in ("-m", "-jar"):
            return args[i + 1] if i + 1 < len(args) else None
        if arg.startswith("-"):
            continue
        return arg
    return None


def resolve(
    comm: str | None,
    exe: str | None,
    cmdline: list[str] | None,
    label_resolver: Callable[[str], str | None] | None = None,
) -> dict:
    """Resolve display metadata for a process identity.

    Returns ``{"name", "bundle", "kind", "label"}`` where ``kind`` is
    ``"app"``, ``"helper"`` or ``""``.
    """
    if label_resolver is None:
        label_resolver = default_label_resolver
    exe = exe or ""
    cmdline = cmdline or []
    comm = comm or (os.path.basename(exe) if exe else "?")

    bundle = None
    kind = ""
    matches = _BUNDLE_RE.findall(exe)
    if matches:
        bundle = matches[-1]  # innermost bundle (helpers nest inside apps)
        kind = "helper" if any(hint in exe for hint in _HELPER_HINTS) else "app"

    script_name = None
    base = os.path.basename(exe) or comm
    interpreter = _VERSION_SUFFIX_RE.sub("", base).lower()
    if interpreter in INTERPRETERS:
        script = _script_of(cmdline)
        if script:
            script_name = f"{base} ({os.path.basename(script)})"

    label = None
    try:
        label = label_resolver(exe or comm)
    except Exception:
        pass

    name = label or script_name or bundle or comm
    return {"name": name, "bundle": bundle or "", "kind": kind, "label": label or ""}
