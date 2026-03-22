"""Tests for tunnel monitor."""

import asyncio
from unittest.mock import Mock, patch

from portmux.backend import TmuxBackend
from portmux.core.output import Output
from portmux.health.monitor import TunnelMonitor
from portmux.health.state import HealthResult, TunnelHealth
from portmux.models import ForwardInfo, MonitorConfig, PortmuxConfig


def _make_config(**kwargs):
    return PortmuxConfig(
        monitor=MonitorConfig(
            check_interval=kwargs.get("check_interval", 1.0),
            tcp_timeout=kwargs.get("tcp_timeout", 0.5),
            auto_reconnect=kwargs.get("auto_reconnect", True),
        ),
        max_retries=kwargs.get("max_retries", 3),
        reconnect_delay=kwargs.get("reconnect_delay", 0.1),
    )


def _make_result(name, health, detail="test"):
    return HealthResult(
        name=name,
        health=health,
        detail=detail,
        process_alive=health != TunnelHealth.DEAD,
        port_open=None,
        pane_error=None,
    )


class TestMonitorHandleResult:
    def test_transition_to_healthy(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        asyncio.run(monitor._handle_result(result))

        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.HEALTHY

    def test_transition_resets_retry_count(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN
        monitor._retry_counts["L:8080:localhost:80"] = 2

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        asyncio.run(monitor._handle_result(result))

        assert "L:8080:localhost:80" not in monitor._retry_counts

    def test_no_change_does_nothing(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.HEALTHY

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        asyncio.run(monitor._handle_result(result))

        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.HEALTHY

    def test_invalid_transition_ignored(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        # DEAD -> HEALTHY is invalid (must go through STARTING)
        monitor._states["L:8080:localhost:80"] = TunnelHealth.DEAD

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        asyncio.run(monitor._handle_result(result))

        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.DEAD


class TestMonitorMaybeRestart:
    @patch("portmux.health.monitor._refresh_forward")
    def test_restart_increments_retry(self, mock_refresh):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(max_retries=3), Output(), "portmux"
        )

        asyncio.run(monitor._maybe_restart("L:8080:localhost:80"))

        assert monitor._retry_counts["L:8080:localhost:80"] == 1
        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.STARTING
        mock_refresh.assert_called_once()

    @patch("portmux.health.monitor._refresh_forward")
    def test_max_retries_exhausted(self, mock_refresh):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(max_retries=2), Output(), "portmux"
        )
        monitor._retry_counts["L:8080:localhost:80"] = 2

        asyncio.run(monitor._maybe_restart("L:8080:localhost:80"))

        mock_refresh.assert_not_called()

    @patch("portmux.health.monitor._refresh_forward")
    def test_restart_failure_marks_dead(self, mock_refresh):
        mock_refresh.side_effect = Exception("tmux error")
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )

        asyncio.run(monitor._maybe_restart("L:8080:localhost:80"))

        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.DEAD


class TestMonitorCheckCycle:
    @patch("portmux.health.monitor._list_forwards")
    def test_no_forwards_returns_empty(self, mock_list):
        mock_list.return_value = []
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )

        results = asyncio.run(monitor._check_cycle())

        assert results == []

    @patch("portmux.health.checker.HealthChecker.check_all")
    @patch("portmux.health.monitor._refresh_forward")
    @patch("portmux.health.monitor._list_forwards")
    def test_vanished_tunnel_triggers_restart(
        self, mock_list, mock_refresh, mock_check_all
    ):
        # One forward still active, but a previously tracked one vanished
        remaining = ForwardInfo(
            name="L:5432:db:5432",
            direction="L",
            spec="5432:db:5432",
            status="",
            command="",
        )
        mock_list.return_value = [remaining]

        async def fake_check_all(forwards):
            return [_make_result("L:5432:db:5432", TunnelHealth.HEALTHY)]

        mock_check_all.side_effect = fake_check_all

        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.HEALTHY
        monitor._states["L:5432:db:5432"] = TunnelHealth.UNKNOWN

        asyncio.run(monitor._check_cycle())

        # Vanished tunnel should attempt restart
        mock_refresh.assert_called_once()
        assert "L:5432:db:5432" in monitor._states

    @patch("portmux.health.checker.HealthChecker.check_all")
    @patch("portmux.health.monitor._list_forwards")
    def test_vanished_tunnel_no_restart_when_disabled(self, mock_list, mock_check_all):
        mock_list.return_value = []

        async def fake_check_all(forwards):
            return []

        mock_check_all.side_effect = fake_check_all

        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend),
            _make_config(auto_reconnect=False),
            Output(),
            "portmux",
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.HEALTHY

        asyncio.run(monitor._check_cycle())

        # Should be pruned, not restarted
        assert "L:8080:localhost:80" not in monitor._states


class TestMonitorRunOnce:
    @patch("portmux.health.monitor._list_forwards")
    def test_run_once_returns_results(self, mock_list):
        mock_list.return_value = []
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )

        results = asyncio.run(monitor.run_once())

        assert results == []


class TestMonitorAutoRestart:
    def test_auto_reconnect_disabled(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend),
            _make_config(auto_reconnect=False),
            Output(),
            "portmux",
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result("L:8080:localhost:80", TunnelHealth.DEAD, "SSH died")
        asyncio.run(monitor._handle_result(result))

        # Should transition to DEAD but not attempt restart
        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.DEAD
        assert "L:8080:localhost:80" not in monitor._retry_counts
