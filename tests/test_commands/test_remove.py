"""Tests for remove command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.remove import remove
from portmux.models import ForwardInfo, PortmuxConfig
from portmux.output import Output


class TestRemoveCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
    @patch("portmux.service._remove_forward")
    @patch("portmux.commands.remove.load_config")
    def test_remove_single_forward_success(
        self,
        mock_load_config,
        mock_remove_forward,
        mock_list_forwards,
        mock_session_exists,
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="ssh",
            )
        ]
        mock_remove_forward.return_value = True

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Successfully removed forward" in result.output
        mock_remove_forward.assert_called_once()
        assert mock_remove_forward.call_args.args == ("L:8080:localhost:80", "portmux")

    @patch("portmux.session.session_exists")
    @patch("portmux.commands.remove.load_config")
    def test_remove_no_session(self, mock_load_config, mock_session_exists):
        mock_session_exists.return_value = False
        mock_load_config.return_value = PortmuxConfig()

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "not active" in result.output
        assert "Nothing to remove" in result.output

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
    @patch("portmux.commands.remove.load_config")
    def test_remove_forward_not_found(
        self, mock_load_config, mock_list_forwards, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = []

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "not found" in result.output
        assert "portmux list" in result.output

    @patch("portmux.session.session_exists")
    @patch("portmux.service._list_forwards")
    @patch("portmux.service._remove_forward")
    @patch("portmux.commands.remove.confirm_destructive_action")
    @patch("portmux.commands.remove.load_config")
    def test_remove_all_with_confirmation(
        self,
        mock_load_config,
        mock_confirm,
        mock_remove_forward,
        mock_list_forwards,
        mock_session_exists,
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_list_forwards.return_value = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="",
                command="ssh",
            ),
            ForwardInfo(
                name="R:9000:localhost:9000",
                direction="R",
                spec="9000:localhost:9000",
                status="",
                command="ssh",
            ),
        ]
        mock_confirm.return_value = True
        mock_remove_forward.return_value = True

        result = self.runner.invoke(
            remove,
            ["--all"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "Successfully removed 2 forward(s)" in result.output
        assert mock_remove_forward.call_count == 2

    @patch("portmux.session.session_exists")
    @patch("portmux.session.kill_session")
    @patch("portmux.commands.remove.confirm_destructive_action")
    @patch("portmux.commands.remove.load_config")
    def test_destroy_session_with_confirmation(
        self, mock_load_config, mock_confirm, mock_kill_session, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = PortmuxConfig()
        mock_confirm.return_value = True
        mock_kill_session.return_value = True

        result = self.runner.invoke(
            remove,
            ["--destroy-session"],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code == 0
        assert "destroyed successfully" in result.output
        mock_kill_session.assert_called_once_with("portmux")

    def test_remove_no_arguments(self):
        result = self.runner.invoke(
            remove,
            [],
            obj={
                "session": "portmux",
                "config": None,
                "verbose": False,
                "output": Output(),
            },
        )

        assert result.exit_code != 0
        assert "Must specify forward name or use --all flag" in result.output
