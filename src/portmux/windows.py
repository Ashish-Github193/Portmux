"""Tmux window management functions for PortMUX."""

import subprocess
from typing import List, Dict

from .exceptions import TmuxError


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
        result = subprocess.run(
            ["tmux", "new-window", "-t", session_name, "-n", name, command],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        else:
            raise TmuxError(f"Failed to create window '{name}': {result.stderr}")
            
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")


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
        result = subprocess.run(
            ["tmux", "kill-window", "-t", f"{session_name}:{name}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        elif "window not found" in result.stderr or "can't find window" in result.stderr:
            return True  # Already gone, consider success
        else:
            raise TmuxError(f"Failed to kill window '{name}': {result.stderr}")
            
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")


def list_windows(session_name: str = "portmux") -> List[Dict[str, str]]:
    """Get all windows in session with their details.
    
    Args:
        session_name: Name of the tmux session
        
    Returns:
        List of dicts containing window details: name, status, command
        
    Raises:
        TmuxError: If tmux command fails
    """
    try:
        result = subprocess.run(
            ["tmux", "list-windows", "-t", session_name, "-F", 
             "#{window_name}|#{window_flags}|#{pane_current_command}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            windows = []
            for line in result.stdout.strip().split('\n'):
                if line:  # Skip empty lines
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        windows.append({
                            'name': parts[0],
                            'status': parts[1],
                            'command': parts[2]
                        })
            return windows
        elif "session not found" in result.stderr:
            return []  # Session doesn't exist, return empty list
        else:
            raise TmuxError(f"Failed to list windows: {result.stderr}")
            
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not found in PATH")


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
    windows = list_windows(session_name)
    return any(window['name'] == name for window in windows)