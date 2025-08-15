"""Tests for init command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.init import init


class TestInitCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.init.session_exists")
    @patch("portmux.commands.init.create_session")
    @patch("portmux.commands.init.load_config")
    @patch("portmux.commands.init.create_default_config")
    def test_init_new_session_success(
        self,
        mock_create_config,
        mock_load_config,
        mock_create_session,
        mock_session_exists,
    ):
        mock_session_exists.return_value = False
        mock_create_session.return_value = True
        mock_load_config.return_value = {"session_name": "portmux"}

        result = self.runner.invoke(
            init, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Successfully initialized PortMUX session" in result.output
        mock_create_session.assert_called_once_with("portmux")

    @patch("portmux.commands.init.session_exists")
    @patch("portmux.commands.init.load_config")
    def test_init_existing_session_no_force(
        self, mock_load_config, mock_session_exists
    ):
        mock_session_exists.return_value = True
        mock_load_config.return_value = {"session_name": "portmux"}

        result = self.runner.invoke(
            init, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "already exists" in result.output
        assert "Use --force to recreate" in result.output

    @patch("portmux.commands.init.session_exists")
    @patch("portmux.commands.init.create_session")
    @patch("portmux.commands.init.kill_session")
    @patch("portmux.commands.init.load_config")
    def test_init_force_recreate(
        self,
        mock_load_config,
        mock_kill_session,
        mock_create_session,
        mock_session_exists,
    ):
        mock_session_exists.return_value = True
        mock_kill_session.return_value = True
        mock_create_session.return_value = True
        mock_load_config.return_value = {"session_name": "portmux"}

        result = self.runner.invoke(
            init,
            ["--force"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0
        assert "Successfully initialized PortMUX session" in result.output
        mock_kill_session.assert_called_once_with("portmux")
        mock_create_session.assert_called_once_with("portmux")

    @patch("portmux.commands.init.session_exists")
    @patch("portmux.commands.init.load_config")
    @patch("portmux.commands.init.create_default_config")
    def test_init_creates_default_config(
        self, mock_create_config, mock_load_config, mock_session_exists
    ):
        mock_session_exists.return_value = False
        mock_load_config.side_effect = [
            Exception("Config not found"),
            {"session_name": "portmux"},
        ]

        with patch("portmux.commands.init.create_session") as mock_create_session:
            mock_create_session.return_value = True

            result = self.runner.invoke(
                init, [], obj={"session": "portmux", "config": None, "verbose": True}
            )

            assert result.exit_code == 0
            mock_create_config.assert_called_once()
            assert "Default configuration created" in result.output

    @patch("portmux.commands.init.session_exists")
    @patch("portmux.commands.init.create_session")
    @patch("portmux.commands.init.load_config")
    def test_init_verbose_output(
        self, mock_load_config, mock_create_session, mock_session_exists
    ):
        mock_session_exists.return_value = False
        mock_create_session.return_value = True
        mock_load_config.return_value = {"session_name": "portmux"}

        result = self.runner.invoke(
            init, [], obj={"session": "portmux", "config": None, "verbose": True}
        )

        assert result.exit_code == 0
        assert "Loading configuration" in result.output
        assert "Creating tmux session" in result.output
