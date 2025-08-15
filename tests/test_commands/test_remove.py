"""Tests for remove command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.remove import remove


class TestRemoveCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.remove.session_exists")
    @patch("portmux.commands.remove.list_forwards")
    @patch("portmux.commands.remove.remove_forward")
    def test_remove_single_forward_success(
        self, mock_remove_forward, mock_list_forwards, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
            }
        ]
        mock_remove_forward.return_value = True

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "Successfully removed forward" in result.output
        mock_remove_forward.assert_called_once_with("L:8080:localhost:80", "portmux")

    @patch("portmux.commands.remove.session_exists")
    def test_remove_no_session(self, mock_session_exists):
        mock_session_exists.return_value = False

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "not active" in result.output
        assert "Nothing to remove" in result.output

    @patch("portmux.commands.remove.session_exists")
    @patch("portmux.commands.remove.list_forwards")
    def test_remove_forward_not_found(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = []

        result = self.runner.invoke(
            remove,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "not found" in result.output
        assert "portmux list" in result.output

    @patch("portmux.commands.remove.session_exists")
    @patch("portmux.commands.remove.list_forwards")
    @patch("portmux.commands.remove.remove_forward")
    @patch("portmux.commands.remove.confirm_destructive_action")
    def test_remove_all_with_confirmation(
        self, mock_confirm, mock_remove_forward, mock_list_forwards, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
            },
            {
                "name": "R:9000:localhost:9000",
                "direction": "R",
                "spec": "9000:localhost:9000",
            },
        ]
        mock_confirm.return_value = True
        mock_remove_forward.return_value = True

        result = self.runner.invoke(
            remove,
            ["--all"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "Successfully removed 2 forward(s)" in result.output
        assert mock_remove_forward.call_count == 2

    @patch("portmux.commands.remove.session_exists")
    @patch("portmux.commands.remove.kill_session")
    @patch("portmux.commands.remove.confirm_destructive_action")
    def test_destroy_session_with_confirmation(
        self, mock_confirm, mock_kill_session, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_confirm.return_value = True
        mock_kill_session.return_value = True

        result = self.runner.invoke(
            remove,
            ["--destroy-session"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "destroyed successfully" in result.output
        mock_kill_session.assert_called_once_with("portmux")

    def test_remove_no_arguments(self):
        result = self.runner.invoke(
            remove, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code != 0
        assert "Must specify forward name or use --all flag" in result.output
