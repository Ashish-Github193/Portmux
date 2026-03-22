"""E2E tests for tmux session lifecycle."""

from __future__ import annotations

import subprocess

import pytest

from portmux.backend import TmuxBackend
from portmux.core.output import Output
from portmux.core.service import MONITOR_WINDOW, PortmuxService
from portmux.models import MonitorConfig, PortmuxConfig

pytestmark = pytest.mark.e2e


class TestSessionLifecycle:
    """Session init / destroy with real tmux."""

    def test_init_creates_session(self, portmux_service, session_name):
        portmux_service.initialize(run_startup=False)

        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_init_idempotent_without_force(self, portmux_service, session_name):
        assert portmux_service.initialize(run_startup=False) is True
        assert portmux_service.initialize(run_startup=False) is True

        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_init_force_recreates_session(
        self, portmux_service, session_name, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        # Add a forward so we can verify it's gone after force-recreate
        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        portmux_service.add_forward("L", spec, ssh_target)
        assert len(portmux_service.list_forwards()) == 1

        # Force-recreate
        portmux_service.initialize(force=True, run_startup=False)
        assert len(portmux_service.list_forwards()) == 0

    def test_destroy_session(self, portmux_service, session_name):
        portmux_service.initialize(run_startup=False)
        portmux_service.destroy_session()

        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        assert result.returncode != 0

    def test_session_name_isolation(self, tmp_path, tcp_server, ssh_target, free_port):
        """Two sessions with different names don't see each other's forwards."""
        sessions = []

        try:
            for i in range(2):
                import uuid

                name = f"e2e-iso-{uuid.uuid4().hex[:8]}"
                sessions.append(name)
                config = PortmuxConfig(
                    session_name=name,
                    default_identity="/root/.ssh/id_ed25519",
                    monitor=MonitorConfig(enabled=False),
                )
                svc = PortmuxService(config, Output(), name)
                svc.initialize(run_startup=False)

                port = free_port()
                svc.add_forward("L", f"{port}:localhost:{tcp_server}", ssh_target)

            # Each session should see exactly 1 forward
            for name in sessions:
                config = PortmuxConfig(
                    session_name=name,
                    monitor=MonitorConfig(enabled=False),
                )
                svc = PortmuxService(config, Output(), name)
                assert len(svc.list_forwards()) == 1
        finally:
            for name in sessions:
                subprocess.run(
                    ["tmux", "kill-session", "-t", name],
                    capture_output=True,
                )

    def test_init_monitor_disabled(self, portmux_service, session_name, backend):
        portmux_service.initialize(run_startup=False)

        assert not backend.tunnel_exists(MONITOR_WINDOW, session_name)

    def test_init_monitor_enabled(self, session_name, tmp_path):
        """When monitor.enabled=True, _monitor window is created."""
        config = PortmuxConfig(
            session_name=session_name,
            default_identity="/root/.ssh/id_ed25519",
            monitor=MonitorConfig(enabled=True),
        )
        svc = PortmuxService(config, Output(), session_name)
        svc.initialize(run_startup=False)

        backend = TmuxBackend()
        assert backend.tunnel_exists(MONITOR_WINDOW, session_name)
