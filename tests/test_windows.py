"""Tests for window management functions."""

from unittest.mock import MagicMock

import pytest

from portmux.exceptions import TmuxError
from portmux.windows import (create_window, kill_window, list_windows,
                             window_exists)


class TestCreateWindow:
    def test_create_window_success(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = create_window("test-window", "ssh -N -L 8080:localhost:80 user@host")

        assert result is True
        mock_run.assert_called_once_with(
            [
                "tmux",
                "new-window",
                "-t",
                "portmux",
                "-n",
                "test-window",
                "ssh -N -L 8080:localhost:80 user@host",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_window_custom_session(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = create_window("test-window", "echo test", "custom-session")

        assert result is True
        mock_run.assert_called_once_with(
            [
                "tmux",
                "new-window",
                "-t",
                "custom-session",
                "-n",
                "test-window",
                "echo test",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_window_error(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="session not found: portmux"
        )

        with pytest.raises(
            TmuxError,
            match="Failed to create window 'test-window': session not found: portmux",
        ):
            create_window("test-window", "echo test")

    def test_create_window_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            create_window("test-window", "echo test")


class TestKillWindow:
    def test_kill_window_success(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = kill_window("test-window")

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "kill-window", "-t", "portmux:test-window"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_kill_window_custom_session(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = kill_window("test-window", "custom-session")

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "kill-window", "-t", "custom-session:test-window"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_kill_window_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="window not found: test-window"
        )

        result = kill_window("test-window")

        assert result is True  # Already gone, consider success

    def test_kill_window_cant_find(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="can't find window: test-window"
        )

        result = kill_window("test-window")

        assert result is True  # Already gone, consider success

    def test_kill_window_other_error(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="some other error")

        with pytest.raises(
            TmuxError, match="Failed to kill window 'test-window': some other error"
        ):
            kill_window("test-window")

    def test_kill_window_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            kill_window("test-window")


class TestListWindows:
    def test_list_windows_success(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="L:8080:localhost:80|-|ssh\nR:9000:localhost:9000|*|ssh\n",
            stderr="",
        )

        result = list_windows()

        expected = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
        ]
        assert result == expected
        mock_run.assert_called_once_with(
            [
                "tmux",
                "list-windows",
                "-t",
                "portmux",
                "-F",
                "#{window_name}|#{window_flags}|#{pane_current_command}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_list_windows_empty(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = list_windows()

        assert result == []

    def test_list_windows_custom_session(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="test-window|-|bash\n", stderr=""
        )

        result = list_windows("custom-session")

        expected = [{"name": "test-window", "status": "-", "command": "bash"}]
        assert result == expected
        mock_run.assert_called_once_with(
            [
                "tmux",
                "list-windows",
                "-t",
                "custom-session",
                "-F",
                "#{window_name}|#{window_flags}|#{pane_current_command}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_list_windows_session_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="session not found: portmux"
        )

        result = list_windows()

        assert result == []  # Session doesn't exist, return empty list

    def test_list_windows_other_error(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="some other error")

        with pytest.raises(TmuxError, match="Failed to list windows: some other error"):
            list_windows()

    def test_list_windows_malformed_output(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="malformed|line\nproper|line|command\n", stderr=""
        )

        result = list_windows()

        # Should only include properly formatted lines
        expected = [{"name": "proper", "status": "line", "command": "command"}]
        assert result == expected

    def test_list_windows_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            list_windows()


class TestWindowExists:
    def test_window_exists_true(self, mocker):
        mock_list_windows = mocker.patch("portmux.windows.list_windows")
        mock_list_windows.return_value = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
        ]

        result = window_exists("L:8080:localhost:80")

        assert result is True
        mock_list_windows.assert_called_once_with("portmux")

    def test_window_exists_false(self, mocker):
        mock_list_windows = mocker.patch("portmux.windows.list_windows")
        mock_list_windows.return_value = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
        ]

        result = window_exists("nonexistent")

        assert result is False
        mock_list_windows.assert_called_once_with("portmux")

    def test_window_exists_custom_session(self, mocker):
        mock_list_windows = mocker.patch("portmux.windows.list_windows")
        mock_list_windows.return_value = [
            {"name": "test-window", "status": "-", "command": "bash"}
        ]

        result = window_exists("test-window", "custom-session")

        assert result is True
        mock_list_windows.assert_called_once_with("custom-session")

    def test_window_exists_empty_list(self, mocker):
        mock_list_windows = mocker.patch("portmux.windows.list_windows")
        mock_list_windows.return_value = []

        result = window_exists("any-window")

        assert result is False
