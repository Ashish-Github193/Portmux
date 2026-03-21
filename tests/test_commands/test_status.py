"""Tests for status command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.status import status
from portmux.core.output import Output
from portmux.models import ForwardInfo, PortmuxConfig


class TestStatusCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.core.service._list_forwards")
    @patch("portmux.commands.status.load_config")
    def test_status_active_session_with_forwards(
        self, mock_load_config, mock_list_forwards, mock_session_exists
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
            ),
            ForwardInfo(
                name="R:9000:localhost:9000",
                direction="R",
                spec="9000:localhost:9000",
                status="",
                command="ssh -N -R 9000:localhost:9000 user@host",
            ),
        ]

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
        assert "L:8080:localhost:80" in result.output
        assert "R:9000:localhost:9000" in result.output

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.core.service._list_forwards")
    @patch("portmux.commands.status.load_config")
    def test_status_active_session_no_forwards(
        self, mock_load_config, mock_list_forwards, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = []

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
        assert "No active forwards" in result.output
        assert "portmux add" in result.output

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.commands.status.load_config")
    def test_status_no_session(self, mock_load_config, mock_session_exists):
        mock_session_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()

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
        assert "not active" in result.output
        assert "portmux init" in result.output
