"""macOS-only process helpers backed by ``libproc`` via ctypes.

psutil does not expose per-process disk I/O on macOS; the kernel does,
through ``proc_pid_rusage``. Reading another user's process requires
elevated privileges - callers get ``None`` for those and should render
a placeholder.
"""

from __future__ import annotations

import ctypes
import sys

__version__ = "0.1.0"

_RUSAGE_INFO_V2 = 2


class _rusage_info_v2(ctypes.Structure):
    _fields_ = [
        ("ri_uuid", ctypes.c_uint8 * 16),
        ("ri_user_time", ctypes.c_uint64),
        ("ri_system_time", ctypes.c_uint64),
        ("ri_pkg_idle_wkups", ctypes.c_uint64),
        ("ri_interrupt_wkups", ctypes.c_uint64),
        ("ri_pageins", ctypes.c_uint64),
        ("ri_wired_size", ctypes.c_uint64),
        ("ri_resident_size", ctypes.c_uint64),
        ("ri_phys_footprint", ctypes.c_uint64),
        ("ri_proc_start_abstime", ctypes.c_uint64),
        ("ri_proc_exit_abstime", ctypes.c_uint64),
        ("ri_child_user_time", ctypes.c_uint64),
        ("ri_child_system_time", ctypes.c_uint64),
        ("ri_child_pkg_idle_wkups", ctypes.c_uint64),
        ("ri_child_interrupt_wkups", ctypes.c_uint64),
        ("ri_child_pageins", ctypes.c_uint64),
        ("ri_child_elapsed_abstime", ctypes.c_uint64),
        ("ri_diskio_bytesread", ctypes.c_uint64),
        ("ri_diskio_byteswritten", ctypes.c_uint64),
    ]


_libproc = None
_libproc_failed = False


def _lib():
    global _libproc, _libproc_failed
    if _libproc is None and not _libproc_failed:
        if sys.platform != "darwin":
            _libproc_failed = True
        else:
            try:
                _libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            except OSError:
                _libproc_failed = True
    return _libproc


def disk_io(pid: int) -> tuple[int, int] | None:
    """Cumulative ``(bytes_read, bytes_written)`` for ``pid``.

    Returns ``None`` off-macOS or when the kernel denies access
    (typically another user's process without sudo).
    """
    lib = _lib()
    if lib is None:
        return None
    info = _rusage_info_v2()
    if lib.proc_pid_rusage(pid, _RUSAGE_INFO_V2, ctypes.byref(info)) != 0:
        return None
    return info.ri_diskio_bytesread, info.ri_diskio_byteswritten
