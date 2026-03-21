"""Tunnel backend protocol for PortMUX."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import TunnelDiagnostics, TunnelInfo


@runtime_checkable
class TunnelBackend(Protocol):
    """Protocol defining the tunnel execution backend.

    Abstracts session and tunnel lifecycle operations so that
    different backends (tmux, subprocess, systemd) can be swapped.
    """

    def create_session(self, session_name: str) -> bool: ...

    def session_exists(self, session_name: str) -> bool: ...

    def kill_session(self, session_name: str) -> bool: ...

    def create_tunnel(self, name: str, command: str, session_name: str) -> bool: ...

    def kill_tunnel(self, name: str, session_name: str) -> bool: ...

    def tunnel_exists(self, name: str, session_name: str) -> bool: ...

    def list_tunnels(self, session_name: str) -> list[TunnelInfo]: ...

    def get_tunnel_diagnostics(
        self, name: str, session_name: str
    ) -> TunnelDiagnostics | None: ...
