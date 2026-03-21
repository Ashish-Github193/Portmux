"""Buffered health event logger for PortMUX."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _default_log_path() -> Path:
    return Path.home() / ".portmux" / "health.log"


class HealthLogger:
    """Buffers health events in memory and flushes to disk in batches.

    Log format: YYYY-MM-DD HH:MM:SS LEVEL [tunnel_name] message
    Heartbeat format: YYYY-MM-DD HH:MM:SS HEARTBEAT message

    Events are queued via info/warning/error/heartbeat methods.
    Auto-flushes when buffer reaches buffer_size. Callers should
    call flush() at natural boundaries (end of check cycle, after
    service operations).
    """

    def __init__(self, log_path: Path | None = None, buffer_size: int = 20):
        self.log_path = log_path or _default_log_path()
        self._buffer: list[str] = []
        self._buffer_size = buffer_size

    def _enqueue(self, level: str, message: str, tunnel: str | None = None) -> None:
        """Format and add event to buffer. Auto-flush when full."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if tunnel:
            line = f"{now} {level} [{tunnel}] {message}"
        else:
            line = f"{now} {level} {message}"
        self._buffer.append(line)
        if len(self._buffer) >= self._buffer_size:
            self.flush()

    def info(self, message: str, tunnel: str | None = None) -> None:
        self._enqueue("INFO", message, tunnel)

    def warning(self, message: str, tunnel: str | None = None) -> None:
        self._enqueue("WARNING", message, tunnel)

    def error(self, message: str, tunnel: str | None = None) -> None:
        self._enqueue("ERROR", message, tunnel)

    def heartbeat(self, message: str) -> None:
        self._enqueue("HEARTBEAT", message)

    def flush(self) -> None:
        """Write all buffered events to disk in one operation."""
        if not self._buffer:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write("\n".join(self._buffer) + "\n")
        self._buffer.clear()

    def __del__(self) -> None:
        """Flush remaining events on garbage collection."""
        try:
            self.flush()
        except Exception:  # nosec B110
            pass  # Best-effort on teardown

    def read_tail(self, n: int) -> list[str]:
        """Read the last n lines from the log file."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text().splitlines()
        return lines[-n:] if n < len(lines) else lines

    def read_head(self, n: int) -> list[str]:
        """Read the first n lines from the log file."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text().splitlines()
        return lines[:n]

    def read_recent_errors(self, minutes: int = 10) -> list[str]:
        """Read error/dead events from the last N minutes."""
        if not self.log_path.exists():
            return []
        cutoff = datetime.now()
        lines = self.log_path.read_text().splitlines()
        results = []
        for line in reversed(lines):
            try:
                ts_str = line[:19]
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                diff = (cutoff - ts).total_seconds()
                if diff > minutes * 60:
                    break
                if " ERROR " in line or " Dead" in line or " Vanished" in line:
                    results.append(line)
            except (ValueError, IndexError):
                continue
        results.reverse()
        return results
