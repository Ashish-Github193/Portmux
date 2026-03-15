"""Status command for PortMUX CLI."""

from __future__ import annotations

import click

from ..config import load_config
from ..output import Output
from ..service import PortmuxService
from ..utils import create_forwards_table, handle_error


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
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        status_info = svc.get_status()

        if not status_info["session_active"]:
            output.panel(
                f"[red]Session '{session_name}' is not active[/red]\n"
                f"[blue]Run 'portmux init' to create the session[/blue]",
                title="PortMUX Status",
                border_style="red",
            )
            return

        # Display session info
        forwards = status_info["forwards"]
        session_info = f"[green]Session '{session_name}' is active[/green]"

        if forwards:
            session_info += f"\n[blue]{len(forwards)} active forward(s)[/blue]"
        else:
            session_info += f"\n[yellow]No active forwards[/yellow]"

        output.panel(session_info, title="PortMUX Status", border_style="green")

        # Display forwards table if any exist
        if forwards:
            output.print("\n[bold]Active Forwards:[/bold]")
            table = create_forwards_table(forwards, include_status=True)
            output.table(table)

            if check_connections:
                output.print(
                    "\n[yellow]Connection checking not implemented yet[/yellow]"
                )
        else:
            output.print("\n[yellow]No forwards to display[/yellow]")
            output.info("Use 'portmux add' to create new forwards")

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
