"""Background monitor commands for PortMUX CLI."""

from __future__ import annotations

import asyncio

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import MONITOR_WINDOW
from ..health.logger import HealthLogger
from ..utils import handle_error


@click.group()
@click.pass_context
def monitor(ctx: click.Context):
    """Manage the background health monitor.

    The background monitor runs as a persistent tmux window (_monitor)
    inside the portmux session, logging health events to
    ~/.portmux/health.log
    """
    pass


@monitor.command()
@click.option(
    "--interval",
    type=float,
    help="Check interval in seconds (default: from config or 30s)",
)
@click.pass_context
def start(ctx: click.Context, interval: float | None):
    """Start the background health monitor."""
    session_name = ctx.obj["session"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))

        from ..core.service import PortmuxService

        svc = PortmuxService(config, output, session_name)

        if not svc.session_is_active():
            output.error(f"Session '{session_name}' is not active")
            output.info("Run 'portmux init' to create the session")
            return

        if svc.backend.tunnel_exists(MONITOR_WINDOW, svc.session_name):
            output.warning("Background monitor is already running")
            return

        svc.start_background_monitor()

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))


@monitor.command()
@click.pass_context
def stop(ctx: click.Context):
    """Stop the background health monitor."""
    session_name = ctx.obj["session"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))

        from ..core.service import PortmuxService

        svc = PortmuxService(config, output, session_name)

        if not svc.backend.tunnel_exists(MONITOR_WINDOW, svc.session_name):
            output.warning("Background monitor is not running")
            return

        svc.backend.kill_tunnel(MONITOR_WINDOW, svc.session_name)
        output.success("Background monitor stopped")
        svc.logger.info("Background monitor stopped")
        svc.logger.flush()

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))


@monitor.command()
@click.pass_context
def status(ctx: click.Context):
    """Show background monitor status."""
    session_name = ctx.obj["session"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(ctx.obj.get("config"))

        from ..core.service import PortmuxService

        svc = PortmuxService(config, output, session_name)

        if not svc.session_is_active():
            output.error(f"Session '{session_name}' is not active")
            return

        running = svc.backend.tunnel_exists(MONITOR_WINDOW, svc.session_name)
        if running:
            output.success(f"Monitor: running ({MONITOR_WINDOW})")
            output.info(
                f"Interval: {config.monitor.check_interval}s, "
                f"auto_reconnect: {'on' if config.monitor.auto_reconnect else 'off'}"
            )
            output.info(f"Log: {HealthLogger().log_path}")
        else:
            output.warning("Monitor: not running")
            output.info("Use 'portmux monitor start' to start it")

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))


def _run_daemon(session_name: str, interval: float | None, config_path: str | None):
    """Entry point for the background monitor process inside the tmux window."""
    from ..core.service import PortmuxService

    output = Output()
    config = load_config(config_path)
    svc = PortmuxService(config, output, session_name)

    logger = HealthLogger()
    monitor = svc.create_monitor(logger=logger)

    try:
        asyncio.run(monitor.run(interval=interval))
    except KeyboardInterrupt:
        pass


@click.command(hidden=True, name="_monitor-daemon")
@click.option("--interval", type=float)
@click.pass_context
def monitor_daemon(ctx: click.Context, interval: float | None):
    """Internal command run inside the _monitor tmux window."""
    _run_daemon(ctx.obj["session"], interval, ctx.obj.get("config"))
