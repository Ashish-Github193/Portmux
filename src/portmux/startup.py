"""Startup command execution system for PortMUX."""

from __future__ import annotations

import shlex
import subprocess

from .exceptions import ConfigError, PortMuxError
from .models import PortmuxConfig, StartupCommand
from .output import Output


def execute_startup_commands(
    config: PortmuxConfig,
    session_name: str,
    verbose: bool = False,
    output: Output | None = None,
) -> bool:
    """Execute startup commands from configuration.

    Args:
        config: Loaded PortmuxConfig
        session_name: Name of the tmux session
        verbose: Enable verbose output
        output: Output channel (creates default if None)

    Returns:
        True if all commands succeeded, False otherwise

    Raises:
        PortMuxError: If startup command execution fails critically
    """
    if output is None:
        output = Output()

    startup = config.startup

    # Check if startup commands are enabled
    if not startup.auto_execute:
        output.verbose("Startup commands disabled in configuration", verbose)
        return True

    commands = startup.commands
    if not commands:
        output.verbose("No startup commands configured", verbose)
        return True

    output.verbose(f"Executing {len(commands)} startup command(s)...", verbose)

    success_count = 0
    with output.progress_context() as progress:
        for i, command in enumerate(commands):
            progress.update(
                f"Executing command {i + 1}/{len(commands)}: {command[:50]}..."
            )

            try:
                success = execute_startup_command(
                    command, session_name, verbose, output
                )
                if success:
                    success_count += 1
                    if verbose:
                        output.success(f"✓ Command {i + 1} succeeded")
                else:
                    output.error(f"✗ Command {i + 1} failed: {command}")

            except Exception as e:
                output.error(f"✗ Command {i + 1} error: {e}")

            progress.finish()

    # Report results
    if success_count == len(commands):
        output.success(f"All {len(commands)} startup commands executed successfully")
        return True
    else:
        output.warning(f"{success_count}/{len(commands)} startup commands succeeded")
        return False


def execute_startup_command(
    command: str,
    session_name: str,
    verbose: bool = False,
    output: Output | None = None,
) -> bool:
    """Execute a single startup command.

    Args:
        command: Command string to execute
        session_name: Name of the tmux session
        verbose: Enable verbose output
        output: Output channel (creates default if None)

    Returns:
        True if command succeeded, False otherwise

    Raises:
        ConfigError: If command format is invalid
        PortMuxError: If command execution fails critically
    """
    if output is None:
        output = Output()

    # Parse and validate the command
    parsed_command = parse_startup_command(command)

    output.verbose(f"Executing: {command}", verbose)

    try:
        # Build the actual command to execute
        if parsed_command.command == "portmux":
            # Modify portmux commands to use the correct session
            cmd_args = parsed_command.args.copy()

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
                output.dim(result.stdout.strip())
            return True
        else:
            if result.stderr:
                output.error(f"Command error: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        output.error(f"Command timed out: {command}")
        return False
    except subprocess.SubprocessError as e:
        output.error(f"Command execution failed: {e}")
        return False
    except Exception as e:
        raise PortMuxError(f"Startup command execution failed: {e}")


def parse_startup_command(command: str) -> StartupCommand:
    """Parse and validate a startup command.

    Args:
        command: Command string to parse

    Returns:
        StartupCommand with parsed information

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

    return StartupCommand(
        command=cmd,
        args=args,
        original=command,
    )


def validate_startup_commands(commands: list[str]) -> tuple[bool, list[str]]:
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
            errors.append(f"Command {i + 1}: {e}")

    return len(errors) == 0, errors


def get_startup_command_preview(config: PortmuxConfig) -> list[str]:
    """Get a preview of startup commands that would be executed.

    Args:
        config: Loaded PortmuxConfig

    Returns:
        List of command strings that would be executed
    """
    if not config.startup.auto_execute:
        return []

    return config.startup.commands


def startup_commands_enabled(config: PortmuxConfig) -> bool:
    """Check if startup commands are enabled in configuration.

    Args:
        config: Loaded PortmuxConfig

    Returns:
        True if startup commands are enabled and available
    """
    return config.startup.auto_execute and len(config.startup.commands) > 0
