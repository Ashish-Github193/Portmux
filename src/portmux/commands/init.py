"""Initialize command for PortMUX CLI."""

import click
from rich.console import Console

from ..config import create_default_config, get_config_path, load_config
from ..profiles import load_profile, profile_exists, list_available_profiles
from ..session import create_session, kill_session, session_exists
from ..startup import execute_startup_commands, startup_commands_enabled
from ..utils import handle_error

console = Console()


@click.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force recreation of existing session"
)
@click.option(
    "--profile", "-p", type=str, help="Initialize with a specific profile"
)
@click.option(
    "--no-startup", is_flag=True, help="Skip startup command execution"
)
@click.pass_context
def init(ctx: click.Context, force: bool, profile: str, no_startup: bool):
    """Initialize PortMUX session and configuration.

    Creates a new tmux session for managing SSH port forwards.
    Optionally loads a profile and executes startup commands.

    Examples:

        portmux init                      # Basic initialization

        portmux init --profile dev        # Initialize with development profile

        portmux init --no-startup         # Skip startup commands

        portmux init --force              # Force recreate existing session
    """
    base_session_name = ctx.obj["session"]  # This might be overridden by profile
    config_path = ctx.obj.get("config")
    verbose = ctx.obj["verbose"]

    try:
        # Load or create base configuration
        if verbose:
            console.print(f"[blue]Loading configuration...[/blue]")

        try:
            config = load_config(config_path)
            if verbose:
                console.print(
                    f"[green]Configuration loaded from {get_config_path()}[/green]"
                )
        except Exception:
            if verbose:
                console.print("[yellow]Creating default configuration...[/yellow]")
            create_default_config()
            config = load_config(config_path)
            console.print(
                f"[green]Default configuration created at {get_config_path()}[/green]"
            )

        # Handle profile loading
        if profile:
            if verbose:
                console.print(f"[blue]Loading profile '{profile}'...[/blue]")

            if not profile_exists(config, profile):
                available_profiles = list_available_profiles(config)
                console.print(f"[red]Profile '{profile}' not found[/red]")
                if available_profiles:
                    console.print(f"[blue]Available profiles: {', '.join(available_profiles)}[/blue]")
                else:
                    console.print("[blue]No profiles are configured[/blue]")
                raise click.ClickException(f"Profile '{profile}' not found")

            # Load profile configuration
            config = load_profile(profile, config)
            console.print(f"[green]Profile '{profile}' loaded[/green]")

        # Determine final session name (may be overridden by profile)
        session_name = config.get("session_name", base_session_name)

        # Update context with actual session name for startup commands
        ctx.obj["session"] = session_name

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
            
            if profile:
                console.print(f"[blue]Initialized with profile: {profile}[/blue]")

            # Execute startup commands if enabled and not skipped
            if not no_startup and startup_commands_enabled(config):
                if verbose:
                    console.print("[blue]Executing startup commands...[/blue]")
                
                startup_success = execute_startup_commands(config, session_name, verbose)
                if startup_success:
                    console.print("[green]Startup commands completed successfully[/green]")
                else:
                    console.print("[yellow]Some startup commands failed (session still active)[/yellow]")
            elif no_startup:
                if verbose:
                    console.print("[blue]Startup commands skipped (--no-startup)[/blue]")
            elif verbose:
                console.print("[blue]No startup commands configured[/blue]")

            console.print(f"[blue]Use 'portmux status' to view session details[/blue]")
        else:
            console.print(f"[yellow]Session '{session_name}' already exists[/yellow]")

    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))
