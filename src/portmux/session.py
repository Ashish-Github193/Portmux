"""Tmux session management functions for PortMUX."""

import subprocess
from typing import Optional

from .exceptions import TmuxError


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
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        elif "duplicate session" in result.stderr:
            return False
        else:
            raise TmuxError(f"Failed to create session '{session_name}': {result.stderr}")
            
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")


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
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
        
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")


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
        result = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        elif "session not found" in result.stderr:
            return True  # Already gone, consider success
        else:
            raise TmuxError(f"Failed to kill session '{session_name}': {result.stderr}")
            
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")