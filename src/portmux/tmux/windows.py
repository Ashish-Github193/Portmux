"""Tmux window management functions for PortMUX."""

from __future__ import annotations

import libtmux
from libtmux.exc import LibTmuxException, TmuxCommandNotFound

from ..exceptions import TmuxError


def _get_session(session_name: str) -> libtmux.Session | None:
    """Get a libtmux Session by name.

    Returns:
        Session object, or None if not found

    Raises:
        TmuxError: If tmux is not installed
    """
    try:
        server = libtmux.Server()
        return server.sessions.get(session_name=session_name, default=None)
    except TmuxCommandNotFound:
        raise TmuxError("tmux is not installed or not found in PATH")


def create_window(name: str, command: str, session_name: str = "portmux") -> bool:
    """Create a new tmux window with given name and run command.

    Args:
        name: Name of the tmux window
        command: Command to run in the window
        session_name: Name of the tmux session

    Returns:
        True if successful

    Raises:
        TmuxError: If tmux command fails
    """
    try:
        session = _get_session(session_name)
        if session is None:
            raise TmuxError(
                f"Failed to create window '{name}': session '{session_name}' not found"
            )
        session.new_window(window_name=name, window_shell=command, attach=False)
        return True
    except TmuxError:
        raise
    except LibTmuxException as e:
        raise TmuxError(f"Failed to create window '{name}': {e}")


def kill_window(name: str, session_name: str = "portmux") -> bool:
    """Kill a specific tmux window by name.

    Args:
        name: Name of the tmux window to kill
        session_name: Name of the tmux session

    Returns:
        True if successful

    Raises:
        TmuxError: If tmux command fails
    """
    try:
        session = _get_session(session_name)
        if session is None:
            return True  # Session gone, window is gone too
        window = session.windows.get(window_name=name, default=None)
        if window is None:
            return True  # Already gone, consider success
        window.kill()
        return True
    except TmuxError:
        raise
    except LibTmuxException as e:
        raise TmuxError(f"Failed to kill window '{name}': {e}")


def list_windows(session_name: str = "portmux") -> list[dict[str, str]]:
    """Get all windows in session with their details.

    Args:
        session_name: Name of the tmux session

    Returns:
        List of dicts containing window details: name, status, command

    Raises:
        TmuxError: If tmux command fails
    """
    try:
        session = _get_session(session_name)
        if session is None:
            return []  # Session doesn't exist, return empty list
        windows = []
        for window in session.windows:
            pane = window.active_pane
            windows.append(
                {
                    "name": window.name,
                    "status": window.window_raw_flags or "",
                    "command": pane.pane_current_command if pane else "",
                }
            )
        return windows
    except TmuxError:
        raise
    except LibTmuxException as e:
        raise TmuxError(f"Failed to list windows: {e}")


def window_exists(name: str, session_name: str = "portmux") -> bool:
    """Check if a window with given name exists.

    Args:
        name: Name of the window to check
        session_name: Name of the tmux session

    Returns:
        True if window exists, False otherwise

    Raises:
        TmuxError: If tmux command fails
    """
    session = _get_session(session_name)
    if session is None:
        return False
    return session.windows.get(window_name=name, default=None) is not None
