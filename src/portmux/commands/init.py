"""Initialize command for PortMUX CLI."""

from __future__ import annotations

import click

from ..core.config import create_default_config, get_config_path, load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..utils import handle_error


@click.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force recreation of existing session"
)
@click.option("--profile", "-p", type=str, help="Initialize with a specific profile")
@click.option("--no-startup", is_flag=True, help="Skip startup command execution")
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
    base_session_name = ctx.obj["session"]
    config_path = ctx.obj.get("config")
    verbose = ctx.obj["verbose"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        # Load or create base configuration
        output.verbose("Loading configuration...", verbose)

        try:
            config = load_config(config_path)
            output.verbose(f"Configuration loaded from {get_config_path()}", verbose)
        except Exception:
            output.verbose("Creating default configuration...", verbose)
            create_default_config()
            config = load_config(config_path)
            output.success(f"Default configuration created at {get_config_path()}")

        # Create service and delegate
        svc = PortmuxService(config, output, base_session_name)

        success = svc.initialize(
            profile=profile,
            force=force,
            run_startup=not no_startup,
            verbose=verbose,
        )

        if not success:
            raise click.ClickException("Initialization failed")

        # Update context with actual session name (may have been overridden by profile)
        ctx.obj["session"] = svc.session_name

    except click.ClickException:
        raise
    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
