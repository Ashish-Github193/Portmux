"""Status command for PortMUX CLI."""

from __future__ import annotations

import asyncio

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..utils import create_forwards_table, handle_error


@click.command()
@click.pass_context
def status(ctx: click.Context):
    """Show PortMUX session status and active forwards.

    Displays information about the tmux session and all active port forwards
    with health check results.
    """
    session_name = ctx.obj["session"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        status_info = svc.get_status()

        if not status_info["session_active"]:
            output.error(f"Session '{session_name}' is not active")
            output.info("Run 'portmux init' to create the session")
            return

        forwards = status_info["forwards"]

        if not forwards:
            output.warning("No active forwards")
            output.info("Use 'portmux add' to create new forwards")
            return

        if forwards:
            results = asyncio.run(svc.check_health())
            health_map = {r.name: r for r in results}
            for f in forwards:
                result = health_map.get(f.name)
                f.health = result.health.value if result else None

            table = create_forwards_table(forwards, include_status=True)
            output.table(table)

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
