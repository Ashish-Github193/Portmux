"""Tests for startup command execution system."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from portmux.config import DEFAULT_STARTUP_CONFIG
from portmux.exceptions import ConfigError, PortMuxError
from portmux.startup import (execute_startup_command, execute_startup_commands,
                            get_startup_command_preview, parse_startup_command,
                            startup_commands_enabled, validate_startup_commands)


class TestParseStartupCommand:
    def test_parse_portmux_command_valid(self):
        command = "portmux add L 8080:localhost:80 user@host"
        result = parse_startup_command(command)

        assert result["command"] == "portmux"
        assert result["args"] == ["add", "L", "8080:localhost:80", "user@host"]
        assert result["original"] == command

    def test_parse_portmux_command_with_options(self):
        command = "portmux add L 8080:localhost:80 user@host -i ~/.ssh/key"
        result = parse_startup_command(command)

        assert result["command"] == "portmux"
        assert result["args"] == ["add", "L", "8080:localhost:80", "user@host", "-i", "~/.ssh/key"]

    def test_parse_non_portmux_command(self):
        command = "echo 'hello world'"
        result = parse_startup_command(command)

        assert result["command"] == "echo"
        assert result["args"] == ["hello world"]
        assert result["original"] == command

    def test_parse_empty_command(self):
        with pytest.raises(ConfigError, match="Startup command cannot be empty"):
            parse_startup_command("")

    def test_parse_whitespace_only_command(self):
        with pytest.raises(ConfigError, match="Startup command cannot be empty"):
            parse_startup_command("   ")

    def test_parse_invalid_syntax(self):
        with pytest.raises(ConfigError, match="Invalid command syntax"):
            parse_startup_command("portmux add 'unclosed quote")

    def test_parse_portmux_without_subcommand(self):
        with pytest.raises(ConfigError, match="PortMUX commands must have subcommands"):
            parse_startup_command("portmux")

    def test_parse_portmux_invalid_subcommand(self):
        with pytest.raises(ConfigError, match="Invalid PortMUX subcommand: invalid"):
            parse_startup_command("portmux invalid")

    def test_parse_quoted_arguments(self):
        command = 'portmux add L "8080:local host:80" user@host'
        result = parse_startup_command(command)

        assert result["command"] == "portmux"
        assert result["args"] == ["add", "L", "8080:local host:80", "user@host"]


class TestValidateStartupCommands:
    def test_validate_empty_list(self):
        valid, errors = validate_startup_commands([])
        assert valid is True
        assert errors == []

    def test_validate_valid_commands(self):
        commands = [
            "portmux add L 8080:localhost:80 user@host",
            "portmux remove L:8080:localhost:80",
            "echo 'test command'"
        ]
        valid, errors = validate_startup_commands(commands)
        
        assert valid is True
        assert errors == []

    def test_validate_invalid_commands(self):
        commands = [
            "portmux add L 8080:localhost:80 user@host",  # Valid
            "",  # Invalid - empty
            "portmux invalid"  # Invalid - bad subcommand
        ]
        valid, errors = validate_startup_commands(commands)
        
        assert valid is False
        assert len(errors) == 2
        assert "Command 2:" in errors[0]
        assert "Command 3:" in errors[1]

    def test_validate_mixed_commands(self):
        commands = [
            "portmux add L 8080:localhost:80 user@host",
            "ls -la",
            "portmux status"
        ]
        valid, errors = validate_startup_commands(commands)
        
        assert valid is True
        assert errors == []


class TestExecuteStartupCommand:
    @patch('portmux.startup.subprocess.run')
    def test_execute_portmux_command_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        
        result = execute_startup_command(
            "portmux add L 8080:localhost:80 user@host",
            "test-session",
            verbose=False
        )
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check that the command includes session argument
        called_args = mock_run.call_args[0][0]
        assert "--session" in called_args
        assert "test-session" in called_args

    @patch('portmux.startup.subprocess.run')
    def test_execute_portmux_command_with_existing_session_arg(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        
        result = execute_startup_command(
            "portmux add L 8080:localhost:80 user@host --session existing",
            "test-session",
            verbose=False
        )
        
        assert result is True
        
        # Should not add another session argument
        called_args = mock_run.call_args[0][0]
        session_count = called_args.count("--session")
        assert session_count == 1

    @patch('portmux.startup.subprocess.run')
    def test_execute_non_portmux_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        
        result = execute_startup_command(
            "echo 'hello world'",
            "test-session",
            verbose=False
        )
        
        assert result is True
        
        # Should execute the command as-is
        called_args = mock_run.call_args[0][0]
        assert called_args == ["echo", "hello world"]

    @patch('portmux.startup.subprocess.run')
    def test_execute_command_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")
        
        result = execute_startup_command(
            "portmux add L 8080:localhost:80 user@host",
            "test-session",
            verbose=False
        )
        
        assert result is False

    @patch('portmux.startup.subprocess.run')
    def test_execute_command_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)
        
        result = execute_startup_command(
            "portmux add L 8080:localhost:80 user@host",
            "test-session",
            verbose=False
        )
        
        assert result is False

    @patch('portmux.startup.subprocess.run')
    def test_execute_command_subprocess_error(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("Process failed")
        
        result = execute_startup_command(
            "portmux add L 8080:localhost:80 user@host",
            "test-session",
            verbose=False
        )
        
        assert result is False

    @patch('portmux.startup.subprocess.run')
    def test_execute_command_unexpected_error(self, mock_run):
        mock_run.side_effect = Exception("Unexpected error")
        
        with pytest.raises(PortMuxError, match="Startup command execution failed"):
            execute_startup_command(
                "portmux add L 8080:localhost:80 user@host",
                "test-session",
                verbose=False
            )

    def test_execute_invalid_command(self):
        with pytest.raises(ConfigError):
            execute_startup_command("", "test-session")


class TestExecuteStartupCommands:
    @patch('portmux.startup.execute_startup_command')
    def test_execute_multiple_commands_success(self, mock_execute):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": [
                    "portmux add L 8080:localhost:80 user@host",
                    "portmux add R 9000:localhost:3000 user@host"
                ]
            }
        }
        mock_execute.return_value = True
        
        result = execute_startup_commands(config, "test-session")
        
        assert result is True
        assert mock_execute.call_count == 2

    @patch('portmux.startup.execute_startup_command')
    def test_execute_commands_partial_failure(self, mock_execute):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": [
                    "portmux add L 8080:localhost:80 user@host",
                    "portmux add R 9000:localhost:3000 user@host"
                ]
            }
        }
        mock_execute.side_effect = [True, False]  # First succeeds, second fails
        
        result = execute_startup_commands(config, "test-session")
        
        assert result is False
        assert mock_execute.call_count == 2

    def test_execute_commands_disabled(self):
        config = {
            "startup": {
                "auto_execute": False,
                "commands": [
                    "portmux add L 8080:localhost:80 user@host"
                ]
            }
        }
        
        result = execute_startup_commands(config, "test-session")
        
        assert result is True  # Returns True when disabled (no-op)

    def test_execute_commands_empty_list(self):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": []
            }
        }
        
        result = execute_startup_commands(config, "test-session")
        
        assert result is True

    def test_execute_commands_missing_startup_config(self):
        config = {}
        
        result = execute_startup_commands(config, "test-session")
        
        assert result is True


class TestStartupCommandsEnabled:
    def test_enabled_with_commands(self):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": ["portmux add L 8080:localhost:80 user@host"]
            }
        }
        
        assert startup_commands_enabled(config) is True

    def test_disabled_auto_execute(self):
        config = {
            "startup": {
                "auto_execute": False,
                "commands": ["portmux add L 8080:localhost:80 user@host"]
            }
        }
        
        assert startup_commands_enabled(config) is False

    def test_enabled_no_commands(self):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": []
            }
        }
        
        assert startup_commands_enabled(config) is False

    def test_missing_startup_config(self):
        config = {}
        
        assert startup_commands_enabled(config) is False

    def test_partial_startup_config(self):
        config = {
            "startup": {
                "auto_execute": True
                # Missing commands
            }
        }
        
        assert startup_commands_enabled(config) is False


class TestGetStartupCommandPreview:
    def test_get_preview_with_commands(self):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": [
                    "portmux add L 8080:localhost:80 user@host",
                    "portmux add R 9000:localhost:3000 user@host"
                ]
            }
        }
        
        preview = get_startup_command_preview(config)
        
        assert len(preview) == 2
        assert "portmux add L 8080:localhost:80 user@host" in preview
        assert "portmux add R 9000:localhost:3000 user@host" in preview

    def test_get_preview_disabled(self):
        config = {
            "startup": {
                "auto_execute": False,
                "commands": ["portmux add L 8080:localhost:80 user@host"]
            }
        }
        
        preview = get_startup_command_preview(config)
        
        assert preview == []

    def test_get_preview_no_commands(self):
        config = {
            "startup": {
                "auto_execute": True,
                "commands": []
            }
        }
        
        preview = get_startup_command_preview(config)
        
        assert preview == []

    def test_get_preview_missing_config(self):
        config = {}
        
        preview = get_startup_command_preview(config)
        
        assert preview == []