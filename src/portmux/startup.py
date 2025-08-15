"""Startup command execution system for PortMUX."""

import shlex
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_startup_config
from .exceptions import ConfigError, PortMuxError

console = Console()


def execute_startup_commands(
    config: Dict, session_name: str, verbose: bool = False
) -> bool:
    """Execute startup commands from configuration.

    Args:
        config: Loaded configuration dict
        session_name: Name of the tmux session
        verbose: Enable verbose output

    Returns:
        True if all commands succeeded, False otherwise

    Raises:
        PortMuxError: If startup command execution fails critically
    """
    startup_config = get_startup_config(config)

    # Check if startup commands are enabled
    if not startup_config.get("auto_execute", True):
        if verbose:
            console.print("[blue]Startup commands disabled in configuration[/blue]")
        return True

    commands = startup_config.get("commands", [])
    if not commands:
        if verbose:
            console.print("[blue]No startup commands configured[/blue]")
        return True

    if verbose:
        console.print(
            f"[blue]Executing {len(commands)} startup command(s)...[/blue]"
        )

    success_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        for i, command in enumerate(commands):
            task = progress.add_task(
                f"Executing command {i+1}/{len(commands)}: {command[:50]}...",
                total=None,
            )

            try:
                success = execute_startup_command(command, session_name, verbose)
                if success:
                    success_count += 1
                    if verbose:
                        console.print(f"[green]✓ Command {i+1} succeeded[/green]")
                else:
                    console.print(f"[red]✗ Command {i+1} failed: {command}[/red]")

            except Exception as e:
                console.print(f"[red]✗ Command {i+1} error: {e}[/red]")

            progress.remove_task(task)

    # Report results
    if success_count == len(commands):
        console.print(
            f"[green]All {len(commands)} startup commands executed successfully[/green]"
        )
        return True
    else:
        console.print(
            f"[yellow]{success_count}/{len(commands)} startup commands succeeded[/yellow]"
        )
        return False


def execute_startup_command(
    command: str, session_name: str, verbose: bool = False
) -> bool:
    """Execute a single startup command.

    Args:
        command: Command string to execute
        session_name: Name of the tmux session
        verbose: Enable verbose output

    Returns:
        True if command succeeded, False otherwise

    Raises:
        ConfigError: If command format is invalid
        PortMuxError: If command execution fails critically
    """
    # Parse and validate the command
    parsed_command = parse_startup_command(command)
    
    if verbose:
        console.print(f"[blue]Executing: {command}[/blue]")

    try:
        # Build the actual command to execute
        # We need to modify the command to use the correct session name
        if parsed_command["command"] == "portmux":
            # Modify portmux commands to use the correct session
            cmd_args = parsed_command["args"].copy()
            
            # Add session argument if not already present
            if "--session" not in cmd_args and "-s" not in cmd_args:
                cmd_args = ["--session", session_name] + cmd_args
                
            # Build the full command using the installed portmux script
            full_command = ["portmux"] + cmd_args
        else:
            # For non-portmux commands, execute as-is
            full_command = shlex.split(command)

        # Execute the command
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for startup commands
        )

        if result.returncode == 0:
            if verbose and result.stdout:
                console.print(f"[dim]{result.stdout.strip()}[/dim]")
            return True
        else:
            if result.stderr:
                console.print(f"[red]Command error: {result.stderr.strip()}[/red]")
            return False

    except subprocess.TimeoutExpired:
        console.print(f"[red]Command timed out: {command}[/red]")
        return False
    except subprocess.SubprocessError as e:
        console.print(f"[red]Command execution failed: {e}[/red]")
        return False
    except Exception as e:
        raise PortMuxError(f"Startup command execution failed: {e}")


def parse_startup_command(command: str) -> Dict:
    """Parse and validate a startup command.

    Args:
        command: Command string to parse

    Returns:
        Dict with parsed command information

    Raises:
        ConfigError: If command format is invalid
    """
    if not command or not command.strip():
        raise ConfigError("Startup command cannot be empty")

    try:
        # Parse the command into parts
        parts = shlex.split(command.strip())
    except ValueError as e:
        raise ConfigError(f"Invalid command syntax: {e}")

    if not parts:
        raise ConfigError("Startup command cannot be empty after parsing")

    # Extract command and arguments
    cmd = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    # Validate command format
    if cmd == "portmux":
        # Validate portmux commands
        if not args:
            raise ConfigError("PortMUX commands must have subcommands")
        
        valid_subcommands = ["add", "remove", "list", "refresh", "status", "profile"]
        subcommand = args[0]
        
        if subcommand not in valid_subcommands:
            raise ConfigError(f"Invalid PortMUX subcommand: {subcommand}")

    return {
        "command": cmd,
        "args": args,
        "original": command,
    }


def validate_startup_commands(commands: List[str]) -> Tuple[bool, List[str]]:
    """Validate a list of startup commands.

    Args:
        commands: List of command strings to validate

    Returns:
        Tuple of (all_valid, error_messages)
    """
    errors = []
    
    for i, command in enumerate(commands):
        try:
            parse_startup_command(command)
        except ConfigError as e:
            errors.append(f"Command {i+1}: {e}")

    return len(errors) == 0, errors


def get_startup_command_preview(config: Dict) -> List[str]:
    """Get a preview of startup commands that would be executed.

    Args:
        config: Loaded configuration dict

    Returns:
        List of command strings that would be executed
    """
    startup_config = get_startup_config(config)
    
    if not startup_config.get("auto_execute", True):
        return []
        
    return startup_config.get("commands", [])


def startup_commands_enabled(config: Dict) -> bool:
    """Check if startup commands are enabled in configuration.

    Args:
        config: Loaded configuration dict

    Returns:
        True if startup commands are enabled and available
    """
    startup_config = get_startup_config(config)
    return (startup_config.get("auto_execute", True) and 
            len(startup_config.get("commands", [])) > 0)