"""Add command for PortMUX CLI."""

import click
from rich.console import Console

from ..forwards import add_forward
from ..config import load_config, get_default_identity
from ..utils import handle_error, init_session_if_needed, validate_direction, validate_port_spec

console = Console()


@click.command()
@click.argument('direction', callback=lambda ctx, param, value: validate_direction(value) if value else value)
@click.argument('spec', callback=lambda ctx, param, value: validate_port_spec(value) if value else value)
@click.argument('host')
@click.option('--identity', '-i', type=click.Path(), help='SSH identity file path')
@click.option('--no-check', is_flag=True, help='Skip connectivity validation')
@click.pass_context
def add(ctx: click.Context, direction: str, spec: str, host: str, identity: str, no_check: bool):
    """Add a new SSH port forward.
    
    DIRECTION: 'L'/'LOCAL' for local forward, 'R'/'REMOTE' for remote forward
    
    SPEC: Port specification in format 'local_port:remote_host:remote_port'
    
    HOST: SSH target in format 'user@hostname'
    
    Examples:
    
        portmux add L 8080:localhost:80 user@server.com
        
        portmux add R 9000:192.168.1.10:9000 user@server.com -i ~/.ssh/key
    """
    session_name = ctx.obj['session']
    verbose = ctx.obj['verbose']
    
    try:
        # Load configuration for defaults
        config = load_config(ctx.obj.get('config'))
        
        # Use provided identity or fall back to config default or system default
        if not identity:
            identity = config.get('default_identity') or get_default_identity()
            if verbose and identity:
                console.print(f"[blue]Using default identity: {identity}[/blue]")
        
        # Initialize session if needed
        init_session_if_needed(session_name)
        
        # Create the forward
        if verbose:
            direction_name = "Local" if direction == 'L' else "Remote"
            console.print(f"[blue]Creating {direction_name.lower()} forward {spec} to {host}...[/blue]")
        
        window_name = add_forward(
            direction=direction,
            spec=spec,
            host=host,
            identity=identity,
            session_name=session_name
        )
        
        direction_name = "Local" if direction == 'L' else "Remote"
        console.print(f"[green]Successfully created {direction_name.lower()} forward '{window_name}'[/green]")
        
        if not no_check:
            console.print("[yellow]Note: Connection validation not implemented yet[/yellow]")
            
    except Exception as e:
        handle_error(e)
        raise click.ClickException(str(e))