"""Watch command for PortMUX CLI."""

from __future__ import annotations

import asyncio

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..utils import handle_error


@click.command()
@click.option(
    "--interval",
    type=float,
    help="Check interval in seconds (default: from config or 30s)",
)
@click.pass_context
def watch(ctx: click.Context, interval: float | None):
    """Continuously monitor tunnel health with auto-restart.

    Periodically checks all active tunnels for:
    - SSH process alive
    - Stuck passphrase or connection errors
    - TCP port responsiveness (local forwards)

    Dead tunnels are automatically restarted up to max_retries times.
    Press Ctrl+C to stop.
    """
    session_name = ctx.obj["session"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        if not svc.session_is_active():
            output.error(f"Session '{session_name}' is not active")
            output.info("Run 'portmux init' to create the session")
            return

        monitor = svc.create_monitor()
        effective_interval = interval or config.monitor.check_interval
        output.info(
            f"Watching tunnels every {effective_interval}s "
            f"(max_retries={config.max_retries}, "
            f"auto_reconnect={'on' if config.monitor.auto_reconnect else 'off'})"
        )
        output.dim("Press Ctrl+C to stop\n")

        asyncio.run(monitor.run(interval=interval))

    except KeyboardInterrupt:
        output.info("\nMonitor stopped")
    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
