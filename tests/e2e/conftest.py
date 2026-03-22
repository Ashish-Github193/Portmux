"""E2E test fixtures — real tmux, real SSH, real TCP."""

from __future__ import annotations

import socket
import socketserver
import subprocess
import threading
import time
import uuid

import pytest

from portmux.backend import TmuxBackend
from portmux.core.output import Output
from portmux.core.service import PortmuxService
from portmux.health.logger import HealthLogger
from portmux.models import MonitorConfig, PortmuxConfig

# ---------------------------------------------------------------------------
# Polling helpers
# ---------------------------------------------------------------------------


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 10.0) -> None:
    """Poll until a TCP port is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"Port {port} not open after {timeout}s")


def wait_for_condition(
    predicate,
    timeout: float = 10.0,
    interval: float = 0.3,
    desc: str = "condition",
):
    """Poll until predicate() returns truthy."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(f"{desc} not met after {timeout}s")


# ---------------------------------------------------------------------------
# TCP echo server
# ---------------------------------------------------------------------------


class _EchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(4096)
        if data:
            self.request.sendall(data)


class _ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_name():
    """Unique tmux session name. Teardown kills the session."""
    name = f"e2e-{uuid.uuid4().hex[:8]}"
    yield name
    subprocess.run(
        ["tmux", "kill-session", "-t", name],
        capture_output=True,
    )


@pytest.fixture()
def backend():
    """Real TmuxBackend — no mocks."""
    return TmuxBackend()


@pytest.fixture()
def portmux_service(session_name, tmp_path):
    """PortmuxService wired to a unique session with monitor disabled."""
    config = PortmuxConfig(
        session_name=session_name,
        default_identity="/root/.ssh/id_ed25519",
        monitor=MonitorConfig(enabled=False),
    )
    logger = HealthLogger(log_path=tmp_path / "health.log")
    svc = PortmuxService(config, Output(), session_name)
    svc.logger = logger
    return svc


@pytest.fixture()
def monitored_service(session_name, tmp_path):
    """PortmuxService with monitor enabled and short intervals."""
    config = PortmuxConfig(
        session_name=session_name,
        default_identity="/root/.ssh/id_ed25519",
        max_retries=3,
        reconnect_delay=1,
        monitor=MonitorConfig(
            enabled=True,
            check_interval=2.0,
            tcp_timeout=2.0,
            auto_reconnect=True,
        ),
    )
    logger = HealthLogger(log_path=tmp_path / "health.log")
    svc = PortmuxService(config, Output(), session_name)
    svc.logger = logger
    return svc


@pytest.fixture()
def free_port():
    """Factory that returns an unused ephemeral port."""

    def _find():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    return _find


@pytest.fixture()
def tcp_server():
    """TCP echo server on a dynamic port. Yields the port number."""
    server = _ReusableTCPServer(("127.0.0.1", 0), _EchoHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@pytest.fixture()
def ssh_target():
    """SSH target for loopback connection."""
    return "root@localhost"


@pytest.fixture()
def ssh_identity():
    """Path to the test SSH identity file."""
    return "/root/.ssh/id_ed25519"


@pytest.fixture()
def remain_on_exit():
    """Set remain-on-exit globally so panes stay after process exits.

    Call the returned function after initialize() but before creating forwards.
    Cleans up the global option on teardown.
    """

    def _enable():
        subprocess.run(
            ["tmux", "set-option", "-g", "remain-on-exit", "on"],
            capture_output=True,
        )

    yield _enable
    subprocess.run(
        ["tmux", "set-option", "-g", "-u", "remain-on-exit"],
        capture_output=True,
    )
