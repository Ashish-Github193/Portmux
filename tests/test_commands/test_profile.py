"""Tests for profile command."""

from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.profile import profile
from portmux.exceptions import ConfigError


class TestProfileListCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.list_available_profiles")
    @patch("portmux.commands.profile.profile_summary")
    def test_profile_list_success(self, mock_summary, mock_list_profiles, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}, "prod": {}}}
        mock_list_profiles.return_value = ["dev", "prod"]
        mock_summary.return_value = {
            "total_profiles": 2,
            "profile_names": ["dev", "prod"],
            "profiles": {
                "dev": {
                    "session_name": "portmux-dev",
                    "command_count": 2,
                    "has_custom_identity": True,
                    "has_custom_session": True
                },
                "prod": {
                    "session_name": "portmux-prod",
                    "command_count": 1,
                    "has_custom_identity": False,
                    "has_custom_session": True
                }
            }
        }

        result = self.runner.invoke(
            profile,
            ["list"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Available Profiles" in result.output
        assert "dev" in result.output
        assert "prod" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.list_available_profiles")
    def test_profile_list_empty(self, mock_list_profiles, mock_load_config):
        mock_load_config.return_value = {"profiles": {}}
        mock_list_profiles.return_value = []

        result = self.runner.invoke(
            profile,
            ["list"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "No profiles configured" in result.output

    @patch("portmux.commands.profile.load_config")
    def test_profile_list_error(self, mock_load_config):
        mock_load_config.side_effect = ConfigError("Config error")

        result = self.runner.invoke(
            profile,
            ["list"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 1


class TestProfileShowCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.profile_exists")
    @patch("portmux.commands.profile.get_profile_info")
    def test_profile_show_success(self, mock_get_info, mock_exists, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}}}
        mock_exists.return_value = True
        mock_get_info.return_value = {
            "name": "dev",
            "session_name": "portmux-dev",
            "default_identity": "~/.ssh/dev_key",
            "commands": [
                "portmux add L 3000:localhost:3000 user@dev",
                "portmux add L 8080:localhost:8080 user@dev"
            ],
            "command_count": 2,
            "inherits_session_name": False,
            "inherits_identity": False
        }

        result = self.runner.invoke(
            profile,
            ["show", "dev"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Profile: dev" in result.output
        assert "portmux-dev" in result.output
        assert "~/.ssh/dev_key" in result.output
        assert "Commands: 2" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.profile_exists")
    @patch("portmux.commands.profile.list_available_profiles")
    def test_profile_show_not_found(self, mock_list_profiles, mock_exists, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}}}
        mock_exists.return_value = False
        mock_list_profiles.return_value = ["dev", "prod"]

        result = self.runner.invoke(
            profile,
            ["show", "staging"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Profile 'staging' not found" in result.output
        assert "Available profiles: dev, prod" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.profile_exists")
    @patch("portmux.commands.profile.list_available_profiles")
    def test_profile_show_no_profiles(self, mock_list_profiles, mock_exists, mock_load_config):
        mock_load_config.return_value = {"profiles": {}}
        mock_exists.return_value = False
        mock_list_profiles.return_value = []

        result = self.runner.invoke(
            profile,
            ["show", "dev"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Profile 'dev' not found" in result.output
        assert "No profiles are configured" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.profile_exists")
    @patch("portmux.commands.profile.get_profile_info")
    def test_profile_show_inherits_config(self, mock_get_info, mock_exists, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}}}
        mock_exists.return_value = True
        mock_get_info.return_value = {
            "name": "dev",
            "session_name": "portmux",
            "default_identity": None,
            "commands": [],
            "command_count": 0,
            "inherits_session_name": True,
            "inherits_identity": True
        }

        result = self.runner.invoke(
            profile,
            ["show", "dev"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "Profile: dev" in result.output
        assert "(inherited from general configuration)" in result.output

    @patch("portmux.commands.profile.load_config")
    def test_profile_show_error(self, mock_load_config):
        mock_load_config.side_effect = ConfigError("Config error")

        result = self.runner.invoke(
            profile,
            ["show", "dev"],
            obj={"config": None, "verbose": False}
        )

        assert result.exit_code == 1


class TestProfileActiveCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.get_active_profile")
    def test_profile_active_with_profile(self, mock_get_active, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}}}
        mock_get_active.return_value = "dev"

        result = self.runner.invoke(
            profile,
            ["active"],
            obj={"config": None, "session": "portmux-dev", "verbose": False}
        )

        assert result.exit_code == 0
        assert "Active profile: dev" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.get_active_profile")
    @patch("portmux.commands.profile.list_available_profiles")
    def test_profile_active_no_profile(self, mock_list_profiles, mock_get_active, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}, "prod": {}}}
        mock_get_active.return_value = None
        mock_list_profiles.return_value = ["dev", "prod"]

        result = self.runner.invoke(
            profile,
            ["active"],
            obj={"config": None, "session": "portmux", "verbose": False}
        )

        assert result.exit_code == 0
        assert "No profile is currently active" in result.output
        assert "Session 'portmux' was initialized without a profile" in result.output
        assert "Available profiles: dev, prod" in result.output

    @patch("portmux.commands.profile.load_config")
    @patch("portmux.commands.profile.get_active_profile")
    def test_profile_active_verbose_with_profile(self, mock_get_active, mock_load_config):
        mock_load_config.return_value = {"profiles": {"dev": {}}}
        mock_get_active.return_value = "dev"

        result = self.runner.invoke(
            profile,
            ["active"],
            obj={"config": None, "session": "portmux-dev", "verbose": True}
        )

        assert result.exit_code == 0
        assert "Active profile: dev" in result.output

    @patch("portmux.commands.profile.load_config")
    def test_profile_active_error(self, mock_load_config):
        mock_load_config.side_effect = ConfigError("Config error")

        result = self.runner.invoke(
            profile,
            ["active"],
            obj={"config": None, "session": "portmux", "verbose": False}
        )

        assert result.exit_code == 1


class TestProfileGroupCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_profile_help(self):
        result = self.runner.invoke(profile, ["--help"])

        assert result.exit_code == 0
        assert "Manage PortMUX configuration profiles" in result.output
        assert "list" in result.output
        assert "show" in result.output
        assert "active" in result.output

    def test_profile_list_help(self):
        result = self.runner.invoke(profile, ["list", "--help"])

        assert result.exit_code == 0
        assert "List all available profiles" in result.output

    def test_profile_show_help(self):
        result = self.runner.invoke(profile, ["show", "--help"])

        assert result.exit_code == 0
        assert "Show detailed information about a specific profile" in result.output

    def test_profile_active_help(self):
        result = self.runner.invoke(profile, ["active", "--help"])

        assert result.exit_code == 0
        assert "Show the currently active profile" in result.output