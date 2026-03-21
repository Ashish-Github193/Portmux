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
from .logger import HealthLogger
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
        logger: HealthLogger | None = None,
    ):
        self.backend = backend
        self.config = config
        self.output = output
        self.session_name = session_name
        self.logger = logger
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
                msg = f"Dead: gave up after {retries} retries"
                self.output.error(f"[{n}] {msg}")
                if self.logger:
                    self.logger.error(msg, tunnel=n)
                vanished_dead.append(n)
                del self._states[n]
                self._retry_counts.pop(n, None)
                continue
            msg = "Vanished: tunnel window disappeared"
            self.output.error(f"[{n}] {msg}")
            if self.logger:
                self.logger.error(msg, tunnel=n)
            await self._maybe_restart(n)

        # Heartbeat summary
        self._print_heartbeat(results, vanished_dead=vanished_dead)

        # Flush buffered log events to disk
        if self.logger:
            self.logger.flush()

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
            msg = f"✓ {healthy}/{total} healthy — {now}"
        else:
            parts = [f"{count} {state}" for state, count in counts.items()]
            msg = f"⚠ {', '.join(parts)} — {now}"
        self.output.dim(msg)
        if self.logger:
            self.logger.heartbeat(msg)

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
            msg = f"Healthy: {result.detail}"
            self.output.success(f"[{result.name}] {msg}")
            if self.logger:
                self.logger.info(msg, tunnel=result.name)
            self._retry_counts.pop(result.name, None)

        elif new == TunnelHealth.UNHEALTHY:
            msg = f"Unhealthy: {result.detail}"
            self.output.warning(f"[{result.name}] {msg}")
            if self.logger:
                self.logger.warning(msg, tunnel=result.name)

        elif new == TunnelHealth.DEAD:
            msg = f"Dead: {result.detail}"
            self.output.error(f"[{result.name}] {msg}")
            if self.logger:
                self.logger.error(msg, tunnel=result.name)
            if self.config.monitor.auto_reconnect:
                await self._maybe_restart(result.name)

    async def _maybe_restart(self, name: str) -> None:
        """Attempt auto-restart if retries remain."""
        retries = self._retry_counts.get(name, 0)
        max_retries = self.config.max_retries

        if retries >= max_retries:
            msg = f"Max retries ({max_retries}) exhausted, giving up"
            self.output.error(f"[{name}] {msg}")
            if self.logger:
                self.logger.error(msg, tunnel=name)
            return

        self._retry_counts[name] = retries + 1
        self._states[name] = TunnelHealth.RESTARTING
        msg = f"Restarting (attempt {retries + 1}/{max_retries})..."
        self.output.info(f"[{name}] {msg}")
        if self.logger:
            self.logger.info(msg, tunnel=name)

        try:
            await asyncio.to_thread(
                _refresh_forward, name, self.session_name, backend=self.backend
            )
            self._states[name] = TunnelHealth.STARTING
            await asyncio.sleep(self.config.reconnect_delay)
        except Exception as e:
            msg = f"Restart failed: {e}"
            self.output.error(f"[{name}] {msg}")
            if self.logger:
                self.logger.error(msg, tunnel=name)
            self._states[name] = TunnelHealth.DEAD
