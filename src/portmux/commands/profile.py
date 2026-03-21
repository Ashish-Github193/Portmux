"""Profile management commands for PortMUX CLI."""

from __future__ import annotations

import click
from rich.table import Table

from ..core.config import load_config
from ..core.output import Output
from ..core.profiles import (
    get_active_profile,
    get_profile_info,
    list_available_profiles,
    profile_exists,
    profile_summary,
)
from ..utils import handle_error


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
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(config_path)
        profiles = list_available_profiles(config)

        if not profiles:
            output.warning("No profiles configured")
            output.info(
                "Profiles can be added to your config file at ~/.portmux/config.toml"
            )
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
                    "[red]Error[/red]",
                )
            else:
                commands_count = str(profile_data.get("command_count", 0))
                custom_identity = (
                    "Yes" if profile_data.get("has_custom_identity", False) else "No"
                )
                session_name = profile_data.get("session_name", "portmux")

                table.add_row(
                    profile_name, session_name, commands_count, custom_identity
                )

        output.table(table)

        if verbose:
            output.info(f"\nTotal profiles: {len(profiles)}")
            output.info(
                f"Configuration file: {config_path or '~/.portmux/config.toml'}"
            )

    except Exception as e:
        handle_error(e, output)
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
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(config_path)

        if not profile_exists(config, profile_name):
            available_profiles = list_available_profiles(config)
            output.error(f"Profile '{profile_name}' not found")
            if available_profiles:
                output.info(f"Available profiles: {', '.join(available_profiles)}")
            else:
                output.info("No profiles are configured")
            return

        # Get profile information
        info = get_profile_info(config, profile_name)

        # Display profile details
        output.print(f"\n[bold cyan]Profile: {profile_name}[/bold cyan]")
        output.print(f"[green]Session Name:[/green] {info['session_name']}")

        if info["inherits_session_name"]:
            output.print("  [dim](inherited from general configuration)[/dim]")

        identity = info["default_identity"] or "[dim]None[/dim]"
        output.print(f"[green]Identity File:[/green] {identity}")

        if info["inherits_identity"]:
            output.print("  [dim](inherited from general configuration)[/dim]")

        output.print(f"[green]Commands:[/green] {info['command_count']}")

        if info["commands"]:
            output.print("\n[bold]Startup Commands:[/bold]")
            for i, command in enumerate(info["commands"], 1):
                output.print(f"  {i}. [yellow]{command}[/yellow]")
        else:
            output.print("  [dim]No commands configured[/dim]")

        if verbose:
            output.info(
                f"\nProfile inherits session name: {info['inherits_session_name']}"
            )
            output.info(f"Profile inherits identity: {info['inherits_identity']}")

    except Exception as e:
        handle_error(e, output)
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
    output: Output = ctx.obj.get("output") or Output()

    try:
        config = load_config(config_path)
        active_profile_name = get_active_profile(config)

        if active_profile_name:
            output.success(f"Active profile: {active_profile_name}")

            if verbose:
                # Show details of the active profile
                output.print("\n[bold]Profile Details:[/bold]")
                ctx.invoke(show, profile_name=active_profile_name)
        else:
            output.warning("No profile is currently active")
            output.info(f"Session '{session_name}' was initialized without a profile")

            available_profiles = list_available_profiles(config)
            if available_profiles:
                output.info(f"Available profiles: {', '.join(available_profiles)}")
                output.info(
                    "Use 'portmux init --profile <name>' to initialize with a profile"
                )

    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))


# Register the profile command group
if __name__ == "__main__":
    profile()
