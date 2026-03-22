"""Tests for monitor command group (start/stop/status)."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.monitor import monitor
from portmux.core.output import Output
from portmux.core.service import MONITOR_WINDOW
from portmux.models import PortmuxConfig


class TestMonitorStart:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.windows.create_window")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_start_creates_monitor_window(
        self, mock_load_config, mock_session_exists, mock_win_exists, mock_create
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

    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_start_already_running(
        self, mock_load_config, mock_session_exists, mock_win_exists
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

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_start_no_session(self, mock_load_config, mock_session_exists):
        mock_session_exists.return_value = False
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
        assert "not active" in result.output


class TestMonitorStop:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.windows.kill_window")
    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_stop_kills_monitor(
        self, mock_load_config, mock_session_exists, mock_win_exists, mock_kill
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = True
        mock_kill.return_value = True
        mock_load_config.return_value = PortmuxConfig()

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

    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_stop_not_running(
        self, mock_load_config, mock_session_exists, mock_win_exists
    ):
        mock_session_exists.return_value = True
        mock_win_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()

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

    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_status_running(
        self, mock_load_config, mock_session_exists, mock_win_exists
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
        assert "health.log" in result.output

    @patch("portmux.tmux.windows.window_exists")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_status_not_running(
        self, mock_load_config, mock_session_exists, mock_win_exists
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

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.monitor.load_config")
    def test_status_no_session(self, mock_load_config, mock_session_exists):
        mock_session_exists.return_value = False
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
        assert "not active" in result.output
