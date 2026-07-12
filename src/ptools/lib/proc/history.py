"""Rolling sample history for the live TUI (per-process and system-wide).

Feeds the CPU sparkline column and the header charts. Bounded deques,
pruned when processes disappear, so memory stays flat over long runs.
"""

from __future__ import annotations

from collections import deque

__version__ = "0.1.0"


class History:
    def __init__(self, maxlen: int = 120):
        self.maxlen = maxlen
        self._proc: dict[int, dict[str, deque]] = {}
        self.system_cpu: deque = deque(maxlen=maxlen)
        self.system_mem: deque = deque(maxlen=maxlen)

    def record(self, rows: list[dict], system: dict | None = None) -> None:
        """Append one sample per process and prune exited PIDs."""
        seen = set()
        for row in rows:
            pid = row["pid"]
            seen.add(pid)
            series = self._proc.get(pid)
            if series is None:
                series = self._proc[pid] = {
                    "cpu": deque(maxlen=self.maxlen),
                    "mem": deque(maxlen=self.maxlen),
                }
            series["cpu"].append(row.get("cpu") or 0.0)
            series["mem"].append(row.get("mem") or 0)

        for gone in set(self._proc) - seen:
            del self._proc[gone]

        if system is not None:
            self.system_cpu.append(system.get("cpu") or 0.0)
            self.system_mem.append(system.get("mem_pct") or 0.0)

    def cpu_series(self, pid: int) -> list[float]:
        series = self._proc.get(pid)
        return list(series["cpu"]) if series else []

    def mem_series(self, pid: int) -> list[float]:
        series = self._proc.get(pid)
        return list(series["mem"]) if series else []
