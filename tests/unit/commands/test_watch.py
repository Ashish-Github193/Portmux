"""Tests for watch command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.watch import watch
from portmux.core.output import Output
from portmux.models import PortmuxConfig


class TestWatchCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.watch.load_config")
    def test_watch_no_session(self, mock_load_config, mock_session_exists):
        mock_session_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()

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
        assert "not active" in result.output

    @patch("portmux.commands.watch.asyncio")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.watch.load_config")
    def test_watch_starts_monitor(
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
        mock_asyncio.run.assert_called_once()

    @patch("portmux.commands.watch.asyncio")
    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.watch.load_config")
    def test_watch_with_custom_interval(
        self, mock_load_config, mock_session_exists, mock_asyncio
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_asyncio.run.return_value = None

        result = self.runner.invoke(
            watch,
            ["--interval", "5"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Watching tunnels every 5.0s" in result.output
