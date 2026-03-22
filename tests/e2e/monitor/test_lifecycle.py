"""E2E tests for background monitor daemon and auto-restart."""

from __future__ import annotations

import asyncio
import os
import signal

import pytest

from portmux.core.service import MONITOR_WINDOW
from portmux.health.logger import HealthLogger
from portmux.health.monitor import TunnelMonitor
from portmux.health.state import TunnelHealth
from tests.e2e.conftest import wait_for_condition, wait_for_port

pytestmark = pytest.mark.e2e


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _wait_for_death(backend, name, session_name, timeout=10.0):
    """Wait for a tunnel to die (pane dead or window gone)."""

    def _is_dead():
        d = backend.get_tunnel_diagnostics(name, session_name)
        return d is None or d.pane_dead

    wait_for_condition(_is_dead, timeout=timeout, desc="SSH death")


class TestMonitorLifecycle:
    """Background monitor start/stop and auto-restart."""

    def test_start_background_monitor(self, monitored_service, backend):
        monitored_service.config.monitor.enabled = False
        monitored_service.initialize(run_startup=False)

        result = monitored_service.start_background_monitor()
        assert result is True
        assert backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)

    def test_stop_background_monitor(self, monitored_service, backend):
        monitored_service.config.monitor.enabled = False
        monitored_service.initialize(run_startup=False)
        monitored_service.start_background_monitor()

        assert backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)

        backend.kill_tunnel(MONITOR_WINDOW, monitored_service.session_name)
        assert not backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)

    def test_monitor_auto_restart_dead_tunnel(
        self,
        monitored_service,
        tcp_server,
        ssh_target,
        free_port,
        backend,
        tmp_path,
        remain_on_exit,
    ):
        """Kill SSH, monitor detects death and restarts the tunnel."""
        monitored_service.initialize(run_startup=False)
        remain_on_exit()

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        name = monitored_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        # Get PID and kill SSH
        diag = backend.get_tunnel_diagnostics(name, monitored_service.session_name)
        assert diag is not None
        os.kill(diag.pane_pid, signal.SIGKILL)
        _wait_for_death(backend, name, monitored_service.session_name)

        # Run monitor cycle — should detect death and restart
        logger = HealthLogger(log_path=tmp_path / "monitor.log")
        monitor = TunnelMonitor(
            backend=backend,
            config=monitored_service.config,
            output=monitored_service.output,
            session_name=monitored_service.session_name,
            logger=logger,
        )
        _run_async(monitor.run_once())

        # The monitor should have restarted the tunnel. Wait for it.
        wait_for_port(local_port, timeout=15.0)

        # Verify the tunnel is back and healthy
        results = _run_async(monitor.run_once())
        healthy = [r for r in results if r.health == TunnelHealth.HEALTHY]
        assert len(healthy) >= 1

    def test_monitor_gives_up_after_max_retries(
        self,
        session_name,
        tcp_server,
        ssh_target,
        free_port,
        backend,
        tmp_path,
        remain_on_exit,
    ):
        """Monitor gives up after max_retries exhausted."""
        from portmux.core.output import Output
        from portmux.core.service import PortmuxService
        from portmux.models import MonitorConfig, PortmuxConfig

        config = PortmuxConfig(
            session_name=session_name,
            default_identity="/root/.ssh/id_ed25519",
            max_retries=1,
            reconnect_delay=0.5,
            monitor=MonitorConfig(
                enabled=False,
                check_interval=1.0,
                tcp_timeout=2.0,
                auto_reconnect=True,
            ),
        )
        svc = PortmuxService(config, Output(), session_name)
        svc.initialize(run_startup=False)
        remain_on_exit()

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        name = svc.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        logger = HealthLogger(log_path=tmp_path / "monitor.log")
        monitor = TunnelMonitor(
            backend=backend,
            config=config,
            output=svc.output,
            session_name=session_name,
            logger=logger,
        )

        # Kill SSH process
        diag = backend.get_tunnel_diagnostics(name, session_name)
        os.kill(diag.pane_pid, signal.SIGKILL)
        _wait_for_death(backend, name, session_name)

        # First cycle: detects death, triggers restart (attempt 1/1)
        _run_async(monitor.run_once())

        # Wait for the restart to establish, then kill again
        wait_for_port(local_port, timeout=10.0)
        diag = backend.get_tunnel_diagnostics(name, session_name)
        if diag and diag.pane_pid and not diag.pane_dead:
            os.kill(diag.pane_pid, signal.SIGKILL)
            _wait_for_death(backend, name, session_name)

        # Second cycle: detects death again, should give up (max_retries=1)
        _run_async(monitor.run_once())

        # Read the log — should contain "Max retries" or "gave up"
        logger.flush()
        log_content = (tmp_path / "monitor.log").read_text()
        assert "max retries" in log_content.lower() or "gave up" in log_content.lower()

    def test_monitor_health_logging(
        self,
        monitored_service,
        tcp_server,
        ssh_target,
        free_port,
        backend,
        tmp_path,
    ):
        """Monitor writes health events to the log file."""
        monitored_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        monitored_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        logger = HealthLogger(log_path=tmp_path / "monitor.log")
        monitor = TunnelMonitor(
            backend=backend,
            config=monitored_service.config,
            output=monitored_service.output,
            session_name=monitored_service.session_name,
            logger=logger,
        )

        _run_async(monitor.run_once())
        logger.flush()

        log_path = tmp_path / "monitor.log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "HEARTBEAT" in content

    def test_foreground_watch_single_cycle(
        self,
        monitored_service,
        tcp_server,
        ssh_target,
        free_port,
        backend,
        tmp_path,
    ):
        """run_once() without logger returns results without file logging."""
        monitored_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        monitored_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        monitor = TunnelMonitor(
            backend=backend,
            config=monitored_service.config,
            output=monitored_service.output,
            session_name=monitored_service.session_name,
            logger=None,
        )

        results = _run_async(monitor.run_once())
        assert len(results) == 1
        assert results[0].health == TunnelHealth.HEALTHY

        assert not (tmp_path / "monitor.log").exists()

    def test_monitor_status_reflects_running(self, monitored_service, backend):
        """tunnel_exists('_monitor') reflects monitor running state."""
        monitored_service.config.monitor.enabled = False
        monitored_service.initialize(run_startup=False)

        assert not backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)

        monitored_service.start_background_monitor()
        assert backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)

        backend.kill_tunnel(MONITOR_WINDOW, monitored_service.session_name)
        assert not backend.tunnel_exists(MONITOR_WINDOW, monitored_service.session_name)
