"""Continuous tunnel health monitor with auto-restart."""

from __future__ import annotations

import asyncio
from datetime import datetime

from ..backend.protocol import TunnelBackend
from ..core.output import Output
from ..models import PortmuxConfig
from ..ssh.forwards import list_forwards as _list_forwards
from ..ssh.forwards import refresh_forward as _refresh_forward
from .checker import HealthChecker
from .state import HealthResult, TunnelHealth, can_transition


class TunnelMonitor:
    """Continuously monitors tunnel health and auto-restarts failed tunnels.

    Maintains per-tunnel state and retry counts. Runs as an asyncio task.
    """

    def __init__(
        self,
        backend: TunnelBackend,
        config: PortmuxConfig,
        output: Output,
        session_name: str,
    ):
        self.backend = backend
        self.config = config
        self.output = output
        self.session_name = session_name
        self.checker = HealthChecker(
            backend, session_name, tcp_timeout=config.monitor.tcp_timeout
        )

        self._states: dict[str, TunnelHealth] = {}
        self._retry_counts: dict[str, int] = {}
        self._running = False

    async def run(self, interval: float | None = None) -> None:
        """Main monitor loop. Runs until cancelled."""
        interval = interval or self.config.monitor.check_interval
        self._running = True

        try:
            while self._running:
                await self._check_cycle()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self._running = False
            raise

    async def run_once(self) -> list[HealthResult]:
        """Single check cycle — used by on-demand commands."""
        return await self._check_cycle()

    def stop(self) -> None:
        """Signal the monitor to stop after the current cycle."""
        self._running = False

    async def _check_cycle(self) -> list[HealthResult]:
        """One iteration: list tunnels, check health, handle transitions."""
        forwards = await asyncio.to_thread(
            _list_forwards, self.session_name, backend=self.backend
        )

        results = []
        if forwards:
            results = await self.checker.check_all(forwards)
            for result in results:
                await self._handle_result(result)

        # Detect and restart vanished tunnels
        active_names = {f.name for f in forwards}
        gone = [n for n in self._states if n not in active_names]
        vanished_dead: list[str] = []
        for n in gone:
            retries = self._retry_counts.get(n, 0)
            if (
                retries >= self.config.max_retries
                or not self.config.monitor.auto_reconnect
            ):
                self.output.error(f"[{n}] Dead: gave up after {retries} retries")
                vanished_dead.append(n)
                del self._states[n]
                self._retry_counts.pop(n, None)
                continue
            self.output.error(f"[{n}] Vanished: tunnel window disappeared")
            await self._maybe_restart(n)

        # Heartbeat summary
        self._print_heartbeat(results, vanished_dead=vanished_dead)

        return results

    def _print_heartbeat(
        self,
        results: list[HealthResult],
        vanished_dead: list[str] | None = None,
    ) -> None:
        """Print a dim summary line so the user knows the monitor is alive."""
        if not results and not vanished_dead:
            return
        now = datetime.now().strftime("%H:%M:%S")
        counts: dict[str, int] = {}
        for r in results:
            counts[r.health.value] = counts.get(r.health.value, 0) + 1
        if vanished_dead:
            counts["dead"] = counts.get("dead", 0) + len(vanished_dead)
        total = sum(counts.values())
        healthy = counts.get("healthy", 0)
        if healthy == total:
            self.output.dim(f"✓ {healthy}/{total} healthy — {now}")
        else:
            parts = [f"{count} {state}" for state, count in counts.items()]
            self.output.dim(f"⚠ {', '.join(parts)} — {now}")

    async def _handle_result(self, result: HealthResult) -> None:
        """Process a health result and handle state transitions."""
        prev = self._states.get(result.name, TunnelHealth.UNKNOWN)
        new = result.health

        if prev == new:
            return  # No change

        if not can_transition(prev, new):
            return  # Invalid transition, ignore

        self._states[result.name] = new

        if new == TunnelHealth.HEALTHY and prev != TunnelHealth.HEALTHY:
            self.output.success(f"[{result.name}] Healthy: {result.detail}")
            self._retry_counts.pop(result.name, None)

        elif new == TunnelHealth.UNHEALTHY:
            self.output.warning(f"[{result.name}] Unhealthy: {result.detail}")

        elif new == TunnelHealth.DEAD:
            self.output.error(f"[{result.name}] Dead: {result.detail}")
            if self.config.monitor.auto_reconnect:
                await self._maybe_restart(result.name)

    async def _maybe_restart(self, name: str) -> None:
        """Attempt auto-restart if retries remain."""
        retries = self._retry_counts.get(name, 0)
        max_retries = self.config.max_retries

        if retries >= max_retries:
            self.output.error(
                f"[{name}] Max retries ({max_retries}) exhausted, giving up"
            )
            return

        self._retry_counts[name] = retries + 1
        self._states[name] = TunnelHealth.RESTARTING
        self.output.info(
            f"[{name}] Restarting (attempt {retries + 1}/{max_retries})..."
        )

        try:
            await asyncio.to_thread(
                _refresh_forward, name, self.session_name, backend=self.backend
            )
            self._states[name] = TunnelHealth.STARTING
            await asyncio.sleep(self.config.reconnect_delay)
        except Exception as e:
            self.output.error(f"[{name}] Restart failed: {e}")
            self._states[name] = TunnelHealth.DEAD
