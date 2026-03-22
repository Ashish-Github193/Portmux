"""Tests for session management functions."""

from unittest.mock import MagicMock

import pytest
from libtmux.exc import LibTmuxException, TmuxSessionExists

from portmux.exceptions import TmuxError
from portmux.tmux.session import create_session, kill_session, session_exists


class TestCreateSession:
    def test_create_session_success(self, mocker):
        mock_server = MagicMock()
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = create_session("test-session")

        assert result is True
        mock_server.new_session.assert_called_once_with(
            session_name="test-session", attach=False
        )

    def test_create_session_default_name(self, mocker):
        mock_server = MagicMock()
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = create_session()

        assert result is True
        mock_server.new_session.assert_called_once_with(
            session_name="portmux", attach=False
        )

    def test_create_session_already_exists(self, mocker):
        mock_server = MagicMock()
        mock_server.new_session.side_effect = TmuxSessionExists()
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = create_session("test-session")

        assert result is False

    def test_create_session_other_error(self, mocker):
        mock_server = MagicMock()
        mock_server.new_session.side_effect = LibTmuxException("some other error")
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        with pytest.raises(TmuxError, match="Failed to create session 'test-session'"):
            create_session("test-session")

    def test_create_session_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.session._get_server",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            create_session("test-session")


class TestSessionExists:
    def test_session_exists_true(self, mocker):
        mock_server = MagicMock()
        mock_server.has_session.return_value = True
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = session_exists("test-session")

        assert result is True
        mock_server.has_session.assert_called_once_with("test-session")

    def test_session_exists_false(self, mocker):
        mock_server = MagicMock()
        mock_server.has_session.return_value = False
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = session_exists("test-session")

        assert result is False

    def test_session_exists_default_name(self, mocker):
        mock_server = MagicMock()
        mock_server.has_session.return_value = True
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = session_exists()

        assert result is True
        mock_server.has_session.assert_called_once_with("portmux")

    def test_session_exists_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.session._get_server",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            session_exists("test-session")

    def test_session_exists_libtmux_error_returns_false(self, mocker):
        mock_server = MagicMock()
        mock_server.has_session.side_effect = LibTmuxException("error")
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = session_exists("test-session")

        assert result is False


class TestKillSession:
    def test_kill_session_success(self, mocker):
        mock_session = MagicMock()
        mock_server = MagicMock()
        mock_server.sessions.get.return_value = mock_session
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = kill_session("test-session")

        assert result is True
        mock_session.kill.assert_called_once()

    def test_kill_session_not_found(self, mocker):
        mock_server = MagicMock()
        mock_server.sessions.get.return_value = None
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = kill_session("test-session")

        assert result is True  # Already gone, consider success

    def test_kill_session_other_error(self, mocker):
        mock_session = MagicMock()
        mock_session.kill.side_effect = LibTmuxException("some other error")
        mock_server = MagicMock()
        mock_server.sessions.get.return_value = mock_session
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        with pytest.raises(TmuxError, match="Failed to kill session 'test-session'"):
            kill_session("test-session")

    def test_kill_session_default_name(self, mocker):
        mock_session = MagicMock()
        mock_server = MagicMock()
        mock_server.sessions.get.return_value = mock_session
        mocker.patch("portmux.tmux.session._get_server", return_value=mock_server)

        result = kill_session()

        assert result is True
        mock_server.sessions.get.assert_called_once_with(
            session_name="portmux", default=None
        )

    def test_kill_session_tmux_not_found(self, mocker):
        mocker.patch(
            "portmux.tmux.session._get_server",
            side_effect=TmuxError("tmux is not installed or not found in PATH"),
        )

        with pytest.raises(
            TmuxError, match="tmux is not installed or not found in PATH"
        ):
            kill_session("test-session")
