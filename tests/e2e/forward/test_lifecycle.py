"""E2E tests for SSH forward lifecycle — real tunnels, real traffic."""

from __future__ import annotations

import socket

import pytest

from portmux.core.output import Output
from portmux.core.service import MONITOR_WINDOW, PortmuxService
from portmux.exceptions import SSHError
from portmux.models import MonitorConfig, PortmuxConfig
from tests.e2e.conftest import wait_for_port

pytestmark = pytest.mark.e2e


def _send_through_tunnel(port: int, payload: bytes = b"hello portmux") -> bytes:
    """Send data through a forwarded port and return the response."""
    with socket.create_connection(("127.0.0.1", port), timeout=5.0) as sock:
        sock.sendall(payload)
        return sock.recv(4096)


class TestForwardLifecycle:
    """Add / list / remove / refresh forwards with real SSH."""

    def test_add_local_forward(
        self, portmux_service, session_name, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        window_name = portmux_service.add_forward("L", spec, ssh_target)

        assert window_name == f"L:{spec}"
        wait_for_port(local_port)

        # Verify traffic flows
        resp = _send_through_tunnel(local_port)
        assert resp == b"hello portmux"

    def test_add_remote_forward(
        self, portmux_service, session_name, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        remote_port = free_port()
        spec = f"{remote_port}:localhost:{tcp_server}"
        window_name = portmux_service.add_forward("R", spec, ssh_target)

        assert window_name == f"R:{spec}"

        # For a remote forward to localhost, the remote side listens on the port.
        # Since we SSH to localhost, the remote port is also on localhost.
        wait_for_port(remote_port)
        resp = _send_through_tunnel(remote_port)
        assert resp == b"hello portmux"

    def test_add_forward_with_explicit_identity(
        self, portmux_service, tcp_server, ssh_target, ssh_identity, free_port
    ):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        portmux_service.add_forward("L", spec, ssh_target, identity=ssh_identity)

        wait_for_port(local_port)
        resp = _send_through_tunnel(local_port)
        assert resp == b"hello portmux"

    def test_list_forwards_shows_active(
        self, portmux_service, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        ports = [free_port(), free_port()]
        for p in ports:
            portmux_service.add_forward("L", f"{p}:localhost:{tcp_server}", ssh_target)

        forwards = portmux_service.list_forwards()
        assert len(forwards) == 2
        names = {f.name for f in forwards}
        for p in ports:
            assert f"L:{p}:localhost:{tcp_server}" in names

        # All should have non-empty commands starting with "ssh"
        for f in forwards:
            assert f.command.startswith("ssh")
            assert f.direction == "L"

    def test_list_forwards_excludes_monitor_window(
        self, session_name, tmp_path, tcp_server, ssh_target, free_port
    ):
        config = PortmuxConfig(
            session_name=session_name,
            default_identity="/root/.ssh/id_ed25519",
            monitor=MonitorConfig(enabled=True),
        )
        svc = PortmuxService(config, Output(), session_name)
        svc.initialize(run_startup=False)

        local_port = free_port()
        svc.add_forward("L", f"{local_port}:localhost:{tcp_server}", ssh_target)

        forwards = svc.list_forwards()
        forward_names = [f.name for f in forwards]
        assert MONITOR_WINDOW not in forward_names
        assert len(forwards) == 1

    def test_remove_forward(self, portmux_service, tcp_server, ssh_target, free_port):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        name = portmux_service.add_forward("L", spec, ssh_target)

        portmux_service.remove_forward(name)
        assert len(portmux_service.list_forwards()) == 0

    def test_remove_all_forwards(
        self, portmux_service, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        for _ in range(3):
            port = free_port()
            portmux_service.add_forward(
                "L", f"{port}:localhost:{tcp_server}", ssh_target
            )

        assert len(portmux_service.list_forwards()) == 3
        removed = portmux_service.remove_all_forwards()
        assert removed == 3
        assert len(portmux_service.list_forwards()) == 0

    def test_refresh_forward(self, portmux_service, tcp_server, ssh_target, free_port):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        name = portmux_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)
        assert _send_through_tunnel(local_port) == b"hello portmux"

        # Refresh — kills and recreates the tunnel
        portmux_service.refresh_forward(name)
        wait_for_port(local_port)
        assert _send_through_tunnel(local_port) == b"hello portmux"

    def test_refresh_all(self, portmux_service, tcp_server, ssh_target, free_port):
        portmux_service.initialize(run_startup=False)

        ports = [free_port(), free_port()]
        for p in ports:
            portmux_service.add_forward("L", f"{p}:localhost:{tcp_server}", ssh_target)
        for p in ports:
            wait_for_port(p)

        portmux_service.refresh_all(delay=0.5)

        for p in ports:
            wait_for_port(p)
            assert _send_through_tunnel(p) == b"hello portmux"

    def test_add_duplicate_forward_fails(
        self, portmux_service, tcp_server, ssh_target, free_port
    ):
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        portmux_service.add_forward("L", spec, ssh_target)

        with pytest.raises(SSHError, match="already exists"):
            portmux_service.add_forward("L", spec, ssh_target)

    def test_traffic_flow_proof(
        self, portmux_service, tcp_server, ssh_target, free_port
    ):
        """Definitive test: send multiple payloads through the tunnel."""
        portmux_service.initialize(run_startup=False)

        local_port = free_port()
        spec = f"{local_port}:localhost:{tcp_server}"
        portmux_service.add_forward("L", spec, ssh_target)
        wait_for_port(local_port)

        payloads = [b"packet-1", b"packet-2", b"large-" + b"x" * 4000]
        for payload in payloads:
            resp = _send_through_tunnel(local_port, payload)
            assert resp == payload
