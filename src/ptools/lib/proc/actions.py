"""Process actions shared by the ``proc`` CLI and TUI.

Every action returns a human-readable success message and raises
:class:`ActionError` with a human-readable reason on failure, so both
frontends can surface results uniformly.
"""

from __future__ import annotations

import os
import signal
import subprocess

__version__ = "0.1.0"


class ActionError(RuntimeError):
    """An action failed for a reason worth showing to the user."""


def _kill(pid: int, sig: int) -> None:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        raise ActionError(f"PID {pid} not found (already exited?)")
    except PermissionError:
        raise ActionError(f"Permission denied for PID {pid}. Try with sudo.")


def terminate(pid: int, force: bool = False) -> str:
    sig = signal.SIGKILL if force else signal.SIGTERM
    _kill(pid, sig)
    return f"Sent {'SIGKILL' if force else 'SIGTERM'} to PID {pid}."


def kill_tree(pid: int, force: bool = False) -> str:
    """Kill a process and all its descendants (children first)."""
    import psutil

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        proc = psutil.Process(pid)
        targets = proc.children(recursive=True) + [proc]
    except psutil.NoSuchProcess:
        raise ActionError(f"PID {pid} not found (already exited?)")

    killed = 0
    for target in targets:
        try:
            target.send_signal(sig)
            killed += 1
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            raise ActionError(f"Permission denied for PID {target.pid}. Try with sudo.")
    return f"Sent {'SIGKILL' if force else 'SIGTERM'} to {killed} process(es) in tree of PID {pid}."


def toggle_suspend(pid: int) -> str:
    """SIGSTOP a running process, SIGCONT a stopped one."""
    import psutil

    try:
        status = psutil.Process(pid).status()
    except psutil.NoSuchProcess:
        raise ActionError(f"PID {pid} not found (already exited?)")
    except psutil.AccessDenied:
        status = ""

    if status == psutil.STATUS_STOPPED:
        _kill(pid, signal.SIGCONT)
        return f"Resumed PID {pid} (SIGCONT)."
    _kill(pid, signal.SIGSTOP)
    return f"Suspended PID {pid} (SIGSTOP). Press again to resume."


def renice(pid: int, value: int) -> str:
    import psutil

    try:
        psutil.Process(pid).nice(value)
    except psutil.NoSuchProcess:
        raise ActionError(f"PID {pid} not found (already exited?)")
    except psutil.AccessDenied:
        raise ActionError(
            f"Permission denied renicing PID {pid}"
            + (" (lowering nice needs sudo)." if value < 0 else ". Try with sudo.")
        )
    return f"Set nice of PID {pid} to {value}."


def copy_to_clipboard(text: str) -> str:
    try:
        import pyperclip
    except ImportError:
        raise ActionError("pyperclip is not installed (pip install pyperclip).")
    try:
        pyperclip.copy(text)
    except Exception as e:
        raise ActionError(f"Failed to copy to clipboard: {e}")
    return f"Copied to clipboard: {text[:60]}{'...' if len(text) > 60 else ''}"


def open_cwd(pid: int) -> str:
    """Reveal the process working directory in Finder (macOS ``open``)."""
    import psutil

    try:
        cwd = psutil.Process(pid).cwd()
    except psutil.NoSuchProcess:
        raise ActionError(f"PID {pid} not found (already exited?)")
    except (psutil.AccessDenied, OSError):
        raise ActionError(f"Cannot read cwd of PID {pid} (permission denied).")
    if not cwd:
        raise ActionError(f"PID {pid} has no readable cwd.")
    try:
        subprocess.run(["open", cwd], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as e:
        raise ActionError(f"Failed to open {cwd}: {e}")
    return f"Opened {cwd}"


def sample(pid: int, seconds: int = 3) -> str:
    """Profile a process with macOS ``sample`` and return the report text."""
    import shutil
    import tempfile

    if shutil.which("sample") is None:
        raise ActionError("The macOS `sample` tool is not available on this system.")

    with tempfile.NamedTemporaryFile(mode="r", suffix=".sample.txt", delete=False) as tmp:
        path = tmp.name
    try:
        proc = subprocess.run(
            ["sample", str(pid), str(seconds), "-file", path],
            capture_output=True, text=True, timeout=seconds + 30,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise ActionError(f"sample failed: {detail or f'exit code {proc.returncode}'}")
        with open(path) as f:
            return f.read()
    except subprocess.TimeoutExpired:
        raise ActionError(f"sample timed out profiling PID {pid}.")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def kill_by_port(port: int, force: bool = False) -> str:
    """Kill every process listening on ``port``."""
    try:
        out = subprocess.run(
            ["lsof", "-t", "-i", f":{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise ActionError(f"lsof failed: {e}")

    pids = [int(p) for p in out.split() if p.isdigit()]
    if not pids:
        raise ActionError(f"No process is listening on port {port}.")

    messages = [terminate(pid, force=force) for pid in pids]
    return " ".join(messages)
