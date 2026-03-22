"""Tests for window management functions."""

from unittest.mock import MagicMock

import pytest

from portmux.exceptions import TmuxError
from portmux.tmux.windows import create_window, kill_window, list_windows, window_exists


def _make_window(name, flags="", command="ssh"):
    """Create a mock libtmux Window."""
    window = MagicMock()
    window.name = name
    window.window_raw_flags = flags
    pane = MagicMock()
    pane.pane_current_command = command
    pane.pane_start_command = command
    window.active_pane = pane
    return window


class TestCreateWindow:
    def test_create_window_success(self, mocker):
        mock_session = MagicMock()
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = create_window("test-window", "ssh -N -L 8080:localhost:80 user@host")

        assert result is True
        mock_session.new_window.assert_called_once_with(
            window_name="test-window",
            window_shell="ssh -N -L 8080:localhost:80 user@host",
            attach=False,
        )

    def test_create_window_custom_session(self, mocker):
        mock_session = MagicMock()
        mock_get = mocker.patch(
            "portmux.tmux.windows._get_session", return_value=mock_session
        )

        result = create_window("test-window", "echo test", "custom-session")

        assert result is True
        mock_get.assert_called_once_with("custom-session")
        mock_session.new_window.assert_called_once_with(
            window_name="test-window",
            window_shell="echo test",
            attach=False,
        )

    def test_create_window_session_not_found(self, mocker):
        mocker.patch("portmux.tmux.windows._get_session", return_value=None)

        with pytest.raises(
            TmuxError,
            match="Failed to create window 'test-window': session 'portmux' not found",
        ):
            create_window("test-window", "echo test")

    def test_create_window_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.windows._get_session",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            create_window("test-window", "echo test")


class TestKillWindow:
    def test_kill_window_success(self, mocker):
        mock_window = MagicMock()
        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = kill_window("test-window")

        assert result is True
        mock_window.kill.assert_called_once()

    def test_kill_window_custom_session(self, mocker):
        mock_window = MagicMock()
        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mock_get = mocker.patch(
            "portmux.tmux.windows._get_session", return_value=mock_session
        )

        result = kill_window("test-window", "custom-session")

        assert result is True
        mock_get.assert_called_once_with("custom-session")

    def test_kill_window_not_found(self, mocker):
        mock_session = MagicMock()
        mock_session.windows.get.return_value = None
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = kill_window("test-window")

        assert result is True  # Already gone, consider success

    def test_kill_window_session_gone(self, mocker):
        mocker.patch("portmux.tmux.windows._get_session", return_value=None)

        result = kill_window("test-window")

        assert result is True  # Session gone, window is gone too

    def test_kill_window_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.windows._get_session",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            kill_window("test-window")


class TestListWindows:
    def test_list_windows_success(self, mocker):
        mock_session = MagicMock()
        mock_session.windows = [
            _make_window("L:8080:localhost:80", "-", "ssh"),
            _make_window("R:9000:localhost:9000", "*", "ssh"),
        ]
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = list_windows()

        expected = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
        ]
        assert result == expected

    def test_list_windows_empty(self, mocker):
        mock_session = MagicMock()
        mock_session.windows = []
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = list_windows()

        assert result == []

    def test_list_windows_custom_session(self, mocker):
        mock_session = MagicMock()
        mock_session.windows = [_make_window("test-window", "-", "bash")]
        mock_get = mocker.patch(
            "portmux.tmux.windows._get_session", return_value=mock_session
        )

        result = list_windows("custom-session")

        expected = [{"name": "test-window", "status": "-", "command": "bash"}]
        assert result == expected
        mock_get.assert_called_once_with("custom-session")

    def test_list_windows_session_not_found(self, mocker):
        mocker.patch("portmux.tmux.windows._get_session", return_value=None)

        result = list_windows()

        assert result == []  # Session doesn't exist, return empty list

    def test_list_windows_no_active_pane(self, mocker):
        mock_window = MagicMock()
        mock_window.name = "test"
        mock_window.window_raw_flags = ""
        mock_window.active_pane = None
        mock_session = MagicMock()
        mock_session.windows = [mock_window]
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = list_windows()

        assert result == [{"name": "test", "status": "", "command": ""}]

    def test_list_windows_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.windows._get_session",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            list_windows()


class TestWindowExists:
    def test_window_exists_true(self, mocker):
        mock_window = MagicMock()
        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = window_exists("L:8080:localhost:80")

        assert result is True
        mock_session.windows.get.assert_called_once_with(
            window_name="L:8080:localhost:80", default=None
        )

    def test_window_exists_false(self, mocker):
        mock_session = MagicMock()
        mock_session.windows.get.return_value = None
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = window_exists("nonexistent")

        assert result is False

    def test_window_exists_custom_session(self, mocker):
        mock_window = MagicMock()
        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mock_get = mocker.patch(
            "portmux.tmux.windows._get_session", return_value=mock_session
        )

        result = window_exists("test-window", "custom-session")

        assert result is True
        mock_get.assert_called_once_with("custom-session")

    def test_window_exists_session_gone(self, mocker):
        mocker.patch("portmux.tmux.windows._get_session", return_value=None)

        result = window_exists("any-window")

        assert result is False
