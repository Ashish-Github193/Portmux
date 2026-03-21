"""Tests for window diagnostics function."""

from unittest.mock import MagicMock

from portmux.models import TunnelDiagnostics
from portmux.tmux.windows import get_window_diagnostics


class TestGetWindowDiagnostics:
    def test_returns_diagnostics(self, mocker):
        mock_pane = MagicMock()
        mock_pane.pane_pid = "12345"
        mock_pane.pane_current_command = "ssh"
        mock_pane.pane_dead_status = None
        mock_pane.capture_pane.return_value = ["line1", "line2"]

        mock_window = MagicMock()
        mock_window.active_pane = mock_pane

        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = get_window_diagnostics("L:8080:localhost:80", "portmux")

        assert isinstance(result, TunnelDiagnostics)
        assert result.pane_pid == 12345
        assert result.pane_current_command == "ssh"
        assert result.pane_dead is False
        assert result.pane_content == ["line1", "line2"]

    def test_session_not_found(self, mocker):
        mocker.patch("portmux.tmux.windows._get_session", return_value=None)

        result = get_window_diagnostics("L:8080:localhost:80", "portmux")

        assert result is None

    def test_window_not_found(self, mocker):
        mock_session = MagicMock()
        mock_session.windows.get.return_value = None
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = get_window_diagnostics("nonexistent", "portmux")

        assert result is None

    def test_no_active_pane(self, mocker):
        mock_window = MagicMock()
        mock_window.active_pane = None

        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = get_window_diagnostics("L:8080:localhost:80", "portmux")

        assert result is None

    def test_dead_pane(self, mocker):
        mock_pane = MagicMock()
        mock_pane.pane_pid = "99999"
        mock_pane.pane_current_command = "ssh"
        mock_pane.pane_dead_status = "255"
        mock_pane.capture_pane.return_value = ["Connection refused"]

        mock_window = MagicMock()
        mock_window.active_pane = mock_pane

        mock_session = MagicMock()
        mock_session.windows.get.return_value = mock_window
        mocker.patch("portmux.tmux.windows._get_session", return_value=mock_session)

        result = get_window_diagnostics("L:8080:localhost:80", "portmux")

        assert result.pane_dead is True
        assert result.pane_dead_status == "255"
        assert result.pane_content == ["Connection refused"]
