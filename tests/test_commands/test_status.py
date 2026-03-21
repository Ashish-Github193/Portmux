"""Tests for status command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.status import status
from portmux.models import ForwardInfo, PortmuxConfig
from portmux.output import Output


class TestStatusCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
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
        assert "is active" in result.output
        assert "2 active forward(s)" in result.output
        assert "Active Forwards:" in result.output
        assert "L:8080:localhost:80" in result.output
        assert "R:9000:localhost:9000" in result.output

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
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
        assert "is active" in result.output
        assert "No active forwards" in result.output
        assert "No forwards to display" in result.output
        assert "portmux add" in result.output

    @patch("portmux.session.session_exists")
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

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
    @patch("portmux.commands.status.load_config")
    def test_status_check_connections_placeholder(
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
            )
        ]

        result = self.runner.invoke(
            status,
            ["--check-connections"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Connection checking not implemented yet" in result.output
