"""Tests for TmuxBackend tunnel backend."""

from unittest.mock import patch

from portmux.backend import TunnelBackend, TmuxBackend
from portmux.models import TunnelInfo


class TestTmuxBackendProtocol:
    def test_satisfies_tunnel_backend_protocol(self):
        backend = TmuxBackend()
        assert isinstance(backend, TunnelBackend)


class TestTmuxBackendSession:
    @patch("portmux.tmux.session.create_session")
    def test_create_session(self, mock_create):
        mock_create.return_value = True
        backend = TmuxBackend()

        result = backend.create_session("test")

        assert result is True
        mock_create.assert_called_once_with("test")

    @patch("portmux.tmux.session.session_exists")
    def test_session_exists(self, mock_exists):
        mock_exists.return_value = True
        backend = TmuxBackend()

        result = backend.session_exists("test")

        assert result is True
        mock_exists.assert_called_once_with("test")

    @patch("portmux.tmux.session.kill_session")
    def test_kill_session(self, mock_kill):
        mock_kill.return_value = True
        backend = TmuxBackend()

        result = backend.kill_session("test")

        assert result is True
        mock_kill.assert_called_once_with("test")


class TestTmuxBackendTunnel:
    @patch("portmux.tmux.windows.create_window")
    def test_create_tunnel(self, mock_create):
        mock_create.return_value = True
        backend = TmuxBackend()

        result = backend.create_tunnel(
            "L:8080:localhost:80", "ssh -N -L 8080:localhost:80 user@host", "portmux"
        )

        assert result is True
        mock_create.assert_called_once_with(
            "L:8080:localhost:80", "ssh -N -L 8080:localhost:80 user@host", "portmux"
        )

    @patch("portmux.tmux.windows.kill_window")
    def test_kill_tunnel(self, mock_kill):
        mock_kill.return_value = True
        backend = TmuxBackend()

        result = backend.kill_tunnel("L:8080:localhost:80", "portmux")

        assert result is True
        mock_kill.assert_called_once_with("L:8080:localhost:80", "portmux")

    @patch("portmux.tmux.windows.window_exists")
    def test_tunnel_exists(self, mock_exists):
        mock_exists.return_value = True
        backend = TmuxBackend()

        result = backend.tunnel_exists("L:8080:localhost:80", "portmux")

        assert result is True
        mock_exists.assert_called_once_with("L:8080:localhost:80", "portmux")

    @patch("portmux.tmux.windows.list_windows")
    def test_list_tunnels(self, mock_list):
        mock_list.return_value = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
        ]
        backend = TmuxBackend()

        result = backend.list_tunnels("portmux")

        assert result == [
            TunnelInfo(name="L:8080:localhost:80", status="-", command="ssh"),
            TunnelInfo(name="R:9000:localhost:9000", status="*", command="ssh"),
        ]
        mock_list.assert_called_once_with("portmux")

    @patch("portmux.tmux.windows.list_windows")
    def test_list_tunnels_empty(self, mock_list):
        mock_list.return_value = []
        backend = TmuxBackend()

        result = backend.list_tunnels("portmux")

        assert result == []
