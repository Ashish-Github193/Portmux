"""E2E tests for health checks against real SSH tunnels."""

from __future__ import annotations

import asyncio
import os
import signal

import pytest

from portmux.health.checker import HealthChecker
from portmux.health.state import TunnelHealth
from tests.e2e.conftest import wait_for_condition, wait_for_port

pytestmark = pytest.mark.e2e


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestHealthChecks:
    """Health checker against real tunnels in various states."""

    def test_healthy_local_forward(
        self, portmux_service, tcp_server, ssh_target, free_port, backend
    ):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        portmux_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 1
        r = results[0]
        assert r.health == TunnelHealth.HEALTHY
        assert r.process_alive is True
        assert r.port_open is True
        assert r.pane_error is None

    def test_healthy_remote_forward(
        self, portmux_service, tcp_server, ssh_target, free_port, backend
    ):
        portmux_service.initialize(run_startup=False)

        remote_port = free_port()
        spec = f"{remote_port}:localhost:{tcp_server}"
        portmux_service.add_forward("R", spec, ssh_target)

        # Wait for the SSH process to establish
        wait_for_port(remote_port)

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 1
        r = results[0]
        assert r.health == TunnelHealth.HEALTHY
        # Remote forwards skip TCP probe
        assert r.port_open is None
        assert r.process_alive is True

    def test_dead_tunnel_ssh_killed(
        self, portmux_service, tcp_server, ssh_target, free_port, backend
    ):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        name = portmux_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        # Get PID and kill the SSH process
        diag = backend.get_tunnel_diagnostics(name, portmux_service.session_name)
        assert diag is not None
        assert diag.pane_pid is not None
        os.kill(diag.pane_pid, signal.SIGKILL)

        # Wait for pane to reflect the death
        def _is_dead():
            d = backend.get_tunnel_diagnostics(name, portmux_service.session_name)
            return d and d.pane_dead

        wait_for_condition(_is_dead, timeout=5.0, desc="SSH process death")

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 1
        assert results[0].health == TunnelHealth.DEAD
        assert results[0].process_alive is False

    def test_unhealthy_port_not_responding(
        self, portmux_service, ssh_target, free_port, backend
    ):
        """Forward to a port where nothing is listening."""
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        dead_port = free_port()  # nothing will listen here
        spec = f"{local_port}:localhost:{dead_port}"
        portmux_service.add_forward("L", spec, ssh_target)

        # Wait for SSH to establish (process alive)
        def _ssh_alive():
            forwards = portmux_service.list_forwards()
            if not forwards:
                return False
            diag = backend.get_tunnel_diagnostics(
                forwards[0].name, portmux_service.session_name
            )
            return diag and diag.pane_current_command == "ssh"

        wait_for_condition(_ssh_alive, timeout=10.0, desc="SSH process start")

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 1
        r = results[0]
        assert r.health == TunnelHealth.UNHEALTHY
        assert r.process_alive is True
        assert r.port_open is False
        assert "port not responding" in r.detail.lower()

    def test_pane_error_detection(self, portmux_service, free_port, backend):
        """Forward to a non-existent host triggers pane error detection."""
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:80"
        # Use a host that will fail DNS resolution
        portmux_service.add_forward("L", spec, "root@nonexistent.invalid")

        # Wait for SSH to fail and pane to show error
        name = f"L:{spec}"

        def _has_error_output():
            diag = backend.get_tunnel_diagnostics(name, portmux_service.session_name)
            if diag is None:
                return False
            content = "\n".join(diag.pane_content).lower()
            return (
                "could not resolve" in content or "name or service not known" in content
            )

        wait_for_condition(_has_error_output, timeout=10.0, desc="SSH error in pane")

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 1
        r = results[0]
        # Could be DEAD (process exited) or UNHEALTHY (error in pane)
        assert r.health in (TunnelHealth.DEAD, TunnelHealth.UNHEALTHY)

    def test_mixed_health_results(
        self, portmux_service, tcp_server, ssh_target, free_port, backend
    ):
        """One healthy + one dead tunnel."""
        portmux_service.initialize(run_startup=False)

        # Healthy tunnel
        healthy_port = free_port()
        portmux_service.add_forward(
            "L", f"{healthy_port}:localhost:{tcp_server}", ssh_target
        )
        wait_for_port(healthy_port)

        # Tunnel that will die (forward to non-existent host)
        dead_port = free_port()
        dead_name = portmux_service.add_forward(
            "L", f"{dead_port}:localhost:80", "root@nonexistent.invalid"
        )

        # Wait for the bad tunnel's SSH to fail
        def _is_dead_or_errored():
            diag = backend.get_tunnel_diagnostics(
                dead_name, portmux_service.session_name
            )
            if diag is None:
                return False
            return (
                diag.pane_dead
                or "could not resolve" in "\n".join(diag.pane_content).lower()
            )

        wait_for_condition(_is_dead_or_errored, timeout=10.0, desc="bad tunnel failure")

        checker = HealthChecker(backend, portmux_service.session_name, tcp_timeout=2.0)
        forwards = portmux_service.list_forwards()
        results = _run_async(checker.check_all(forwards))

        assert len(results) == 2
        healths = {r.name: r.health for r in results}
        healthy_name = f"L:{healthy_port}:localhost:{tcp_server}"
        assert healths[healthy_name] == TunnelHealth.HEALTHY

    def test_diagnostics_capture_pane_content(
        self, portmux_service, free_port, backend
    ):
        """Verify pane_content captures real SSH error text."""
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:80"
        name = portmux_service.add_forward("L", spec, "root@nonexistent.invalid")

        def _has_content():
            diag = backend.get_tunnel_diagnostics(name, portmux_service.session_name)
            if diag is None:
                return False
            return len(diag.pane_content) > 0 and any(
                line.strip() for line in diag.pane_content
            )

        wait_for_condition(_has_content, timeout=10.0, desc="pane content")

        diag = backend.get_tunnel_diagnostics(name, portmux_service.session_name)
        content = "\n".join(diag.pane_content).lower()
        # SSH should have printed some error about the host
        assert (
            "nonexistent" in content or "resolve" in content or "not known" in content
        )
