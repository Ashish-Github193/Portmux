"""Status command for PortMUX CLI."""

import click
from rich.console import Console
from rich.panel import Panel

from ..forwards import list_forwards
from ..session import session_exists
from ..utils import create_forwards_table, handle_error

console = Console()


@click.command()
@click.option(
    "--check-connections",
    is_flag=True,
    help="Test forward connectivity (not implemented yet)",
)
@click.pass_context
def status(ctx: click.Context, check_connections: bool):
    """Show PortMUX session status and active forwards.

    Displays information about the tmux session and all active port forwards.
    """
    session_name = ctx.obj["session"]
    ctx.obj["verbose"]

    try:
        # Check session status
        session_active = session_exists(session_name)

        if not session_active:
            console.print(
                Panel(
                    f"[red]Session '{session_name}' is not active[/red]\n"
                    f"[blue]Run 'portmux init' to create the session[/blue]",
                    title="PortMUX Status",
                    border_style="red",
                )
            )
            return

        # Get forwards
        forwards = list_forwards(session_name)

        # Display session info
        session_info = f"[green]Session '{session_name}' is active[/green]"

        if forwards:
            session_info += f"\n[blue]{len(forwards)} active forward(s)[/blue]"
        else:
            session_info += f"\n[yellow]No active forwards[/yellow]"

        console.print(Panel(session_info, title="PortMUX Status", border_style="green"))

        # Display forwards table if any exist
        if forwards:
            console.print("\n[bold]Active Forwards:[/bold]")
            table = create_forwards_table(forwards, include_status=True)
            console.print(table)

            if check_connections:
                console.print(
                    "\n[yellow]Connection checking not implemented yet[/yellow]"
                )
        else:
            console.print("\n[yellow]No forwards to display[/yellow]")
            console.print("[blue]Use 'portmux add' to create new forwards[/blue]")

    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))
