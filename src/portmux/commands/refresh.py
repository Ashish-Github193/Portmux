"""Refresh command for PortMUX CLI."""

import time

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import load_config
from ..forwards import list_forwards, refresh_forward
from ..session import session_exists
from ..utils import handle_error

console = Console()


@click.command()
@click.argument("name", required=False)
@click.option("--all", "refresh_all", is_flag=True, help="Refresh all forwards")
@click.option("--delay", type=float, help="Delay between kill and recreate (seconds)")
@click.pass_context
def refresh(ctx: click.Context, name: str, refresh_all: bool, delay: float):
    """Refresh SSH port forwards by recreating them.

    NAME: Forward name to refresh (e.g., 'L:8080:localhost:80')

    Useful for reconnecting after network issues or server restarts.

    Examples:

        portmux refresh L:8080:localhost:80   # Refresh specific forward

        portmux refresh --all                 # Refresh all forwards

        portmux refresh --all --delay 2       # Refresh with 2 second delay
    """
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]

    try:
        # Validate arguments early
        if not refresh_all and not name:
            raise click.UsageError("Must specify forward name or use --all flag")

        # Check if session exists
        if not session_exists(session_name):
            console.print(f"[red]Session '{session_name}' is not active[/red]")
            console.print("[blue]Run 'portmux init' to create the session[/blue]")
            return

        # Load config for default delay
        config = load_config(ctx.obj.get("config"))
        if delay is None:
            delay = config.get("reconnect_delay", 1)

        # Get current forwards
        forwards = list_forwards(session_name)

        # Handle refresh all
        if refresh_all:
            if not forwards:
                console.print(
                    f"[yellow]No forwards to refresh in session '{session_name}'[/yellow]"
                )
                return

            console.print(
                f"[blue]Refreshing all {len(forwards)} forward(s) with {delay}s delay...[/blue]"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:

                refreshed_count = 0
                for i, forward in enumerate(forwards):
                    task = progress.add_task(
                        f"Refreshing {forward['name']} ({i+1}/{len(forwards)})",
                        total=None,
                    )

                    try:
                        refresh_forward(forward["name"], session_name)
                        refreshed_count += 1
                        if verbose:
                            console.print(
                                f"[green]Refreshed forward '{forward['name']}'[/green]"
                            )

                        # Add delay between refreshes (except for last one)
                        if i < len(forwards) - 1 and delay > 0:
                            time.sleep(delay)

                    except Exception as e:
                        console.print(
                            f"[red]Failed to refresh '{forward['name']}': {e}[/red]"
                        )

                    progress.remove_task(task)

            console.print(
                f"[green]Successfully refreshed {refreshed_count}/{len(forwards)} forward(s)[/green]"
            )
            return

        # Handle single forward refresh
        # Check if forward exists
        forward_exists = any(f["name"] == name for f in forwards)
        if not forward_exists:
            console.print(f"[red]Forward '{name}' not found[/red]")
            console.print("[blue]Use 'portmux list' to see active forwards[/blue]")
            return

        # Refresh the forward
        if verbose or delay != config.get("reconnect_delay", 1):
            console.print(
                f"[blue]Refreshing forward '{name}' with {delay}s delay...[/blue]"
            )

        refresh_forward(name, session_name)
        console.print(f"[green]Successfully refreshed forward '{name}'[/green]")

    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))
