"""Tests for session management functions."""

from unittest.mock import MagicMock

import pytest

from portmux.exceptions import TmuxError
from portmux.session import create_session, kill_session, session_exists


class TestCreateSession:
    def test_create_session_success(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = create_session("test-session")

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "new-session", "-d", "-s", "test-session"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_session_default_name(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = create_session()

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "new-session", "-d", "-s", "portmux"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_session_already_exists(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="duplicate session: test-session"
        )

        result = create_session("test-session")

        assert result is False

    def test_create_session_other_error(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="some other error")

        with pytest.raises(
            TmuxError, match="Failed to create session 'test-session': some other error"
        ):
            create_session("test-session")

    def test_create_session_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            create_session("test-session")


class TestSessionExists:
    def test_session_exists_true(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = session_exists("test-session")

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "has-session", "-t", "test-session"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_session_exists_false(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1)

        result = session_exists("test-session")

        assert result is False

    def test_session_exists_default_name(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = session_exists()

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "has-session", "-t", "portmux"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_session_exists_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            session_exists("test-session")


class TestKillSession:
    def test_kill_session_success(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = kill_session("test-session")

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "kill-session", "-t", "test-session"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_kill_session_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="session not found: test-session"
        )

        result = kill_session("test-session")

        assert result is True  # Already gone, consider success

    def test_kill_session_other_error(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="some other error")

        with pytest.raises(
            TmuxError, match="Failed to kill session 'test-session': some other error"
        ):
            kill_session("test-session")

    def test_kill_session_default_name(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = kill_session()

        assert result is True
        mock_run.assert_called_once_with(
            ["tmux", "kill-session", "-t", "portmux"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_kill_session_tmux_not_found(self, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            kill_session("test-session")
