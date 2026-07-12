"""Field registry for process rows.

One registry drives everything: the query DSL knows how to coerce and
compare each field, the CLI knows which columns exist, and the TUI knows
which columns each join contributes. A field with ``join`` set is only
populated when that join provider runs; :func:`required_joins` maps the
fields referenced by a query back to the joins that must be enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

__version__ = "0.1.0"

# Field kinds - drive value coercion and comparison in the query DSL.
NUM = "num"            # plain number (cpu %, counts, pid, ...)
SIZE = "size"          # bytes; accepts humanized literals like 500MB
STR = "str"            # string; = exact (ci), ~ regex/substring
DURATION = "duration"  # seconds; accepts 30s / 5m / 2h / 1d / 1w
NUM_LIST = "num_list"  # list of numbers; = is membership (ports)
STR_LIST = "str_list"  # list of strings; ~/= match any element (files)


@dataclass(frozen=True)
class Field:
    key: str
    kind: str
    title: str
    join: str | None = None
    aliases: tuple[str, ...] = ()
    help: str = ""


FIELDS: list[Field] = [
    # Core (always populated by the psutil scan)
    Field("pid", NUM, "PID"),
    Field("ppid", NUM, "PPID"),
    Field("name", STR, "Name", help="Resolved display name (bundle/label/script aware)"),
    Field("comm", STR, "Comm", aliases=("proc",), help="Raw process name"),
    Field("cmd", STR, "Cmdline", aliases=("cmdline", "args")),
    Field("exe", STR, "Exe"),
    Field("user", STR, "User", aliases=("username",)),
    Field("cpu", NUM, "CPU%", aliases=("cpu%",)),
    Field("mem", SIZE, "MEM", aliases=("rss",)),
    Field("mem_pct", NUM, "MEM%", aliases=("mem%",)),
    Field("status", STR, "St", aliases=("state",)),
    Field("threads", NUM, "Thr"),
    Field("nice", NUM, "Ni"),
    Field("age", DURATION, "Age", aliases=("uptime",)),
    Field("started", STR, "Started"),
    Field("bundle", STR, "Bundle", help="macOS .app bundle name, if any"),
    Field("kind", STR, "Kind", help="app / helper / '' "),
    Field("label", STR, "Label", help="User-configured watcher label"),
    # ports join
    Field("ports", NUM_LIST, "Ports", join="ports", aliases=("port",), help="Listening TCP/UDP ports"),
    Field("conns", NUM, "Conns", join="ports", aliases=("connections",), help="Non-listen socket count"),
    # watchers join
    Field("fds", NUM, "FDs", join="watchers", help="Open file descriptor count"),
    Field("kqueues", NUM, "KQ", join="watchers", aliases=("kq",), help="kqueue (file watcher) count"),
    # files join
    Field("files", STR_LIST, "Files", join="files", aliases=("file",), help="Open file paths"),
    Field("nfiles", NUM, "#Files", join="files"),
    Field("cwd", STR, "CWD", join="files"),
    # launchd join
    Field("service", STR, "Service", join="launchd", help="launchd job label"),
    # docker join
    Field("container", STR, "Container", join="docker"),
    Field("image", STR, "Image", join="docker"),
    # io join
    Field("io_read", SIZE, "R/s", join="io", aliases=("ior", "read")),
    Field("io_write", SIZE, "W/s", join="io", aliases=("iow", "write")),
]

FIELD_MAP: dict[str, Field] = {}
for _f in FIELDS:
    FIELD_MAP[_f.key] = _f
    for _a in _f.aliases:
        FIELD_MAP[_a] = _f

#: All join provider names, in display/toggle order.
JOINS: tuple[str, ...] = ("ports", "watchers", "files", "launchd", "docker", "io")

#: Fields a bare (no-operator) query word is matched against.
BARE_MATCH_FIELDS: tuple[str, ...] = (
    "name", "comm", "cmd", "label", "bundle", "service", "container", "user",
)


def required_joins(field_keys: Iterable[str]) -> set[str]:
    """Return the joins needed to populate the given field keys."""
    joins = set()
    for key in field_keys:
        field = FIELD_MAP.get(key)
        if field is not None and field.join is not None:
            joins.add(field.join)
    return joins
