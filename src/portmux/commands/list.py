"""List command for PortMUX CLI."""

from __future__ import annotations

import json

import click

from ..config import load_config
from ..output import Output
from ..service import PortmuxService
from ..utils import create_forwards_table, handle_error


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
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        # Check if session exists
        if not svc.session_is_active():
            if output_json:
                click.echo(
                    json.dumps(
                        {"session": session_name, "active": False, "forwards": []}
                    )
                )
            else:
                output.error(f"Session '{session_name}' is not active")
                output.info("Run 'portmux init' to create the session")
            return

        # Get forwards
        forwards = svc.list_forwards()

        if output_json:
            # JSON output for scripting — convert ForwardInfo to dicts
            forwards_data = [
                {
                    "name": f.name,
                    "direction": f.direction,
                    "spec": f.spec,
                    "status": f.status,
                    "command": f.command,
                }
                for f in forwards
            ]
            output_data = {"session": session_name, "active": True, "forwards": forwards_data}
            click.echo(json.dumps(output_data, indent=2))
        else:
            # Human-readable table output
            if not forwards:
                output.warning(
                    f"No active forwards in session '{session_name}'"
                )
                output.info("Use 'portmux add' to create new forwards")
            else:
                output.verbose(
                    f"Active forwards in session '{session_name}':\n", verbose
                )

                table = create_forwards_table(forwards, include_status=include_status)
                output.table(table)

                output.success(f"\n{len(forwards)} forward(s) active")

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
