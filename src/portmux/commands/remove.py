"""Remove command for PortMUX CLI."""

import click
from rich.console import Console

from ..session import session_exists, kill_session
from ..forwards import remove_forward, list_forwards
from ..utils import handle_error, confirm_destructive_action

console = Console()


@click.command()
@click.argument('name', required=False)
@click.option('--all', 'remove_all', is_flag=True, help='Remove all forwards')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompts')
@click.option('--destroy-session', is_flag=True, help='Destroy entire session and all forwards')
@click.pass_context
def remove(ctx: click.Context, name: str, remove_all: bool, force: bool, destroy_session: bool):
    """Remove SSH port forwards.
    
    NAME: Forward name to remove (e.g., 'L:8080:localhost:80')
    
    Examples:
    
        portmux remove L:8080:localhost:80    # Remove specific forward
        
        portmux remove --all                  # Remove all forwards
        
        portmux remove --destroy-session      # Destroy entire session
    """
    session_name = ctx.obj['session']
    verbose = ctx.obj['verbose']
    
    try:
        # Validate arguments early
        if not remove_all and not destroy_session and not name:
            raise click.UsageError("Must specify forward name or use --all flag")
        
        # Check if session exists
        if not session_exists(session_name):
            console.print(f"[red]Session '{session_name}' is not active[/red]")
            console.print("[blue]Nothing to remove[/blue]")
            return
        
        # Handle session destruction
        if destroy_session:
            if confirm_destructive_action(
                f"This will destroy session '{session_name}' and ALL forwards. Continue?",
                force
            ):
                if verbose:
                    console.print(f"[blue]Destroying session '{session_name}'...[/blue]")
                kill_session(session_name)
                console.print(f"[green]Session '{session_name}' destroyed successfully[/green]")
            else:
                console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        # Get current forwards
        forwards = list_forwards(session_name)
        
        # Handle remove all
        if remove_all:
            if not forwards:
                console.print(f"[yellow]No forwards to remove in session '{session_name}'[/yellow]")
                return
                
            if confirm_destructive_action(
                f"This will remove ALL {len(forwards)} forward(s). Continue?",
                force
            ):
                removed_count = 0
                for forward in forwards:
                    try:
                        remove_forward(forward['name'], session_name)
                        removed_count += 1
                        if verbose:
                            console.print(f"[green]Removed forward '{forward['name']}'[/green]")
                    except Exception as e:
                        console.print(f"[red]Failed to remove '{forward['name']}': {e}[/red]")
                
                console.print(f"[green]Successfully removed {removed_count} forward(s)[/green]")
            else:
                console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        # Handle single forward removal
        # Check if forward exists
        forward_exists = any(f['name'] == name for f in forwards)
        if not forward_exists:
            console.print(f"[red]Forward '{name}' not found[/red]")
            console.print("[blue]Use 'portmux list' to see active forwards[/blue]")
            return
        
        # Remove the forward
        if verbose:
            console.print(f"[blue]Removing forward '{name}'...[/blue]")
        
        remove_forward(name, session_name)
        console.print(f"[green]Successfully removed forward '{name}'[/green]")
        
    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))