"""Initialize command for PortMUX CLI."""

import click
from rich.console import Console

from ..config import create_default_config, get_config_path, load_config
from ..session import create_session, kill_session, session_exists
from ..utils import handle_error

console = Console()


@click.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force recreation of existing session"
)
@click.pass_context
def init(ctx: click.Context, force: bool):
    """Initialize PortMUX session and configuration.

    Creates a new tmux session for managing SSH port forwards.
    If session already exists, this command will report the status.
    """
    session_name = ctx.obj["session"]
    config_path = ctx.obj.get("config")
    verbose = ctx.obj["verbose"]

    try:
        # Load or create configuration
        if verbose:
            console.print(f"[blue]Loading configuration...[/blue]")

        try:
            load_config(config_path)
            if verbose:
                console.print(
                    f"[green]Configuration loaded from {get_config_path()}[/green]"
                )
        except Exception:
            if verbose:
                console.print("[yellow]Creating default configuration...[/yellow]")
            create_default_config()
            load_config(config_path)
            console.print(
                f"[green]Default configuration created at {get_config_path()}[/green]"
            )

        # Check if session exists
        if session_exists(session_name):
            if force:
                console.print(
                    f"[yellow]Destroying existing session '{session_name}'...[/yellow]"
                )
                kill_session(session_name)
            else:
                console.print(
                    f"[yellow]Session '{session_name}' already exists[/yellow]"
                )
                console.print("Use --force to recreate the session")
                return

        # Create session
        if verbose:
            console.print(f"[blue]Creating tmux session '{session_name}'...[/blue]")

        success = create_session(session_name)
        if success:
            console.print(
                f"[green]Successfully initialized PortMUX session '{session_name}'[/green]"
            )
            console.print(f"[blue]Use 'portmux status' to view session details[/blue]")
        else:
            console.print(f"[yellow]Session '{session_name}' already exists[/yellow]")

    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))
