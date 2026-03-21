"""Refresh command for PortMUX CLI."""

from __future__ import annotations

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..utils import handle_error


@click.command()
@click.argument("name", required=False)
@click.option("--all", "refresh_all", is_flag=True, help="Refresh all forwards")
@click.option("--delay", type=float, help="Delay between kill and recreate (seconds)")
@click.option(
    "--reload-startup", is_flag=True, help="Re-execute startup commands after refresh"
)
@click.pass_context
def refresh(
    ctx: click.Context, name: str, refresh_all: bool, delay: float, reload_startup: bool
):
    """Refresh SSH port forwards by recreating them.

    NAME: Forward name to refresh (e.g., 'L:8080:localhost:80')

    Useful for reconnecting after network issues or server restarts.
    Optionally re-execute startup commands after refreshing forwards.

    Examples:

        portmux refresh L:8080:localhost:80   # Refresh specific forward

        portmux refresh --all                 # Refresh all forwards

        portmux refresh --all --delay 2       # Refresh with 2 second delay

        portmux refresh --all --reload-startup # Refresh and re-run startup commands
    """
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        # Validate arguments early
        if not refresh_all and not name:
            raise click.UsageError("Must specify forward name or use --all flag")

        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        # Check if session exists
        if not svc.session_is_active():
            output.error(f"Session '{session_name}' is not active")
            output.info("Run 'portmux init' to create the session")
            return

        # Handle refresh all
        if refresh_all:
            svc.refresh_all(
                delay=delay,
                reload_startup=reload_startup,
                verbose=verbose,
            )
            return

        # Handle single forward refresh
        forwards = svc.list_forwards()
        forward_exists = any(f.name == name for f in forwards)
        if not forward_exists:
            output.error(f"Forward '{name}' not found")
            output.info("Use 'portmux list' to see active forwards")
            return

        # Use config default delay if not specified
        effective_delay = delay if delay is not None else config.reconnect_delay

        if verbose or (delay is not None and delay != config.reconnect_delay):
            output.info(f"Refreshing forward '{name}' with {effective_delay}s delay...")

        svc.refresh_forward(name, verbose=verbose)
        output.success(f"Successfully refreshed forward '{name}'")

        # Handle startup reload for single forward
        if reload_startup:
            svc.handle_startup_reload(verbose)

    except click.UsageError:
        raise
    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
