"""Tests for add command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.add import add
from portmux.core.output import Output
from portmux.exceptions import SSHError
from portmux.models import PortmuxConfig


class TestAddCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.tmux.session.create_session")
    @patch("portmux.core.service._add_forward")
    @patch("portmux.commands.add.load_config")
    @patch("portmux.core.service.get_default_identity")
    def test_add_local_forward_success(
        self,
        mock_get_identity,
        mock_load_config,
        mock_add_forward,
        mock_create_session,
        mock_session_exists,
    ):
        mock_load_config.return_value = PortmuxConfig(default_identity=None)
        mock_get_identity.return_value = "/home/user/.ssh/id_rsa"
        mock_add_forward.return_value = "L:8080:localhost:80"
        mock_session_exists.return_value = True

        result = self.runner.invoke(
            add,
            ["L", "8080:localhost:80", "user@host"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Successfully created local forward" in result.output
        mock_add_forward.assert_called_once()
        call_kwargs = mock_add_forward.call_args.kwargs
        assert call_kwargs["direction"] == "L"
        assert call_kwargs["spec"] == "8080:localhost:80"
        assert call_kwargs["host"] == "user@host"
        assert call_kwargs["identity"] == "/home/user/.ssh/id_rsa"
        assert call_kwargs["session_name"] == "portmux"

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.core.service._add_forward")
    @patch("portmux.commands.add.load_config")
    def test_add_remote_forward_with_identity(
        self, mock_load_config, mock_add_forward, mock_session_exists
    ):
        mock_load_config.return_value = PortmuxConfig(default_identity=None)
        mock_add_forward.return_value = "R:9000:localhost:9000"
        mock_session_exists.return_value = True

        result = self.runner.invoke(
            add,
            ["R", "9000:localhost:9000", "user@host", "-i", "/path/to/key"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        if result.exit_code != 0:
            print(f"Error output: {result.output}")
        assert result.exit_code == 0
        assert "Successfully created remote forward" in result.output
        mock_add_forward.assert_called_once()
        call_kwargs = mock_add_forward.call_args.kwargs
        assert call_kwargs["direction"] == "R"
        assert call_kwargs["spec"] == "9000:localhost:9000"
        assert call_kwargs["host"] == "user@host"
        assert call_kwargs["identity"] == "/path/to/key"
        assert call_kwargs["session_name"] == "portmux"

    def test_add_invalid_direction(self):
        result = self.runner.invoke(
            add,
            ["X", "8080:localhost:80", "user@host"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code != 0
        assert "Invalid direction" in result.output

    def test_add_invalid_port_spec(self):
        result = self.runner.invoke(
            add,
            ["L", "invalid-spec", "user@host"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code != 0
        assert "Invalid port specification" in result.output

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.core.service._add_forward")
    @patch("portmux.commands.add.load_config")
    def test_add_forward_already_exists(
        self, mock_load_config, mock_add_forward, mock_session_exists
    ):
        mock_load_config.return_value = PortmuxConfig(default_identity=None)
        mock_add_forward.side_effect = SSHError(
            "Forward 'L:8080:localhost:80' already exists"
        )
        mock_session_exists.return_value = True

        result = self.runner.invoke(
            add,
            ["L", "8080:localhost:80", "user@host"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code != 0
        assert "already exists" in result.output

    @patch("portmux.tmux.session.session_exists")
    @patch("portmux.core.service._add_forward")
    @patch("portmux.commands.add.load_config")
    @patch("portmux.core.service.get_default_identity")
    def test_add_verbose_output(
        self, mock_get_identity, mock_load_config, mock_add_forward, mock_session_exists
    ):
        mock_load_config.return_value = PortmuxConfig(default_identity="/default/key")
        mock_get_identity.return_value = "/default/key"
        mock_add_forward.return_value = "L:8080:localhost:80"
        mock_session_exists.return_value = True

        result = self.runner.invoke(
            add,
            ["L", "8080:localhost:80", "user@host"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": True,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Creating local forward" in result.output
