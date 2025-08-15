"""Tests for refresh command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.refresh import refresh


class TestRefreshCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.refresh.session_exists")
    @patch("portmux.commands.refresh.list_forwards")
    @patch("portmux.commands.refresh.refresh_forward")
    @patch("portmux.commands.refresh.load_config")
    def test_refresh_single_forward_success(
        self,
        mock_load_config,
        mock_refresh_forward,
        mock_list_forwards,
        mock_session_exists,
    ):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
            }
        ]
        mock_refresh_forward.return_value = True
        mock_load_config.return_value = {"reconnect_delay": 1}

        result = self.runner.invoke(
            refresh,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "Successfully refreshed forward" in result.output
        mock_refresh_forward.assert_called_once_with("L:8080:localhost:80", "portmux")

    @patch("portmux.commands.refresh.session_exists")
    def test_refresh_no_session(self, mock_session_exists):
        mock_session_exists.return_value = False

        result = self.runner.invoke(
            refresh,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "not active" in result.output
        assert "portmux init" in result.output

    @patch("portmux.commands.refresh.session_exists")
    @patch("portmux.commands.refresh.list_forwards")
    def test_refresh_forward_not_found(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = []

        result = self.runner.invoke(
            refresh,
            ["L:8080:localhost:80"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "not found" in result.output
        assert "portmux list" in result.output

    @patch("portmux.commands.refresh.session_exists")
    @patch("portmux.commands.refresh.list_forwards")
    @patch("portmux.commands.refresh.refresh_forward")
    @patch("portmux.commands.refresh.load_config")
    @patch("time.sleep")
    def test_refresh_all_forwards(
        self,
        mock_sleep,
        mock_load_config,
        mock_refresh_forward,
        mock_list_forwards,
        mock_session_exists,
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
        mock_refresh_forward.return_value = True
        mock_load_config.return_value = {"reconnect_delay": 1}

        result = self.runner.invoke(
            refresh,
            ["--all"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "Successfully refreshed 2/2 forward(s)" in result.output
        assert mock_refresh_forward.call_count == 2
        # Should sleep between refreshes (but not after the last one)
        mock_sleep.assert_called_once_with(1)

    @patch("portmux.commands.refresh.session_exists")
    @patch("portmux.commands.refresh.list_forwards")
    @patch("portmux.commands.refresh.refresh_forward")
    @patch("portmux.commands.refresh.load_config")
    def test_refresh_with_custom_delay(
        self,
        mock_load_config,
        mock_refresh_forward,
        mock_list_forwards,
        mock_session_exists,
    ):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
            }
        ]
        mock_refresh_forward.return_value = True
        mock_load_config.return_value = {"reconnect_delay": 1}

        result = self.runner.invoke(
            refresh,
            ["L:8080:localhost:80", "--delay", "3"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "with 3.0s delay" in result.output

    def test_refresh_no_arguments(self):
        result = self.runner.invoke(
            refresh, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code != 0
        assert "Must specify forward name or use --all flag" in result.output
