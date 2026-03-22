"""Tests for background monitor: watch --bg, init auto-start, status log events,
service logging, monitor flush."""

import asyncio
from unittest.mock import Mock, patch

from click.testing import CliRunner

from portmux.backend import TmuxBackend
from portmux.commands.init import init
from portmux.commands.monitor import monitor
from portmux.commands.status import status
from portmux.commands.watch import watch
from portmux.core.output import Output
from portmux.core.service import MONITOR_WINDOW, PortmuxService
from portmux.health.logger import HealthLogger
from portmux.health.monitor import TunnelMonitor
from portmux.health.state import HealthResult, TunnelHealth
from portmux.models import ForwardInfo, MonitorConfig, PortmuxConfig


def _make_config(**kwargs):
    return PortmuxConfig(
        monitor=MonitorConfig(
            enabled=kwargs.get("enabled", True),
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


class TestMonitorWithLogger:
    def test_logger_receives_healthy_transition(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux", logger=logger
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY, "SSH alive")
        asyncio.run(monitor._handle_result(result))
        logger.flush()

        content = log_file.read_text()
        assert "INFO" in content
        assert "Healthy: SSH alive" in content

    def test_logger_receives_dead_transition(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux", logger=logger
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result("L:8080:localhost:80", TunnelHealth.DEAD, "SSH exited")
        asyncio.run(monitor._handle_result(result))
        logger.flush()

        content = log_file.read_text()
        assert "ERROR" in content
        assert "Dead: SSH exited" in content

    def test_logger_receives_unhealthy_transition(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux", logger=logger
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result(
            "L:8080:localhost:80", TunnelHealth.UNHEALTHY, "port closed"
        )
        asyncio.run(monitor._handle_result(result))
        logger.flush()

        content = log_file.read_text()
        assert "WARNING" in content
        assert "Unhealthy: port closed" in content

    def test_logger_receives_heartbeat(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux", logger=logger
        )

        results = [_make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)]
        monitor._print_heartbeat(results)
        logger.flush()

        content = log_file.read_text()
        assert "HEARTBEAT" in content

    @patch("portmux.health.monitor._refresh_forward")
    def test_logger_receives_restart_events(self, mock_refresh, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend),
            _make_config(max_retries=3),
            Output(),
            "portmux",
            logger=logger,
        )

        asyncio.run(monitor._maybe_restart("L:8080:localhost:80"))
        logger.flush()

        content = log_file.read_text()
        assert "Restarting (attempt 1/3)" in content

    @patch("portmux.health.monitor._refresh_forward")
    def test_logger_receives_max_retries(self, mock_refresh, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend),
            _make_config(max_retries=2),
            Output(),
            "portmux",
            logger=logger,
        )
        monitor._retry_counts["L:8080:localhost:80"] = 2

        asyncio.run(monitor._maybe_restart("L:8080:localhost:80"))
        logger.flush()

        content = log_file.read_text()
        assert "Max retries" in content
        assert "ERROR" in content

    def test_no_logger_does_not_crash(self):
        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux"
        )
        monitor._states["L:8080:localhost:80"] = TunnelHealth.UNKNOWN

        result = _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        asyncio.run(monitor._handle_result(result))

        assert monitor._states["L:8080:localhost:80"] == TunnelHealth.HEALTHY


class TestMonitorFlush:
    @patch("portmux.health.checker.HealthChecker.check_all")
    @patch("portmux.health.monitor._list_forwards")
    def test_check_cycle_flushes_logger(self, mock_list, mock_check_all, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)
        forward = ForwardInfo(
            name="L:8080:localhost:80",
            direction="L",
            spec="8080:localhost:80",
            status="",
            command="",
        )
        mock_list.return_value = [forward]

        async def fake_check_all(forwards):
            return [_make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)]

        mock_check_all.side_effect = fake_check_all

        monitor = TunnelMonitor(
            Mock(spec=TmuxBackend), _make_config(), Output(), "portmux", logger=logger
        )

        asyncio.run(monitor._check_cycle())

        # Logger should have been flushed — events on disk
        assert log_file.exists()
        content = log_file.read_text()
        assert "HEARTBEAT" in content


class TestServiceLogging:
    def _make_service(self, tmp_path, **config_kwargs):
        log_file = tmp_path / "health.log"
        config = _make_config(enabled=False, **config_kwargs)
        backend = Mock(spec=TmuxBackend)
        backend.session_exists.return_value = True
        backend.tunnel_exists.return_value = False
        backend.create_session.return_value = True
        backend.create_tunnel.return_value = True
        svc = PortmuxService(config, Output(), "portmux", backend=backend)
        svc.logger = HealthLogger(log_path=log_file)
        return svc, log_file

    @patch("portmux.core.service._add_forward")
    def test_add_forward_logs(self, mock_add, tmp_path):
        mock_add.return_value = "L:8080:localhost:80"
        svc, log_file = self._make_service(tmp_path)

        svc.add_forward("L", "8080:localhost:80", "user@host")

        content = log_file.read_text()
        assert "Forward created" in content
        assert "L:8080:localhost:80" in content

    @patch("portmux.core.service._remove_forward")
    def test_remove_forward_logs(self, mock_remove, tmp_path):
        svc, log_file = self._make_service(tmp_path)

        svc.remove_forward("L:8080:localhost:80")

        content = log_file.read_text()
        assert "Forward removed" in content
        assert "L:8080:localhost:80" in content

    def test_destroy_session_logs(self, tmp_path):
        svc, log_file = self._make_service(tmp_path)

        svc.destroy_session()

        content = log_file.read_text()
        assert "Session" in content
        assert "destroyed" in content

    @patch("portmux.core.service._refresh_forward")
    def test_refresh_forward_logs(self, mock_refresh, tmp_path):
        svc, log_file = self._make_service(tmp_path)

        svc.refresh_forward("L:8080:localhost:80")

        content = log_file.read_text()
        assert "Forward refreshed" in content
        assert "L:8080:localhost:80" in content

    @patch("portmux.core.service._list_forwards")
    @patch("portmux.core.service._refresh_forward")
    def test_refresh_all_logs(self, mock_refresh, mock_list, tmp_path):
        mock_list.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="",
            )
        ]
        svc, log_file = self._make_service(tmp_path)

        svc.refresh_all()

        content = log_file.read_text()
        assert "All forwards refreshed" in content

    def test_initialize_logs(self, tmp_path):
        svc, log_file = self._make_service(tmp_path)
        svc.backend.session_exists.return_value = False

        svc.initialize()

        content = log_file.read_text()
        assert "initialized" in content

    def test_start_background_monitor_logs(self, tmp_path):
        svc, log_file = self._make_service(tmp_path)

        svc.start_background_monitor()

        content = log_file.read_text()
        assert "Background monitor started" in content

    @patch("portmux.core.service._remove_forward")
    @patch("portmux.core.service._list_forwards")
    def test_remove_all_logs(self, mock_list, mock_remove, tmp_path):
        mock_list.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="",
            )
        ]
        svc, log_file = self._make_service(tmp_path)

        svc.remove_all_forwards()

        content = log_file.read_text()
        assert "Forward removed" in content
        assert "All forwards removed" in content


class TestMonitorStart:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.windows.create_window")
    @patch("portmux.commands.monitor.load_config")
    def test_start_creates_monitor_window(
        self, mock_load_config, mock_create, mock_win_exists, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = False
        mock_create.return_value = True
        mock_load_config.return_value = PortmuxConfig()

        result = self.runner.invoke(
            monitor,
            ["start"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Background health monitor started" in result.output
        mock_create.assert_called_once()
        assert mock_create.call_args[0][0] == MONITOR_WINDOW

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_start_already_running(
        self, mock_load_config, mock_win_exists, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()

        result = self.runner.invoke(
            monitor,
            ["start"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "already running" in result.output


class TestMonitorStop:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.kill_window")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_stop_kills_monitor(
        self, mock_load_config, mock_win_exists, mock_kill, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_win_exists.return_value = True
        mock_kill.return_value = True

        result = self.runner.invoke(
            monitor,
            ["stop"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Background monitor stopped" in result.output
        mock_kill.assert_called_once_with(MONITOR_WINDOW, "portmux")

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_stop_not_running(
        self, mock_load_config, mock_win_exists, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_win_exists.return_value = False

        result = self.runner.invoke(
            monitor,
            ["stop"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "not running" in result.output


class TestMonitorStatus:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_status_running(
        self, mock_load_config, mock_win_exists, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()

        result = self.runner.invoke(
            monitor,
            ["status"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "running" in result.output

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_status_not_running(
        self, mock_load_config, mock_win_exists, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()

        result = self.runner.invoke(
            monitor,
            ["status"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "not running" in result.output


class TestWatchForeground:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.watch.asyncio")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.watch.load_config")
    def test_foreground_watch(
        self, mock_load_config, mock_session_exists, mock_asyncio
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_asyncio.run.return_value = None

        result = self.runner.invoke(
            watch,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Watching tunnels" in result.output


class TestInitWithMonitorEnabled:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.session.create_session")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.windows.create_window")
    @patch("portmux.commands.init.load_config")
    def test_init_starts_monitor_by_default(
        self,
        mock_load_config,
        mock_create_window,
        mock_win_exists,
        mock_create_session,
        mock_session_exists,
    ):
        mock_session_exists.return_value = False
        mock_create_session.return_value = True
        mock_win_exists.return_value = False
        mock_create_window.return_value = True
        mock_load_config.return_value = PortmuxConfig()  # enabled=True by default

        result = self.runner.invoke(
            init,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Background health monitor started" in result.output
        mock_create_window.assert_called_once()
        assert mock_create_window.call_args[0][0] == MONITOR_WINDOW

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.session.create_session")
    @patch("portmux.commands.init.load_config")
    def test_init_skips_monitor_when_disabled(
        self, mock_load_config, mock_create_session, mock_session_exists
    ):
        mock_session_exists.return_value = False
        mock_create_session.return_value = True
        mock_load_config.return_value = PortmuxConfig(
            monitor=MonitorConfig(enabled=False)
        )

        result = self.runner.invoke(
            init,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Background health monitor" not in result.output


class TestStatusWithLogEvents:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.status.HealthLogger")
    @patch("portmux.commands.status.asyncio")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.core.service._list_forwards")
    @patch("portmux.commands.status.load_config")
    def test_status_shows_recent_errors(
        self,
        mock_load_config,
        mock_list_forwards,
        mock_win_exists,
        mock_session_exists,
        mock_asyncio,
        mock_logger_cls,
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="ssh -N -L 8080:localhost:80 user@host",
            )
        ]

        mock_asyncio.run.return_value = [
            _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        ]

        mock_logger = Mock()
        mock_logger.read_recent_errors.return_value = [
            "2026-03-21 14:00:00 ERROR [L:5432:db:5432] Dead: SSH exited"
        ]
        mock_logger_cls.return_value = mock_logger

        result = self.runner.invoke(
            status,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Recent events" in result.output

    @patch("portmux.commands.status.HealthLogger")
    @patch("portmux.commands.status.asyncio")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.core.service._list_forwards")
    @patch("portmux.commands.status.load_config")
    def test_status_shows_monitor_running(
        self,
        mock_load_config,
        mock_list_forwards,
        mock_win_exists,
        mock_session_exists,
        mock_asyncio,
        mock_logger_cls,
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="ssh -N -L 8080:localhost:80 user@host",
            )
        ]

        def win_exists(name, session_name="portmux"):
            return name == MONITOR_WINDOW

        mock_win_exists.side_effect = win_exists

        mock_asyncio.run.return_value = [
            _make_result("L:8080:localhost:80", TunnelHealth.HEALTHY)
        ]
        mock_logger = Mock()
        mock_logger.read_recent_errors.return_value = []
        mock_logger_cls.return_value = mock_logger

        result = self.runner.invoke(
            status,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Monitor: running" in result.output


class TestConfigEnabledField:
    def test_monitor_enabled_default_true(self):
        config = PortmuxConfig()
        assert config.monitor.enabled is True

    def test_monitor_enabled_false(self):
        config = PortmuxConfig(monitor=MonitorConfig(enabled=False))
        assert config.monitor.enabled is False

    def test_config_roundtrip(self, tmp_path):
        from portmux.core.config import load_config, save_config

        config = PortmuxConfig(monitor=MonitorConfig(enabled=True))
        config_path = tmp_path / "config.toml"
        save_config(config, str(config_path))

        loaded = load_config(str(config_path))
        assert loaded.monitor.enabled is True

    def test_config_enabled_validation(self):
        import pytest

        from portmux.core.config import _validate_monitor_config
        from portmux.exceptions import ConfigError

        with pytest.raises(ConfigError, match="'monitor.enabled' must be a boolean"):
            _validate_monitor_config({"enabled": "yes"})
