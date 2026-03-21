"""Add command for PortMUX CLI."""

from __future__ import annotations

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
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

        svc.add_forward(
            direction=direction,
            spec=spec,
            host=host,
            identity=identity,
            verbose=verbose,
        )

        if not no_check:
            output.warning("Note: Connection validation not implemented yet")

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
