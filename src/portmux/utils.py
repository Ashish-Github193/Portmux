"""CLI utility functions for PortMUX."""

from __future__ import annotations

import click
from rich.table import Table

from .exceptions import ConfigError, PortMuxError, SSHError, TmuxError
from .models import ForwardInfo
from .core.output import Output


def handle_error(error: PortMuxError, output: Output | None = None) -> None:
    """Handle and display PortMUX errors with appropriate formatting.

    Args:
        error: The PortMUX error to handle
        output: Output channel (creates default if None)
    """
    if output is None:
        output = Output()

    if isinstance(error, TmuxError):
        output.error(f"Tmux Error: {error}")
        if "not installed" in str(error):
            output.warning("Hint: Install tmux with your package manager")
    elif isinstance(error, SSHError):
        output.error(f"SSH Error: {error}")
    elif isinstance(error, ConfigError):
        output.error(f"Config Error: {error}")
    else:
        output.error(f"Error: {error}")


def create_forwards_table(
    forwards: list[ForwardInfo], include_status: bool = True
) -> Table:
    """Create a Rich table for displaying forwards.

    Args:
        forwards: List of ForwardInfo objects
        include_status: Whether to include status column

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold blue")

    table.add_column("Name", style="cyan")
    table.add_column("Direction", style="magenta", width=10)
    table.add_column("Specification", style="green")

    if include_status:
        table.add_column("Status", style="yellow", width=10)

    for forward in forwards:
        direction_display = "Local" if forward.direction == "L" else "Remote"

        row = [forward.name, direction_display, forward.spec]

        if include_status:
            # Simple status based on tmux window flags
            status = "Running"
            row.append(status)

        table.add_row(*row)

    return table


def validate_direction(direction: str) -> str:
    """Validate and normalize direction argument.

    Args:
        direction: Direction string to validate

    Returns:
        Normalized direction ('L' or 'R')

    Raises:
        click.BadParameter: If direction is invalid
    """
    direction = direction.upper()
    if direction not in ("L", "R", "LOCAL", "REMOTE"):
        raise click.BadParameter(
            f"Invalid direction '{direction}'. Must be 'L'/'LOCAL' or 'R'/'REMOTE'"
        )

    # Normalize to single letter
    if direction in ("LOCAL", "L"):
        return "L"
    else:  # REMOTE or R
        return "R"


def validate_port_spec(spec: str) -> str:
    """Validate port specification format.

    Args:
        spec: Port specification to validate

    Returns:
        The validated spec string

    Raises:
        click.BadParameter: If spec is invalid
    """
    # Import here to avoid circular imports
    from .ssh.forwards import parse_port_spec

    try:
        parse_port_spec(spec)
        return spec
    except Exception as e:
        raise click.BadParameter(f"Invalid port specification: {e}")


def confirm_destructive_action(message: str, force: bool = False) -> bool:
    """Confirm destructive actions with user.

    Args:
        message: Confirmation message to display
        force: If True, skip confirmation

    Returns:
        True if user confirms or force is True
    """
    if force:
        return True

    return click.confirm(message)
