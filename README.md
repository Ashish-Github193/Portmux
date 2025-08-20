# PortMUX

A simple tool to manage SSH port forwards using tmux.

## What is PortMUX?

PortMUX wraps around tmux and helps you create and manage SSH port forwards without directly handling tmux commands. It keeps all your port forwards running within a single tmux session, which remains active even after you close your terminal. PortMUX provides a rich command-line interface that allows users to initialize, add, remove, and refresh sessions. Users can also define profiles by creating TOML files. PortMUX utilizes these files to instantiate SSH sessions based on the environment using the corresponding id_rsa keys.

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

## Configuration

PortMUX supports advanced configuration through a TOML file that enables startup commands, profiles, and custom settings.

### Configuration File Location

Place your configuration file at: `~/.portmux/config.toml`

### Quick Setup

```bash
# Create the configuration directory
mkdir -p ~/.portmux

# Copy the sample configuration
cp config/config.toml.example ~/.portmux/config.toml

# Edit the configuration with your settings
nano ~/.portmux/config.toml

# Initialize with your configuration
portmux init
```

### Basic Configuration

```toml
[general]
session_name = "portmux"
default_identity = "~/.ssh/id_rsa"
reconnect_delay = 1
max_retries = 3

[startup]
auto_execute = true
commands = [
    "portmux add L 8080:localhost:80 user@server.com",
    "portmux add R 9000:localhost:3000 user@server.com"
]
```

### Profile-Based Workflows

PortMUX supports profiles for different environments:

```bash
# Initialize with development profile
portmux init --profile development

# Initialize with production profile  
portmux init --profile production

# List available profiles
portmux profile list

# Show profile details
portmux profile show development

# Check currently active profile
portmux profile active
```

### Example Profile Configuration

```toml
[profiles.development]
session_name = "portmux-dev"
commands = [
    "portmux add L 3000:db.dev:5432 dev-user@dev-server.com",
    "portmux add L 8080:api.dev:8080 dev-user@dev-server.com"
]

[profiles.production]
session_name = "portmux-prod"
default_identity = "~/.ssh/prod_key"
commands = [
    "portmux add L 5432:prod-db:5432 prod-user@prod-server.com",
    "portmux add R 9090:localhost:9090 prod-user@prod-server.com"
]
```

### Advanced Features

```bash
# Skip startup commands during initialization
portmux init --no-startup

# Re-execute startup commands after refresh
portmux refresh --reload-startup

# Use custom configuration file
portmux --config /path/to/config.toml init
```

For a complete configuration example with all available options, see [`config/config.toml.example`](config/config.toml.example).

## Requirements

- Python 3.10 or higher
- tmux installed on your system (works well with tmux version 3.5a)
- SSH access to remote servers

## Development

This project is built in phases:

- **Phase 1**: Core tmux and SSH management (✅ Complete)
- **Phase 2**: Command-line interface (✅ Complete)  
- **Phase 3**: Smart Configuration & Startup Automation (✅ Complete)
- **Phase 4**: Text user interface (TUI) - Coming soon

## Testing

```bash
uv run pytest
```

## License

This project is open source.
