"""Main CLI interface for PortMUX."""

import sys
from typing import Optional

import click
import colorama
from rich.console import Console

from . import __version__
from .exceptions import PortMuxError
from .utils import handle_error, init_session_if_needed


# Initialize colorama for cross-platform colored output
colorama.init()

# Rich console for better output formatting
console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--session', '-s', default='portmux', help='Tmux session name (default: portmux)')
@click.option('--config', '-c', type=click.Path(), help='Path to config file')
@click.version_option(version=__version__, prog_name='PortMUX')
@click.pass_context
def main(ctx: click.Context, verbose: bool, session: str, config: Optional[str]):
    """PortMUX - Port Multiplexer and Manager for SSH forwards.
    
    Manage SSH port forwards through a persistent tmux session.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj['verbose'] = verbose
    ctx.obj['session'] = session
    ctx.obj['config'] = config


# Import and register command modules
from .commands import init, status, add, list as list_cmd, remove, refresh

main.add_command(init.init)
main.add_command(status.status)
main.add_command(add.add)
main.add_command(list_cmd.list)
main.add_command(remove.remove)
main.add_command(refresh.refresh)


if __name__ == '__main__':
    main()