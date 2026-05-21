from ptools.utils.config import LazyConfigFile, config_to_CLI

_watcher_labels = LazyConfigFile(
    name="watcher-labels",
    quiet=True,
)

_DEFAULT_LABELS = {
    "/System/Library/Frameworks/Virtualization.framework": "macOS VM (Docker?)",
    "com.docker": "Docker Desktop",
    "com.apple.WebKit": "WebKit",
    "node": "Node.js",
    "fswatch": "fswatch",
    "fseventsd": "FSEvents daemon",
}


def _resolve_label(exec_path: str) -> str | None:
    """Check persisted labels first, then fall back to default substring matches."""
    label = _watcher_labels.get(exec_path)
    if label:
        return label

    for pattern, name in _watcher_labels.data.items():
        if pattern in exec_path:
            return name

    for pattern, name in _DEFAULT_LABELS.items():
        if pattern in exec_path:
            return name
    return None


def _get_watcher_data():
    """Run lsof and aggregate FD/kqueue counts per (pid, exec_path)."""
    import subprocess

    # Get all open files grouped by PID
    try:
        raw = subprocess.check_output(
            ["lsof", "-n", "-w"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raw = e.output or ""

    pid_data = {}  # pid -> { command, fds, kqueues, user }

    for line in raw.strip().split("\n")[1:]:  # skip header
        parts = line.split()
        if len(parts) < 9:
            continue
        command = parts[0]
        pid = parts[1]
        user = parts[2]
        fd_type = parts[4] if len(parts) > 4 else ""

        if pid not in pid_data:
            pid_data[pid] = {
                "command": command,
                "user": user,
                "fds": 0,
                "kqueues": 0,
            }
        pid_data[pid]["fds"] += 1
        if "KQUEUE" in line or "kqueue" in fd_type.lower():
            pid_data[pid]["kqueues"] += 1

    # Resolve full executable paths via ps
    pids = list(pid_data.keys())
    if not pids:
        return []

    try:
        ps_raw = subprocess.check_output(
            ["ps", "-o", "pid=,comm=", "-p", ",".join(pids)],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError:
        ps_raw = ""

    pid_exec = {}
    for line in ps_raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            pid_exec[parts[0]] = parts[1]

    results = []
    for pid, info in pid_data.items():
        exec_path = pid_exec.get(pid, info["command"])
        label = _resolve_label(exec_path)
        results.append(
            {
                "pid": int(pid),
                "command": info["command"],
                "exec_path": exec_path,
                "label": label or "",
                "user": info["user"],
                "fds": info["fds"],
                "kqueues": info["kqueues"],
            }
        )

    results.sort(key=lambda x: x["fds"], reverse=True)
    return results
