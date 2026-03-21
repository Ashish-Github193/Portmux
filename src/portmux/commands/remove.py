"""Remove command for PortMUX CLI."""

from __future__ import annotations

import click

from ..core.config import load_config
from ..core.output import Output
from ..core.service import PortmuxService
from ..utils import confirm_destructive_action, handle_error


@click.command()
@click.argument("name", required=False)
@click.option("--all", "remove_all", is_flag=True, help="Remove all forwards")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--destroy-session", is_flag=True, help="Destroy entire session and all forwards"
)
@click.pass_context
def remove(
    ctx: click.Context, name: str, remove_all: bool, force: bool, destroy_session: bool
):
    """Remove SSH port forwards.

    NAME: Forward name to remove (e.g., 'L:8080:localhost:80')

    Examples:

        portmux remove L:8080:localhost:80    # Remove specific forward

        portmux remove --all                  # Remove all forwards

        portmux remove --destroy-session      # Destroy entire session
    """
    session_name = ctx.obj["session"]
    verbose = ctx.obj["verbose"]
    output: Output = ctx.obj.get("output") or Output()

    try:
        # Validate arguments early
        if not remove_all and not destroy_session and not name:
            raise click.UsageError("Must specify forward name or use --all flag")

        config = load_config(ctx.obj.get("config"))
        svc = PortmuxService(config, output, session_name)

        # Check if session exists
        if not svc.session_is_active():
            output.error(f"Session '{session_name}' is not active")
            output.info("Nothing to remove")
            return

        # Handle session destruction
        if destroy_session:
            if confirm_destructive_action(
                f"This will destroy session '{session_name}'"
                " and ALL forwards. Continue?",
                force,
            ):
                svc.destroy_session(verbose)
            else:
                output.warning("Operation cancelled")
            return

        # Handle remove all
        if remove_all:
            forwards = svc.list_forwards()
            if not forwards:
                output.warning(f"No forwards to remove in session '{session_name}'")
                return

            if confirm_destructive_action(
                f"This will remove ALL {len(forwards)} forward(s). Continue?", force
            ):
                svc.remove_all_forwards(verbose)
            else:
                output.warning("Operation cancelled")
            return

        # Handle single forward removal
        forwards = svc.list_forwards()
        forward_exists = any(f.name == name for f in forwards)
        if not forward_exists:
            output.error(f"Forward '{name}' not found")
            output.info("Use 'portmux list' to see active forwards")
            return

        svc.remove_forward(name, verbose)

    except click.UsageError:
        raise
    except Exception as e:
        handle_error(e, output)
        raise click.ClickException(str(e))
