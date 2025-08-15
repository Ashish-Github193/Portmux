"""List command for PortMUX CLI."""

import json

import click
from rich.console import Console

from ..forwards import list_forwards
from ..session import session_exists
from ..utils import create_forwards_table, handle_error

console = Console()


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option(
    "--status", "include_status", is_flag=True, help="Include connection status"
)
@click.pass_context
def list(ctx: click.Context, output_json: bool, include_status: bool):
    """List all active SSH port forwards.

    Shows a table of all forwards with their direction, specification, and status.
    Use --json for machine-readable output suitable for scripting.
    """
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]

    try:
        # Check if session exists
        if not session_exists(session_name):
            if output_json:
                click.echo(
                    json.dumps(
                        {"session": session_name, "active": False, "forwards": []}
                    )
                )
            else:
                console.print(f"[red]Session '{session_name}' is not active[/red]")
                console.print("[blue]Run 'portmux init' to create the session[/blue]")
            return

        # Get forwards
        forwards = list_forwards(session_name)

        if output_json:
            # JSON output for scripting
            output = {"session": session_name, "active": True, "forwards": forwards}
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable table output
            if not forwards:
                console.print(
                    f"[yellow]No active forwards in session '{session_name}'[/yellow]"
                )
                console.print("[blue]Use 'portmux add' to create new forwards[/blue]")
            else:
                if verbose:
                    console.print(
                        f"[blue]Active forwards in session '{session_name}':[/blue]\n"
                    )

                table = create_forwards_table(forwards, include_status=include_status)
                console.print(table)

                console.print(f"\n[green]{len(forwards)} forward(s) active[/green]")

    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))
