"""Status command for PortMUX CLI."""

from __future__ import annotations

import asyncio

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import MONITOR_WINDOW, PortmuxService
from ..health.logger import HealthLogger
from ..utils import create_forwards_table, handle_error


@click.command()
@click.pass_context
def status(ctx: click.Context):
    """Show PortMUX session status and active forwards.

    Displays information about the tmux session and all active port forwards
    with health check results. Shows recent error events from the health log.
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

        # Show monitor status
        monitor_running = svc.backend.tunnel_exists(MONITOR_WINDOW, svc.session_name)
        if monitor_running:
            output.dim(f"Monitor: running ({MONITOR_WINDOW})")

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

        # Show recent error events from health log
        logger = HealthLogger()
        recent_errors = logger.read_recent_errors(minutes=10)
        if recent_errors:
            output.print("")
            output.warning(f"Recent events ({len(recent_errors)}):")
            for line in recent_errors[-5:]:
                output.error(f"  {line}")
            if len(recent_errors) > 5:
                output.dim(
                    f"  ... and {len(recent_errors) - 5} more"
                    " (use 'portmux watch --tail 20' to see all)"
                )

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
