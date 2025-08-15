"""Tests for profile management system."""

from unittest.mock import MagicMock, patch

import pytest

from portmux.config import DEFAULT_PROFILE_CONFIG
from portmux.exceptions import ConfigError
from portmux.profiles import (create_profile_template, get_active_profile,
                             get_profile_info, list_available_profiles,
                             load_profile, merge_profile_with_base,
                             profile_exists, profile_summary, validate_profile)


class TestLoadProfile:
    def test_load_profile_success(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {
                "dev": {
                    "session_name": "portmux-dev",
                    "commands": ["portmux add L 3000:localhost:3000 user@dev"]
                }
            }
        }
        
        result = load_profile("dev", config)
        
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] == "~/.ssh/id_rsa"  # Inherited
        assert result["startup"]["commands"] == ["portmux add L 3000:localhost:3000 user@dev"]
        assert result["_active_profile"] == "dev"

    def test_load_profile_inherits_base_config(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {
                "dev": {
                    "commands": ["portmux add L 3000:localhost:3000 user@dev"]
                    # No session_name or default_identity - should inherit
                }
            }
        }
        
        result = load_profile("dev", config)
        
        assert result["session_name"] == "portmux"  # Inherited
        assert result["default_identity"] == "~/.ssh/id_rsa"  # Inherited
        assert result["startup"]["commands"] == ["portmux add L 3000:localhost:3000 user@dev"]

    def test_load_profile_not_found(self):
        config = {
            "session_name": "portmux",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {
                "dev": {"commands": []}
            }
        }
        
        with pytest.raises(ConfigError, match="Profile 'prod' not found"):
            load_profile("prod", config)

    def test_load_profile_not_found_with_suggestions(self):
        config = {
            "session_name": "portmux",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {
                "dev": {"commands": []},
                "staging": {"commands": []}
            }
        }
        
        with pytest.raises(ConfigError, match="Available profiles: dev, staging"):
            load_profile("prod", config)

    def test_load_profile_no_profiles_configured(self):
        config = {
            "session_name": "portmux",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {}
        }
        
        with pytest.raises(ConfigError, match="No profiles are configured"):
            load_profile("dev", config)

    def test_load_profile_with_custom_identity(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "startup": {"auto_execute": True, "commands": []},
            "profiles": {
                "prod": {
                    "session_name": "portmux-prod",
                    "default_identity": "~/.ssh/prod_key",
                    "commands": ["portmux add L 5432:db:5432 user@prod"]
                }
            }
        }
        
        result = load_profile("prod", config)
        
        assert result["session_name"] == "portmux-prod"
        assert result["default_identity"] == "~/.ssh/prod_key"
        assert result["startup"]["commands"] == ["portmux add L 5432:db:5432 user@prod"]


class TestListAvailableProfiles:
    def test_list_profiles_multiple(self):
        config = {
            "profiles": {
                "dev": {"commands": []},
                "staging": {"commands": []},
                "prod": {"commands": []}
            }
        }
        
        result = list_available_profiles(config)
        
        assert result == ["dev", "prod", "staging"]  # Sorted alphabetically

    def test_list_profiles_empty(self):
        config = {"profiles": {}}
        
        result = list_available_profiles(config)
        
        assert result == []

    def test_list_profiles_missing_section(self):
        config = {}
        
        result = list_available_profiles(config)
        
        assert result == []

    def test_list_profiles_single(self):
        config = {
            "profiles": {
                "dev": {"commands": []}
            }
        }
        
        result = list_available_profiles(config)
        
        assert result == ["dev"]


class TestProfileExists:
    def test_profile_exists_true(self):
        config = {
            "profiles": {
                "dev": {"commands": []},
                "prod": {"commands": []}
            }
        }
        
        assert profile_exists(config, "dev") is True
        assert profile_exists(config, "prod") is True

    def test_profile_exists_false(self):
        config = {
            "profiles": {
                "dev": {"commands": []}
            }
        }
        
        assert profile_exists(config, "prod") is False

    def test_profile_exists_empty_profiles(self):
        config = {"profiles": {}}
        
        assert profile_exists(config, "dev") is False

    def test_profile_exists_missing_section(self):
        config = {}
        
        assert profile_exists(config, "dev") is False


class TestGetProfileInfo:
    def test_get_profile_info_complete(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "profiles": {
                "dev": {
                    "session_name": "portmux-dev",
                    "default_identity": "~/.ssh/dev_key",
                    "commands": [
                        "portmux add L 3000:localhost:3000 user@dev",
                        "portmux add L 8080:localhost:8080 user@dev"
                    ]
                }
            }
        }
        
        result = get_profile_info(config, "dev")
        
        assert result["name"] == "dev"
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] == "~/.ssh/dev_key"
        assert result["commands"] == [
            "portmux add L 3000:localhost:3000 user@dev",
            "portmux add L 8080:localhost:8080 user@dev"
        ]
        assert result["command_count"] == 2
        assert result["inherits_session_name"] is False
        assert result["inherits_identity"] is False

    def test_get_profile_info_inherits_config(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "profiles": {
                "dev": {
                    "commands": ["portmux add L 3000:localhost:3000 user@dev"]
                    # Missing session_name and default_identity
                }
            }
        }
        
        result = get_profile_info(config, "dev")
        
        assert result["name"] == "dev"
        assert result["session_name"] == "portmux"  # Inherited
        assert result["default_identity"] == "~/.ssh/id_rsa"  # Inherited
        assert result["command_count"] == 1
        assert result["inherits_session_name"] is True
        assert result["inherits_identity"] is True

    def test_get_profile_info_not_found(self):
        config = {
            "profiles": {
                "dev": {"commands": []}
            }
        }
        
        with pytest.raises(ConfigError, match="Profile 'prod' not found"):
            get_profile_info(config, "prod")

    def test_get_profile_info_no_commands(self):
        config = {
            "session_name": "portmux",
            "profiles": {
                "dev": {}  # No commands
            }
        }
        
        result = get_profile_info(config, "dev")
        
        assert result["commands"] == []
        assert result["command_count"] == 0


class TestValidateProfile:
    @patch('pathlib.Path.exists')
    def test_validate_profile_valid(self, mock_exists):
        mock_exists.return_value = True
        
        profile_config = {
            "session_name": "portmux-dev",
            "default_identity": "~/.ssh/dev_key",
            "commands": [
                "portmux add L 3000:localhost:3000 user@dev"
            ]
        }
        
        result = validate_profile("dev", profile_config)
        
        assert result is True

    def test_validate_profile_minimal(self):
        profile_config = {
            "commands": []
        }
        
        result = validate_profile("dev", profile_config)
        
        assert result is True

    def test_validate_profile_invalid_name(self):
        profile_config = {"commands": []}
        
        with pytest.raises(ConfigError, match="Profile names must be non-empty strings"):
            validate_profile("", profile_config)
        
        with pytest.raises(ConfigError, match="Profile names must be non-empty strings"):
            validate_profile(123, profile_config)

    def test_validate_profile_invalid_config_type(self):
        with pytest.raises(ConfigError, match="Profile 'dev' must be a dictionary"):
            validate_profile("dev", "not a dict")

    def test_validate_profile_invalid_session_name(self):
        profile_config = {
            "session_name": "",
            "commands": []
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' session_name must be a non-empty string"):
            validate_profile("dev", profile_config)

    def test_validate_profile_invalid_identity_type(self):
        profile_config = {
            "default_identity": 123,
            "commands": []
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' default_identity must be a string"):
            validate_profile("dev", profile_config)

    @patch('pathlib.Path.exists')
    def test_validate_profile_identity_not_found(self, mock_exists):
        mock_exists.return_value = False
        
        profile_config = {
            "default_identity": "~/.ssh/nonexistent_key",
            "commands": []
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' identity file not found"):
            validate_profile("dev", profile_config)

    def test_validate_profile_invalid_commands_type(self):
        profile_config = {
            "commands": "not a list"
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' commands must be a list"):
            validate_profile("dev", profile_config)

    def test_validate_profile_invalid_command_type(self):
        profile_config = {
            "commands": [123, "valid command"]
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' commands\\[0\\] must be a string"):
            validate_profile("dev", profile_config)

    def test_validate_profile_empty_command(self):
        profile_config = {
            "commands": ["", "valid command"]
        }
        
        with pytest.raises(ConfigError, match="Profile 'dev' commands\\[0\\] cannot be empty"):
            validate_profile("dev", profile_config)


class TestGetActiveProfile:
    def test_get_active_profile_present(self):
        config = {"_active_profile": "dev"}
        
        result = get_active_profile(config)
        
        assert result == "dev"

    def test_get_active_profile_missing(self):
        config = {}
        
        result = get_active_profile(config)
        
        assert result is None

    def test_get_active_profile_none(self):
        config = {"_active_profile": None}
        
        result = get_active_profile(config)
        
        assert result is None


class TestCreateProfileTemplate:
    def test_create_profile_template_minimal(self):
        result = create_profile_template("dev")
        
        assert result == DEFAULT_PROFILE_CONFIG

    def test_create_profile_template_complete(self):
        result = create_profile_template(
            "dev",
            session_name="portmux-dev",
            default_identity="~/.ssh/dev_key",
            commands=["portmux add L 3000:localhost:3000 user@dev"]
        )
        
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] == "~/.ssh/dev_key"
        assert result["commands"] == ["portmux add L 3000:localhost:3000 user@dev"]

    def test_create_profile_template_partial(self):
        result = create_profile_template(
            "dev",
            session_name="portmux-dev"
        )
        
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] is None
        assert result["commands"] == []


class TestProfileSummary:
    def test_profile_summary_multiple_profiles(self):
        config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "profiles": {
                "dev": {
                    "session_name": "portmux-dev",
                    "commands": ["cmd1", "cmd2"]
                },
                "prod": {
                    "default_identity": "~/.ssh/prod_key",
                    "commands": ["cmd1"]
                }
            }
        }
        
        result = profile_summary(config)
        
        assert result["total_profiles"] == 2
        assert result["profile_names"] == ["dev", "prod"]
        
        dev_info = result["profiles"]["dev"]
        assert dev_info["session_name"] == "portmux-dev"
        assert dev_info["command_count"] == 2
        assert dev_info["has_custom_identity"] is False
        assert dev_info["has_custom_session"] is True
        
        prod_info = result["profiles"]["prod"]
        assert prod_info["session_name"] == "portmux"  # Inherited
        assert prod_info["command_count"] == 1
        assert prod_info["has_custom_identity"] is True
        assert prod_info["has_custom_session"] is False

    def test_profile_summary_empty(self):
        config = {"profiles": {}}
        
        result = profile_summary(config)
        
        assert result["total_profiles"] == 0
        assert result["profile_names"] == []
        assert result["profiles"] == {}

    def test_profile_summary_invalid_profile(self):
        # This test would need to mock get_profile_info to raise an exception
        # Since we don't want to create an actually invalid profile config
        config = {
            "profiles": {
                "dev": {"commands": []}
            }
        }
        
        with patch('portmux.profiles.get_profile_info') as mock_get_info:
            mock_get_info.side_effect = ConfigError("Invalid profile")
            
            result = profile_summary(config)
            
            assert result["profiles"]["dev"]["error"] == "Invalid profile configuration"


class TestMergeProfileWithBase:
    def test_merge_profile_with_base_complete(self):
        base_config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "startup": {"auto_execute": True, "commands": []}
        }
        
        profile_config = {
            "session_name": "portmux-dev",
            "default_identity": "~/.ssh/dev_key",
            "commands": ["portmux add L 3000:localhost:3000 user@dev"]
        }
        
        result = merge_profile_with_base(base_config, profile_config)
        
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] == "~/.ssh/dev_key"
        assert result["startup"]["commands"] == ["portmux add L 3000:localhost:3000 user@dev"]
        assert result["startup"]["auto_execute"] is True

    def test_merge_profile_with_base_partial(self):
        base_config = {
            "session_name": "portmux",
            "default_identity": "~/.ssh/id_rsa",
            "startup": {"auto_execute": True, "commands": ["base_cmd"]}
        }
        
        profile_config = {
            "session_name": "portmux-dev"
            # No default_identity or commands
        }
        
        result = merge_profile_with_base(base_config, profile_config)
        
        assert result["session_name"] == "portmux-dev"
        assert result["default_identity"] == "~/.ssh/id_rsa"  # Inherited
        assert result["startup"]["commands"] == ["base_cmd"]  # Unchanged
        assert result["startup"]["auto_execute"] is True

    def test_merge_profile_with_base_commands_only(self):
        base_config = {
            "session_name": "portmux",
            "startup": {"auto_execute": False, "commands": ["base_cmd"]}
        }
        
        profile_config = {
            "commands": ["profile_cmd1", "profile_cmd2"]
        }
        
        result = merge_profile_with_base(base_config, profile_config)
        
        assert result["session_name"] == "portmux"  # Unchanged
        assert result["startup"]["commands"] == ["profile_cmd1", "profile_cmd2"]
        assert result["startup"]["auto_execute"] is True  # Set to True when commands provided

    def test_merge_profile_with_base_no_startup_section(self):
        base_config = {
            "session_name": "portmux"
        }
        
        profile_config = {
            "commands": ["profile_cmd"]
        }
        
        result = merge_profile_with_base(base_config, profile_config)
        
        assert result["startup"]["commands"] == ["profile_cmd"]
        assert result["startup"]["auto_execute"] is True