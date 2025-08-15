# PortMUX

A simple tool to manage SSH port forwards using tmux.

## What is PortMUX?

PortMUX helps you create and manage SSH port forwards without dealing with tmux commands directly. It keeps all your port forwards running in one tmux session that survives when you close your terminal.

## What it does

- **Create port forwards**: Set up local and remote SSH port forwards
- **Keep them running**: Uses tmux to keep forwards alive even when you close your terminal
- **Easy management**: Add, remove, list, and refresh forwards with simple commands
- **No tmux knowledge needed**: You don't need to know tmux commands

## Installation

```bash
uv install .
```

## Basic usage

```bash
# Start the portmux session
portmux init

# Add a local forward (forwards local port 8080 to remote port 80)
portmux add L 8080:localhost:80 user@server.com

# Add a remote forward (forwards remote port 9000 to local port 3000)  
portmux add R 9000:localhost:3000 user@server.com

# List all forwards
portmux list

# Remove a forward
portmux remove L:8080:localhost:80

# Check status
portmux status

# Refresh a forward (reconnect it)
portmux refresh L:8080:localhost:80
```

## Port forward types

- **Local forward (`L`)**: Makes a remote service available on your local machine
  - Example: `portmux add L 8080:localhost:80 user@server.com`
  - Access remote port 80 by connecting to localhost:8080

- **Remote forward (`R`)**: Makes your local service available on the remote machine
  - Example: `portmux add R 9000:localhost:3000 user@server.com`
  - Remote machine can access your local port 3000 by connecting to its port 9000

## Requirements

- Python 3.10 or higher
- tmux installed on your system
- SSH access to remote servers

## Development

This project is built in phases:

- **Phase 1**: Core tmux and SSH management ( Complete)
- **Phase 2**: Command-line interface ( Complete)  
- **Phase 3**: Text user interface (TUI) - Coming soon

## Testing

```bash
uv run pytest
```

## License

This project is open source.