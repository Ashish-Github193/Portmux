"""Tmux session management functions for PortMUX."""

from __future__ import annotations

import libtmux
from libtmux.exc import LibTmuxException, TmuxCommandNotFound, TmuxSessionExists

from ..exceptions import TmuxError


def _get_server() -> libtmux.Server:
    """Get a libtmux Server instance.

    Returns:
        libtmux Server connected to the default socket

    Raises:
        TmuxError: If tmux is not installed
    """
    try:
        return libtmux.Server()
    except TmuxCommandNotFound:
        raise TmuxError("tmux is not installed or not found in PATH")


def create_session(session_name: str = "portmux") -> bool:
    """Create a new tmux session dedicated to port forwards.

    Args:
        session_name: Name of the tmux session to create

    Returns:
        True if successful, False if session already exists

    Raises:
        TmuxError: If tmux command fails for reasons other than session existing
    """
    try:
        server = _get_server()
        server.new_session(session_name=session_name, attach=False)
        return True
    except TmuxSessionExists:
        return False
    except TmuxCommandNotFound:
        raise TmuxError("tmux is not installed or not found in PATH")
    except LibTmuxException as e:
        raise TmuxError(f"Failed to create session '{session_name}': {e}")


def session_exists(session_name: str = "portmux") -> bool:
    """Check if the portmux tmux session exists.

    Args:
        session_name: Name of the tmux session to check

    Returns:
        True if session exists, False otherwise

    Raises:
        TmuxError: If tmux command fails
    """
    try:
        server = _get_server()
        return server.has_session(session_name)
    except TmuxCommandNotFound:
        raise TmuxError("tmux is not installed or not found in PATH")
    except LibTmuxException:
        return False


def kill_session(session_name: str = "portmux") -> bool:
    """Destroy the portmux tmux session and all its windows.

    Args:
        session_name: Name of the tmux session to kill

    Returns:
        True if successful

    Raises:
        TmuxError: If tmux command fails
    """
    try:
        server = _get_server()
        session = server.sessions.get(session_name=session_name, default=None)
        if session is None:
            return True  # Already gone, consider success
        session.kill()
        return True
    except TmuxCommandNotFound:
        raise TmuxError("tmux is not installed or not found in PATH")
    except LibTmuxException as e:
        raise TmuxError(f"Failed to kill session '{session_name}': {e}")
