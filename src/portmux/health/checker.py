"""Async health checker for SSH tunnels."""

from __future__ import annotations

import asyncio

from ..backend.protocol import TunnelBackend
from ..models import ForwardInfo, TunnelDiagnostics
from ..ssh.forwards import parse_port_spec
from .state import HealthResult, TunnelHealth

# Patterns indicating SSH authentication or connection problems
_ERROR_PATTERNS = [
    "Enter passphrase",
    "Permission denied",
    "Host key verification failed",
    "Could not resolve hostname",
    "Connection refused",
    "Connection timed out",
    "Network is unreachable",
    "No route to host",
]


class HealthChecker:
    """Checks health of SSH tunnels.

    Runs three checks per tunnel:
    1. Process alive — is the pane's process still running
    2. Pane output — scan for stuck prompts or error messages
    3. TCP port probe — connect to localhost:<local_port> for local forwards
    """

    def __init__(
        self,
        backend: TunnelBackend,
        session_name: str,
        tcp_timeout: float = 2.0,
    ):
        self.backend = backend
        self.session_name = session_name
        self.tcp_timeout = tcp_timeout

    async def check_all(self, forwards: list[ForwardInfo]) -> list[HealthResult]:
        """Check all forwards concurrently."""
        tasks = [self.check_one(f) for f in forwards]
        return await asyncio.gather(*tasks)

    async def check_one(self, forward: ForwardInfo) -> HealthResult:
        """Run all checks for a single forward."""
        diag = await asyncio.to_thread(
            self.backend.get_tunnel_diagnostics,
            forward.name,
            self.session_name,
        )

        if diag is None:
            return HealthResult(
                name=forward.name,
                health=TunnelHealth.DEAD,
                detail="Tunnel window not found",
                process_alive=False,
                port_open=None,
                pane_error=None,
            )

        process_alive = self._check_process(diag)
        pane_error = self._check_pane_output(diag)

        port_open = None
        if forward.direction == "L":
            parsed = parse_port_spec(forward.spec)
            port_open = await self._probe_port(parsed.local_port)

        health, detail = self._evaluate(
            process_alive, pane_error, port_open, diag, forward.direction
        )

        return HealthResult(
            name=forward.name,
            health=health,
            detail=detail,
            process_alive=process_alive,
            port_open=port_open,
            pane_error=pane_error,
        )

    def _check_process(self, diag: TunnelDiagnostics) -> bool:
        """Check if the SSH process is alive."""
        if diag.pane_dead:
            return False
        return diag.pane_current_command == "ssh"

    def _check_pane_output(self, diag: TunnelDiagnostics) -> str | None:
        """Scan pane output for error patterns."""
        content = "\n".join(diag.pane_content).lower()
        for pattern in _ERROR_PATTERNS:
            if pattern.lower() in content:
                return pattern
        return None

    async def _probe_port(self, port: int, host: str = "127.0.0.1") -> bool:
        """TCP connect to verify a local forward is passing traffic."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.tcp_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            return False

    def _evaluate(
        self,
        process_alive: bool,
        pane_error: str | None,
        port_open: bool | None,
        diag: TunnelDiagnostics,
        direction: str,
    ) -> tuple[TunnelHealth, str]:
        """Combine check results into a health verdict."""
        if not process_alive:
            exit_info = (
                f" (exit: {diag.pane_dead_status})" if diag.pane_dead_status else ""
            )
            return TunnelHealth.DEAD, f"SSH process not running{exit_info}"

        if pane_error:
            return TunnelHealth.UNHEALTHY, f"Detected: {pane_error}"

        if direction == "L":
            if port_open:
                return TunnelHealth.HEALTHY, "SSH alive, port accepting connections"
            else:
                return TunnelHealth.UNHEALTHY, "SSH alive but port not responding"

        # Remote forwards — can't TCP probe from this side
        return TunnelHealth.HEALTHY, "SSH process alive, no errors detected"
