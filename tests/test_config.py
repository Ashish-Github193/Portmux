"""Simplified tests for configuration management functions."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open

import pytest

from portmux.config import (DEFAULT_CONFIG, get_default_identity, load_config,
                            validate_config)
from portmux.exceptions import ConfigError


class TestValidateConfig:
    def test_validate_config_valid(self):
        config = {
            "session_name": "test-session",
            "default_identity": None,
            "reconnect_delay": 1,
            "max_retries": 3,
        }

        result = validate_config(config)

        assert result is True

    def test_validate_config_missing_session_name(self):
        config = {}

        with pytest.raises(
            ConfigError, match="Missing required config key: 'session_name'"
        ):
            validate_config(config)

    def test_validate_config_invalid_session_name_type(self):
        config = {"session_name": 123}

        with pytest.raises(
            ConfigError, match="'session_name' must be a non-empty string"
        ):
            validate_config(config)

    def test_validate_config_empty_session_name(self):
        config = {"session_name": ""}

        with pytest.raises(
            ConfigError, match="'session_name' must be a non-empty string"
        ):
            validate_config(config)


class TestLoadConfigBasic:
    def test_load_config_file_not_exists(self, mocker):
        # Mock the config path to return a non-existent file
        mock_get_config_path = mocker.patch("portmux.config.get_config_path")
        mock_get_config_path.return_value = Path("/nonexistent/config.toml")

        result = load_config()

        expected = DEFAULT_CONFIG.copy()
        expected["startup"] = {"auto_execute": True, "commands": []}
        expected["profiles"] = {}
        assert result == expected

    def test_load_config_success(self, mocker):
        config_content = 'session_name = "custom-session"'

        # Mock file operations
        mock_get_config_path = mocker.patch("portmux.config.get_config_path")
        mock_config_file = MagicMock()
        mock_config_file.exists.return_value = True
        mock_get_config_path.return_value = mock_config_file

        # Mock open and toml.load
        mock_open_func = mock_open(read_data=config_content)
        mock_toml_load = mocker.patch("toml.load")
        mock_toml_load.return_value = {"session_name": "custom-session"}

        mocker.patch("builtins.open", mock_open_func)
        result = load_config()

        expected = DEFAULT_CONFIG.copy()
        expected["session_name"] = "custom-session"
        expected["startup"] = {"auto_execute": True, "commands": []}
        expected["profiles"] = {}
        assert result == expected


class TestGetDefaultIdentitySimple:
    def test_get_default_identity_found(self, mocker):
        # Mock Path.home to return a test directory
        mock_home = mocker.patch("pathlib.Path.home")
        mock_home.return_value = Path("/home/testuser")

        # Mock the exists method for the specific path we expect
        mocker.patch.object(Path, "exists", side_effect=lambda: True)
        result = get_default_identity()

        # Should return the first identity file found
        assert result == "/home/testuser/.ssh/id_ed25519"

    def test_get_default_identity_none_found(self, mocker):
        # Mock Path.home to return a test directory
        mock_home = mocker.patch("pathlib.Path.home")
        mock_home.return_value = Path("/home/testuser")

        # Mock exists to always return False
        mocker.patch.object(Path, "exists", return_value=False)
        result = get_default_identity()

        assert result is None
