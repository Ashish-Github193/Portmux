"""SSH port forwarding functions for PortMUX."""

import re
from typing import List, Dict, Optional

from .windows import create_window, kill_window, list_windows, window_exists
from .exceptions import SSHError, TmuxError


def parse_port_spec(spec: str) -> Dict[str, str]:
    """Validate and parse port specifications.
    
    Args:
        spec: Port specification like "8080:localhost:80" or "9000:192.168.1.10:443"
        
    Returns:
        Dict with parsed components: local_port, remote_host, remote_port
        
    Raises:
        SSHError: If port specification is invalid
    """
    # Pattern: local_port:remote_host:remote_port
    pattern = r'^(\d{1,5}):([^:]+):(\d{1,5})$'
    match = re.match(pattern, spec)
    
    if not match:
        raise SSHError(f"Invalid port specification '{spec}'. Expected format: 'local_port:remote_host:remote_port'")
    
    local_port, remote_host, remote_port = match.groups()
    
    # Validate port ranges
    for port_name, port_str in [("local", local_port), ("remote", remote_port)]:
        port_num = int(port_str)
        if not (1 <= port_num <= 65535):
            raise SSHError(f"Invalid {port_name} port {port_num}. Must be between 1 and 65535")
    
    return {
        'local_port': local_port,
        'remote_host': remote_host,
        'remote_port': remote_port
    }


def add_forward(direction: str, spec: str, host: str, identity: Optional[str] = None, session_name: str = "portmux") -> str:
    """Create SSH port forward in new tmux window.
    
    Args:
        direction: "L" for local, "R" for remote
        spec: Port specification like "8080:localhost:80"
        host: SSH target like "user@hostname"
        identity: Path to SSH key file (optional)
        session_name: Name of the tmux session
        
    Returns:
        Window name created
        
    Raises:
        SSHError: If direction is invalid or port spec is malformed
        TmuxError: If tmux operations fail
    """
    if direction not in ("L", "R"):
        raise SSHError(f"Invalid direction '{direction}'. Must be 'L' (local) or 'R' (remote)")
    
    # Validate port specification
    parsed_spec = parse_port_spec(spec)
    
    # Create window name
    window_name = f"{direction}:{spec}"
    
    # Check if window already exists
    if window_exists(window_name, session_name):
        raise SSHError(f"Forward '{window_name}' already exists")
    
    # Build SSH command
    ssh_args = ["ssh", "-N"]
    
    if direction == "L":
        ssh_args.extend(["-L", f"{parsed_spec['local_port']}:{parsed_spec['remote_host']}:{parsed_spec['remote_port']}"])
    else:  # direction == "R"
        ssh_args.extend(["-R", f"{parsed_spec['local_port']}:{parsed_spec['remote_host']}:{parsed_spec['remote_port']}"])
    
    if identity:
        ssh_args.extend(["-i", identity])
    
    ssh_args.append(host)
    
    # Create the window with SSH command
    ssh_command = " ".join(ssh_args)
    create_window(window_name, ssh_command, session_name)
    
    return window_name


def remove_forward(name: str, session_name: str = "portmux") -> bool:
    """Remove SSH forward by killing its tmux window.
    
    Args:
        name: Window name (e.g., "L:8080:localhost:80")
        session_name: Name of the tmux session
        
    Returns:
        True if successful
        
    Raises:
        TmuxError: If tmux operations fail
    """
    return kill_window(name, session_name)


def list_forwards(session_name: str = "portmux") -> List[Dict[str, str]]:
    """List all active SSH forwards.
    
    Args:
        session_name: Name of the tmux session
        
    Returns:
        List of dicts with forward details: name, direction, spec, status, command
        
    Raises:
        TmuxError: If tmux operations fail
    """
    windows = list_windows(session_name)
    forwards = []
    
    for window in windows:
        name = window['name']
        
        # Parse window name to extract forward details
        if ':' in name and name[0] in ('L', 'R'):
            direction = name[0]
            spec = name[2:]  # Skip "L:" or "R:"
            
            forwards.append({
                'name': name,
                'direction': direction,
                'spec': spec,
                'status': window['status'],
                'command': window['command']
            })
    
    return forwards


def refresh_forward(name: str, session_name: str = "portmux") -> bool:
    """Remove existing forward and recreate it with same parameters.
    
    Args:
        name: Window name (e.g., "L:8080:localhost:80")
        session_name: Name of the tmux session
        
    Returns:
        True if successful
        
    Raises:
        SSHError: If forward doesn't exist or can't be parsed
        TmuxError: If tmux operations fail
    """
    # Get the current forward details before removing it
    forwards = list_forwards(session_name)
    current_forward = None
    
    for forward in forwards:
        if forward['name'] == name:
            current_forward = forward
            break
    
    if not current_forward:
        raise SSHError(f"Forward '{name}' not found")
    
    # Parse the current command to extract parameters
    command_parts = current_forward['command'].split()
    if len(command_parts) < 2 or command_parts[0] != 'ssh':
        raise SSHError(f"Cannot parse SSH command for forward '{name}'")
    
    # Extract host (last argument)
    host = command_parts[-1]
    
    # Extract identity if present
    identity = None
    if '-i' in command_parts:
        identity_index = command_parts.index('-i')
        if identity_index + 1 < len(command_parts):
            identity = command_parts[identity_index + 1]
    
    # Remove the current forward
    remove_forward(name, session_name)
    
    # Recreate it
    direction = current_forward['direction']
    spec = current_forward['spec']
    
    try:
        add_forward(direction, spec, host, identity, session_name)
        return True
    except (SSHError, TmuxError):
        # If recreation fails, we've already removed the original
        raise