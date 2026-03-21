"""Add command for PortMUX CLI."""

from __future__ import annotations

import asyncio
import time

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..health import HealthChecker, TunnelHealth
from ..models import ForwardInfo
from ..utils import handle_error, validate_direction, validate_port_spec


@click.command()
@click.argument(
    "direction",
    callback=lambda ctx, _param, value: validate_direction(value) if value else value,
)
@click.argument(
    "spec",
    callback=lambda ctx, _param, value: validate_port_spec(value) if value else value,
)
@click.argument("host")
@click.option("--identity", "-i", type=click.Path(), help="SSH identity file path")
@click.option("--no-check", is_flag=True, help="Skip connectivity validation")
@click.pass_context
def add(
    ctx: click.Context,
    direction: str,
    spec: str,
    host: str,
    identity: str,
    no_check: bool,
):
    """Add a new SSH port forward.

    DIRECTION: 'L'/'LOCAL' for local forward, 'R'/'REMOTE' for remote forward

    SPEC: Port specification in format 'local_port:remote_host:remote_port'

    HOST: SSH target in format 'user@hostname'

    Examples:

        portmux add L 8080:localhost:80 user@server.com

        portmux add R 9000:192.168.1.10:9000 user@server.com -i ~/.ssh/key
    """
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        # Load configuration for defaults
        config = load_config(ctx.obj.get("config"))

        # Create service and delegate
        svc = PortmuxService(config, output, session_name)

        window_name = svc.add_forward(
            direction=direction,
            spec=spec,
            host=host,
            identity=identity,
            verbose=verbose,
        )

        if not no_check and direction == "L":
            time.sleep(1.5)  # Give the tunnel time to establish
            checker = HealthChecker(
                svc.backend, svc.session_name, tcp_timeout=config.monitor.tcp_timeout
            )
            forward = ForwardInfo(
                name=window_name,
                direction=direction,
                spec=spec,
                status="",
                command="",
            )
            results = asyncio.run(checker.check_all([forward]))
            if results and results[0].health == TunnelHealth.HEALTHY:
                output.success("Connection verified")
            elif results:
                output.warning(f"Connection check: {results[0].detail}")
            else:
                output.warning("Could not verify connection")

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
