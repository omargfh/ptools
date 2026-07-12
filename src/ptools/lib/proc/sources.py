"""Process data collection: psutil core scan plus optional join providers.

:func:`scan` returns one plain dict per process (keys documented in
:mod:`ptools.lib.proc.model`). Passing join names enriches the rows from
other sources:

- ``ports``    - listening ports / connection counts (``lsof -i``)
- ``watchers`` - FD & kqueue counts + labels (shares ``ptools fs watchers`` logic)
- ``files``    - open file paths and cwd (``lsof``)
- ``launchd``  - launchd job labels (``launchctl list``)
- ``docker``   - container name/image (``docker inspect``; host-pid match
  only works where containers share the host kernel, i.e. Linux)
- ``io``       - disk read/write rates (``proc_pid_rusage`` on macOS)

Expensive shell-outs are cached module-wide with a short TTL so a live
TUI refreshing every couple of seconds does not hammer ``lsof``.
"""

from __future__ import annotations

import subprocess
import time

from ptools.lib.proc import names

__version__ = "0.1.0"

Row = dict

# fd-count / open-file scans via lsof take seconds on a busy machine.
_CACHE_TTL = {"watchers": 10.0, "files": 10.0, "launchd": 15.0, "docker": 15.0, "ports": 2.0}
_cache: dict[str, tuple[float, object]] = {}


def _cached(key: str, fn):
    """Memoize ``fn()`` under ``key`` for the TTL configured above."""
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None and now - hit[0] < _CACHE_TTL.get(key, 0.0):
        return hit[1]
    value = fn()
    _cache[key] = (now, value)
    return value


def clear_cache() -> None:
    """Drop all join caches (used by explicit refresh)."""
    _cache.clear()


def _run(cmd: list[str], timeout: float = 10.0) -> str:
    """Run a command, returning stdout ('' on any failure)."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


# ----------------------------------------------------------------------
# Core scan
# ----------------------------------------------------------------------

_SCAN_ATTRS = [
    "pid", "ppid", "name", "username", "cmdline", "exe", "status",
    "num_threads", "nice", "create_time", "memory_info", "memory_percent",
    "cpu_percent",
]


def prime(joins: set[str] | None = None) -> None:
    """Prime delta-based collectors (CPU%, IO rates) for one-shot use.

    psutil's ``cpu_percent`` and our IO rates measure *change since the
    previous call*, so a single CLI invocation must sample twice: call
    :func:`prime`, sleep briefly, then :func:`scan`.
    """
    import psutil

    psutil.cpu_percent(interval=None)
    pids = []
    for proc in psutil.process_iter(attrs=["cpu_percent"]):
        pids.append(proc.pid)
    if joins and "io" in joins:
        _join_io({pid: {} for pid in pids})


def scan(joins: set[str] | None = None) -> list[Row]:
    """Snapshot all processes, enriched by the requested ``joins``."""
    import psutil

    joins = set(joins or ())
    now = time.time()
    rows: list[Row] = []

    for proc in psutil.process_iter(attrs=_SCAN_ATTRS):
        info = proc.info
        try:
            cmdline = info.get("cmdline") or []
            exe = info.get("exe") or ""
            comm = info.get("name") or ""
            resolved = names.resolve(comm, exe, cmdline)
            meminfo = info.get("memory_info")
            create_time = info.get("create_time")
            rows.append({
                "pid": info["pid"],
                "ppid": info.get("ppid"),
                "comm": comm,
                "name": resolved["name"],
                "bundle": resolved["bundle"],
                "kind": resolved["kind"],
                "label": resolved["label"],
                "cmd": " ".join(cmdline),
                "exe": exe,
                "user": info.get("username") or "?",
                "cpu": info.get("cpu_percent") or 0.0,
                "mem": meminfo.rss if meminfo else 0,
                "mem_pct": round(info.get("memory_percent") or 0.0, 1),
                "status": info.get("status") or "?",
                "threads": info.get("num_threads") or 0,
                "nice": info.get("nice"),
                "age": (now - create_time) if create_time else None,
                "started": time.strftime("%b %d %H:%M", time.localtime(create_time)) if create_time else "",
            })
        except psutil.Error:
            continue

    rows_by_pid = {row["pid"]: row for row in rows}
    for join in joins:
        provider = JOIN_PROVIDERS.get(join)
        if provider is not None:
            provider(rows_by_pid)
    return rows


def system_snapshot() -> dict:
    """Overall CPU/memory/load stats for the TUI header panel."""
    import os
    import psutil

    vm = psutil.virtual_memory()
    try:
        load = os.getloadavg()
    except OSError:
        load = (0.0, 0.0, 0.0)
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ncpu": psutil.cpu_count() or 1,
        "mem_pct": vm.percent,
        "mem_used": vm.total - vm.available,
        "mem_total": vm.total,
        "load": load,
        "nproc": len(psutil.pids()),
    }


# ----------------------------------------------------------------------
# Join providers - each sets defaults on every row, then fills in data.
# ----------------------------------------------------------------------

def _set_defaults(rows_by_pid: dict[int, Row], defaults: dict) -> None:
    for row in rows_by_pid.values():
        for key, value in defaults.items():
            row.setdefault(key, [] if value == [] else value)


def _join_ports(rows_by_pid: dict[int, Row]) -> None:
    """Listening ports and connection counts, via ``lsof -nP -i``."""
    _set_defaults(rows_by_pid, {"ports": [], "conns": 0})

    def collect():
        listen: dict[int, set[int]] = {}
        conns: dict[int, int] = {}
        out = _run(["lsof", "-nP", "-i"])
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 9 or not parts[1].isdigit():
                continue
            pid = int(parts[1])
            name = " ".join(parts[8:])
            if "(LISTEN)" in name:
                addr = name.split(" ", 1)[0]
                port_text = addr.rsplit(":", 1)[-1]
                if port_text.isdigit():
                    listen.setdefault(pid, set()).add(int(port_text))
            else:
                conns[pid] = conns.get(pid, 0) + 1
        return listen, conns

    listen, conns = _cached("ports", collect)
    for pid, ports in listen.items():
        if pid in rows_by_pid:
            rows_by_pid[pid]["ports"] = sorted(ports)
    for pid, count in conns.items():
        if pid in rows_by_pid:
            rows_by_pid[pid]["conns"] = count


def _join_watchers(rows_by_pid: dict[int, Row]) -> None:
    """FD/kqueue counts from the shared ``fs watchers`` scan."""
    _set_defaults(rows_by_pid, {"fds": 0, "kqueues": 0})

    def collect():
        from ptools.lib.fs.watchers import _get_watcher_data
        return _get_watcher_data()

    for entry in _cached("watchers", collect):
        row = rows_by_pid.get(entry["pid"])
        if row is None:
            continue
        row["fds"] = entry["fds"]
        row["kqueues"] = entry["kqueues"]
        if entry.get("label") and not row.get("label"):
            row["label"] = entry["label"]
            row["name"] = entry["label"]


_MAX_FILES_PER_PROC = 512


def _join_files(rows_by_pid: dict[int, Row]) -> None:
    """Open file paths and cwd per process, via ``lsof -F``."""
    _set_defaults(rows_by_pid, {"files": [], "nfiles": 0, "cwd": ""})

    def collect():
        per_pid: dict[int, dict] = {}
        out = _run(["lsof", "-n", "-w", "-Fpfn"], timeout=30.0)
        pid = None
        fd = None
        for line in out.splitlines():
            tag, value = line[:1], line[1:]
            if tag == "p" and value.isdigit():
                pid = int(value)
                per_pid.setdefault(pid, {"files": [], "cwd": ""})
            elif tag == "f":
                fd = value
            elif tag == "n" and pid is not None and value.startswith("/"):
                entry = per_pid[pid]
                if fd == "cwd":
                    entry["cwd"] = value
                elif len(entry["files"]) < _MAX_FILES_PER_PROC:
                    entry["files"].append(value)
        return per_pid

    for pid, data in _cached("files", collect).items():
        row = rows_by_pid.get(pid)
        if row is None:
            continue
        row["files"] = data["files"]
        row["nfiles"] = len(data["files"])
        row["cwd"] = data["cwd"]


def _join_launchd(rows_by_pid: dict[int, Row]) -> None:
    """launchd job labels for the current user, via ``launchctl list``."""
    _set_defaults(rows_by_pid, {"service": ""})

    def collect():
        services: dict[int, str] = {}
        for line in _run(["launchctl", "list"]).splitlines()[1:]:
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0].isdigit():
                services[int(parts[0])] = parts[2]
        return services

    for pid, label in _cached("launchd", collect).items():
        if pid in rows_by_pid:
            rows_by_pid[pid]["service"] = label


def _join_docker(rows_by_pid: dict[int, Row]) -> None:
    """Container name/image by host PID, via ``docker inspect``."""
    _set_defaults(rows_by_pid, {"container": "", "image": ""})

    def collect():
        containers: dict[int, tuple[str, str]] = {}
        ids = _run(["docker", "ps", "-q"], timeout=3.0).split()
        if ids:
            fmt = "{{.State.Pid}}|{{.Name}}|{{.Config.Image}}"
            out = _run(["docker", "inspect", "-f", fmt, *ids], timeout=5.0)
            for line in out.splitlines():
                parts = line.split("|")
                if len(parts) == 3 and parts[0].isdigit():
                    containers[int(parts[0])] = (parts[1].lstrip("/"), parts[2])
        return containers

    for pid, (container, image) in _cached("docker", collect).items():
        if pid in rows_by_pid:
            rows_by_pid[pid]["container"] = container
            rows_by_pid[pid]["image"] = image


# pid -> (monotonic time, cumulative read, cumulative written)
_io_prev: dict[int, tuple[float, int, int]] = {}


def _join_io(rows_by_pid: dict[int, Row]) -> None:
    """Disk read/write rates (bytes/sec) from macOS rusage counters.

    Rates are deltas against the previous call, so the first sample in a
    process's lifetime reports 0. ``None`` means the kernel denied access
    (another user's process); render as unknown, not zero.
    """
    from ptools.lib.proc.macos import disk_io

    now = time.monotonic()
    for pid, row in rows_by_pid.items():
        io = disk_io(pid)
        if io is None:
            row["io_read"] = None
            row["io_write"] = None
            continue
        read, written = io
        prev = _io_prev.get(pid)
        if prev is not None and now > prev[0]:
            dt = now - prev[0]
            row["io_read"] = max(0.0, (read - prev[1]) / dt)
            row["io_write"] = max(0.0, (written - prev[2]) / dt)
        else:
            row["io_read"] = 0.0
            row["io_write"] = 0.0
        _io_prev[pid] = (now, read, written)

    for gone in set(_io_prev) - set(rows_by_pid):
        del _io_prev[gone]


JOIN_PROVIDERS = {
    "ports": _join_ports,
    "watchers": _join_watchers,
    "files": _join_files,
    "launchd": _join_launchd,
    "docker": _join_docker,
    "io": _join_io,
}


# ----------------------------------------------------------------------
# Single-process deep dive
# ----------------------------------------------------------------------

def process_detail(pid: int) -> dict:
    """Everything knowable about one PID; inaccessible parts become None."""
    import psutil

    proc = psutil.Process(pid)  # raises NoSuchProcess for the caller to handle

    def safe(fn):
        try:
            return fn()
        except (psutil.Error, OSError):
            return None

    with proc.oneshot():
        parent = safe(proc.parent)
        meminfo = safe(proc.memory_info)
        create_time = safe(proc.create_time)
        detail = {
            "pid": pid,
            "name": safe(proc.name),
            "exe": safe(proc.exe),
            "cmdline": safe(proc.cmdline),
            "user": safe(proc.username),
            "status": safe(proc.status),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(create_time)) if create_time else None,
            "cpu": safe(lambda: proc.cpu_percent(interval=0.1)),
            "mem_rss": meminfo.rss if meminfo else None,
            "mem_vms": meminfo.vms if meminfo else None,
            "mem_pct": safe(proc.memory_percent),
            "threads": safe(proc.num_threads),
            "nice": safe(proc.nice),
            "cwd": safe(proc.cwd),
            "terminal": safe(proc.terminal),
            "parent": f"{parent.pid} {parent.name()}" if parent else None,
            "children": safe(lambda: [
                {"pid": c.pid, "name": c.name()} for c in proc.children()
            ]),
            "open_files": safe(lambda: [f.path for f in proc.open_files()]),
            "connections": safe(lambda: [
                {
                    "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                    "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                    "status": c.status,
                }
                for c in proc.net_connections()
            ]),
            "environ": safe(proc.environ),
        }

    resolved = names.resolve(detail["name"], detail["exe"], detail["cmdline"])
    detail["display_name"] = resolved["name"]
    detail["bundle"] = resolved["bundle"]
    return detail
