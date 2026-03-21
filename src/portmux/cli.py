"""Main CLI interface for PortMUX."""

from __future__ import annotations

import click
import colorama

from . import __version__
from .core.output import Output

# Initialize colorama for cross-platform colored output
colorama.init()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--session", "-s", default="portmux", help="Tmux session name (default: portmux)"
)
@click.option("--config", "-c", type=click.Path(), help="Path to config file")
@click.version_option(version=__version__, prog_name="PortMUX")
@click.pass_context
def main(ctx: click.Context, verbose: bool, session: str, config: str | None):
    """PortMUX - Port Multiplexer and Manager for SSH forwards.

    Manage SSH port forwards through a persistent tmux session.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Create shared output channel
    output = Output()

    # Store global options in context
    ctx.obj["verbose"] = verbose
    ctx.obj["session"] = session
    ctx.obj["config"] = config
    ctx.obj["output"] = output


# Import and register command modules
from .commands import add, init, profile, refresh, remove, status  # noqa: E402
from .commands import list as list_cmd  # noqa: E402

main.add_command(init.init)
main.add_command(status.status)
main.add_command(add.add)
main.add_command(list_cmd.list)
main.add_command(remove.remove)
main.add_command(refresh.refresh)
main.add_command(profile.profile)


if __name__ == "__main__":
    main()
