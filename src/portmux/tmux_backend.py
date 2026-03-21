"""Tmux-based tunnel backend for PortMUX."""

from __future__ import annotations

from .models import TunnelInfo
from . import session as _session
from . import windows as _windows


class TmuxBackend:
    """TunnelBackend implementation using tmux sessions and windows."""

    def create_session(self, session_name: str) -> bool:
        return _session.create_session(session_name)

    def session_exists(self, session_name: str) -> bool:
        return _session.session_exists(session_name)

    def kill_session(self, session_name: str) -> bool:
        return _session.kill_session(session_name)

    def create_tunnel(self, name: str, command: str, session_name: str) -> bool:
        return _windows.create_window(name, command, session_name)

    def kill_tunnel(self, name: str, session_name: str) -> bool:
        return _windows.kill_window(name, session_name)

    def tunnel_exists(self, name: str, session_name: str) -> bool:
        return _windows.window_exists(name, session_name)

    def list_tunnels(self, session_name: str) -> list[TunnelInfo]:
        raw_windows = _windows.list_windows(session_name)
        return [
            TunnelInfo(name=w["name"], status=w["status"], command=w["command"])
            for w in raw_windows
        ]
