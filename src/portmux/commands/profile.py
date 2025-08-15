"""Profile management commands for PortMUX CLI."""

import click
from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..profiles import (get_active_profile, get_profile_info,
                       list_available_profiles, profile_exists,
                       profile_summary)
from ..utils import handle_error

console = Console()


@click.group()
@click.pass_context
def profile(ctx: click.Context):
    """Manage PortMUX configuration profiles.
    
    Profiles allow you to define different sets of port forwards
    for different environments (development, staging, production, etc.).
    
    Examples:
    
        portmux profile list              # List all profiles
        
        portmux profile show dev          # Show development profile details
        
        portmux profile active            # Show currently active profile
    """
    pass


@profile.command()
@click.pass_context
def list(ctx: click.Context):
    """List all available profiles.
    
    Shows all profiles defined in the configuration file
    with their basic information.
    """
    config_path = ctx.obj.get("config")
    verbose = ctx.obj["verbose"]
    
    try:
        config = load_config(config_path)
        profiles = list_available_profiles(config)
        
        if not profiles:
            console.print("[yellow]No profiles configured[/yellow]")
            console.print("[blue]Profiles can be added to your config file at ~/.portmux/config.toml[/blue]")
            return
        
        # Create table for profile list
        table = Table(title="Available Profiles")
        table.add_column("Profile Name", style="cyan")
        table.add_column("Session Name", style="green")
        table.add_column("Commands", style="yellow")
        table.add_column("Custom Identity", style="magenta")
        
        summary = profile_summary(config)
        
        for profile_name in profiles:
            profile_data = summary["profiles"].get(profile_name, {})
            
            if "error" in profile_data:
                table.add_row(
                    profile_name,
                    "[red]Error[/red]",
                    "[red]Error[/red]",
                    "[red]Error[/red]"
                )
            else:
                commands_count = str(profile_data.get("command_count", 0))
                custom_identity = "Yes" if profile_data.get("has_custom_identity", False) else "No"
                session_name = profile_data.get("session_name", "portmux")
                
                table.add_row(
                    profile_name,
                    session_name,
                    commands_count,
                    custom_identity
                )
        
        console.print(table)
        
        if verbose:
            console.print(f"\n[blue]Total profiles: {len(profiles)}[/blue]")
            console.print(f"[blue]Configuration file: {config_path or '~/.portmux/config.toml'}[/blue]")
    
    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))


@profile.command()
@click.argument("profile_name")
@click.pass_context
def show(ctx: click.Context, profile_name: str):
    """Show detailed information about a specific profile.
    
    PROFILE_NAME: Name of the profile to show details for
    
    Displays complete configuration information for the specified profile,
    including session name, identity file, and all configured commands.
    """
    config_path = ctx.obj.get("config")
    verbose = ctx.obj["verbose"]
    
    try:
        config = load_config(config_path)
        
        if not profile_exists(config, profile_name):
            available_profiles = list_available_profiles(config)
            console.print(f"[red]Profile '{profile_name}' not found[/red]")
            if available_profiles:
                console.print(f"[blue]Available profiles: {', '.join(available_profiles)}[/blue]")
            else:
                console.print("[blue]No profiles are configured[/blue]")
            return
        
        # Get profile information
        info = get_profile_info(config, profile_name)
        
        # Display profile details
        console.print(f"\n[bold cyan]Profile: {profile_name}[/bold cyan]")
        console.print(f"[green]Session Name:[/green] {info['session_name']}")
        
        if info["inherits_session_name"]:
            console.print("  [dim](inherited from general configuration)[/dim]")
        
        identity = info["default_identity"] or "[dim]None[/dim]"
        console.print(f"[green]Identity File:[/green] {identity}")
        
        if info["inherits_identity"]:
            console.print("  [dim](inherited from general configuration)[/dim]")
        
        console.print(f"[green]Commands:[/green] {info['command_count']}")
        
        if info["commands"]:
            console.print("\n[bold]Startup Commands:[/bold]")
            for i, command in enumerate(info["commands"], 1):
                console.print(f"  {i}. [yellow]{command}[/yellow]")
        else:
            console.print("  [dim]No commands configured[/dim]")
        
        if verbose:
            console.print(f"\n[blue]Profile inherits session name: {info['inherits_session_name']}[/blue]")
            console.print(f"[blue]Profile inherits identity: {info['inherits_identity']}[/blue]")
    
    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))


@profile.command()
@click.pass_context
def active(ctx: click.Context):
    """Show the currently active profile.
    
    Displays information about the profile that was used to initialize
    the current session, if any.
    """
    config_path = ctx.obj.get("config")
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]
    
    try:
        config = load_config(config_path)
        active_profile = get_active_profile(config)
        
        if active_profile:
            console.print(f"[green]Active profile:[/green] {active_profile}")
            
            if verbose:
                # Show details of the active profile
                console.print("\n[bold]Profile Details:[/bold]")
                ctx.invoke(show, profile_name=active_profile)
        else:
            console.print("[yellow]No profile is currently active[/yellow]")
            console.print(f"[blue]Session '{session_name}' was initialized without a profile[/blue]")
            
            available_profiles = list_available_profiles(config)
            if available_profiles:
                console.print(f"[blue]Available profiles: {', '.join(available_profiles)}[/blue]")
                console.print("[blue]Use 'portmux init --profile <name>' to initialize with a profile[/blue]")
    
    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))


# Register the profile command group
if __name__ == "__main__":
    profile()