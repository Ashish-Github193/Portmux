"""Tests for health checker."""

import asyncio
from unittest.mock import Mock, patch

from portmux.backend import TmuxBackend
from portmux.health.checker import HealthChecker
from portmux.health.state import TunnelHealth
from portmux.models import ForwardInfo, TunnelDiagnostics


def _make_forward(name="L:8080:localhost:80", direction="L", spec="8080:localhost:80"):
    return ForwardInfo(name=name, direction=direction, spec=spec, status="", command="")


def _make_diag(
    command="ssh",
    dead=False,
    dead_status=None,
    content=None,
    pid=12345,
):
    return TunnelDiagnostics(
        pane_pid=pid,
        pane_current_command=command,
        pane_dead=dead,
        pane_dead_status=dead_status,
        pane_content=content or [],
    )


class TestCheckProcess:
    def test_alive_ssh(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(command="ssh")
        assert checker._check_process(diag) is True

    def test_dead_pane(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(dead=True, dead_status="255")
        assert checker._check_process(diag) is False

    def test_non_ssh_command(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(command="bash")
        assert checker._check_process(diag) is False


class TestCheckPaneOutput:
    def test_no_errors(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(content=["Last login: Mon Mar 21", ""])
        assert checker._check_pane_output(diag) is None

    def test_passphrase_prompt(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(
            content=["Enter passphrase for key '/home/user/.ssh/id_rsa':"]
        )
        assert checker._check_pane_output(diag) == "Enter passphrase"

    def test_permission_denied(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(content=["Permission denied (publickey)."])
        assert checker._check_pane_output(diag) == "Permission denied"

    def test_connection_refused(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(content=["ssh: connect to host: Connection refused"])
        assert checker._check_pane_output(diag) == "Connection refused"

    def test_host_key_verification(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(content=["Host key verification failed."])
        assert checker._check_pane_output(diag) == "Host key verification failed"


class TestEvaluate:
    def test_dead_process(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(dead=True, dead_status="255")
        health, detail = checker._evaluate(False, None, None, diag, "L")
        assert health == TunnelHealth.DEAD
        assert "exit: 255" in detail

    def test_dead_process_no_exit_code(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag(dead=True)
        health, detail = checker._evaluate(False, None, None, diag, "L")
        assert health == TunnelHealth.DEAD
        assert "SSH process not running" in detail

    def test_pane_error(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag()
        health, detail = checker._evaluate(True, "Enter passphrase", False, diag, "L")
        assert health == TunnelHealth.UNHEALTHY
        assert "Enter passphrase" in detail

    def test_local_forward_healthy(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag()
        health, detail = checker._evaluate(True, None, True, diag, "L")
        assert health == TunnelHealth.HEALTHY

    def test_local_forward_port_closed(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag()
        health, detail = checker._evaluate(True, None, False, diag, "L")
        assert health == TunnelHealth.UNHEALTHY
        assert "port not responding" in detail

    def test_remote_forward_healthy(self):
        checker = HealthChecker(Mock(spec=TmuxBackend), "portmux")
        diag = _make_diag()
        health, detail = checker._evaluate(True, None, None, diag, "R")
        assert health == TunnelHealth.HEALTHY


class TestCheckOne:
    def test_tunnel_not_found(self):
        backend = Mock(spec=TmuxBackend)
        backend.get_tunnel_diagnostics.return_value = None
        checker = HealthChecker(backend, "portmux")

        result = asyncio.run(checker.check_one(_make_forward()))

        assert result.health == TunnelHealth.DEAD
        assert result.process_alive is False

    @patch("portmux.health.checker.HealthChecker._probe_port")
    def test_healthy_local_forward(self, mock_probe):
        mock_probe.return_value = True

        async def async_probe(*args, **kwargs):
            return True

        mock_probe.side_effect = async_probe

        backend = Mock(spec=TmuxBackend)
        backend.get_tunnel_diagnostics.return_value = _make_diag()
        checker = HealthChecker(backend, "portmux")

        result = asyncio.run(checker.check_one(_make_forward()))

        assert result.health == TunnelHealth.HEALTHY
        assert result.process_alive is True
        assert result.port_open is True

    def test_remote_forward_skips_tcp_probe(self):
        backend = Mock(spec=TmuxBackend)
        backend.get_tunnel_diagnostics.return_value = _make_diag()
        checker = HealthChecker(backend, "portmux")

        forward = _make_forward(
            name="R:9000:localhost:9000", direction="R", spec="9000:localhost:9000"
        )
        result = asyncio.run(checker.check_one(forward))

        assert result.health == TunnelHealth.HEALTHY
        assert result.port_open is None


class TestCheckAll:
    @patch("portmux.health.checker.HealthChecker._probe_port")
    def test_check_multiple_forwards(self, mock_probe):
        async def async_probe(*args, **kwargs):
            return True

        mock_probe.side_effect = async_probe

        backend = Mock(spec=TmuxBackend)
        backend.get_tunnel_diagnostics.return_value = _make_diag()
        checker = HealthChecker(backend, "portmux")

        forwards = [
            _make_forward("L:8080:localhost:80", "L", "8080:localhost:80"),
            _make_forward("L:5432:db:5432", "L", "5432:db:5432"),
        ]
        results = asyncio.run(checker.check_all(forwards))

        assert len(results) == 2
        assert all(r.health == TunnelHealth.HEALTHY for r in results)

    def test_check_empty_list(self):
        backend = Mock(spec=TmuxBackend)
        checker = HealthChecker(backend, "portmux")

        results = asyncio.run(checker.check_all([]))

        assert results == []
