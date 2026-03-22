# PortMUX

Manage SSH port forwards through persistent tmux sessions. Each forward runs in its own
tmux window — independently manageable, observable, and health-checked.

**Python 3.10+** | **Click** CLI | **Rich** output | **libtmux** backend

## Installation

```bash
uv install .
```

## Quick Start

```bash
# Start the portmux session
portmux init

# Add a local forward (forwards local port 8080 to remote port 80)
portmux add L 8080:localhost:80 user@server.com

# Check status with health checks
portmux status

# List all forwards (fast, no health check)
portmux list

# Remove a forward
portmux remove L:8080:localhost:80
```

## Port Forward Types

- **Local forward (`L`)**: Makes a remote service available on your local machine
  - `portmux add L 8080:localhost:80 user@server.com` → access remote port 80 at localhost:8080

- **Remote forward (`R`)**: Makes your local service available on the remote machine
  - `portmux add R 9000:localhost:3000 user@server.com` → remote can reach your port 3000 at its port 9000

## Commands

| Command | Description |
|---------|-------------|
| `portmux init` | Create tmux session, run startup commands, start monitor |
| `portmux init -p dev` | Initialize with a profile |
| `portmux add L 8080:localhost:80 user@host` | Add local forward |
| `portmux add R 9000:localhost:9000 user@host -i key` | Add remote forward with identity |
| `portmux list` | Show active forwards (fast, no health check) |
| `portmux list --json` | Machine-readable output |
| `portmux remove L:8080:localhost:80` | Remove specific forward |
| `portmux remove --all -f` | Remove all without confirmation |
| `portmux remove --destroy-session -f` | Kill entire session |
| `portmux refresh --all --delay 2` | Reconnect all with 2s delay |
| `portmux status` | Health table + monitor status + recent errors |
| `portmux watch` | Foreground health monitor (terminal only) |
| `portmux monitor start` | Start background monitor daemon |
| `portmux monitor stop` | Stop background monitor daemon |
| `portmux monitor status` | Show monitor running state |
| `portmux profile list` | Show configured profiles |
| `portmux profile show dev` | Profile details |

Global flags: `--verbose/-v`, `--session/-s NAME`, `--config/-c PATH`, `--version`

## Health Monitoring

PortMUX continuously monitors tunnel health with three checks per tunnel:
- **Process alive**: Is the SSH process still running?
- **Pane output scan**: Detects stuck passphrases, connection errors, DNS failures
- **TCP port probe**: Verifies the local port is actually accepting connections

### Background Monitor

`portmux init` auto-starts a background monitor daemon in a `_monitor` tmux window.
It logs health events to `~/.portmux/health.log` and auto-restarts dead tunnels.

```bash
portmux monitor start      # start manually
portmux monitor stop       # stop
portmux monitor status     # check if running
tail -f ~/.portmux/health.log  # watch logs
```

### Foreground Watch

```bash
portmux watch              # live health output in terminal (no file logging)
portmux watch --interval 5 # custom check interval
```

## Configuration

Location: `~/.portmux/config.toml` (override with `--config`)

```toml
[general]
session_name = "portmux"
default_identity = "~/.ssh/id_rsa"    # optional, auto-detected if absent
reconnect_delay = 1
max_retries = 3

[startup]
auto_execute = true
commands = [
    "portmux add L 8080:localhost:80 user@prod",
    "portmux add L 5432:db.internal:5432 user@prod",
]

[monitor]
enabled = true             # auto-start background monitor on portmux init
check_interval = 30.0      # seconds between health checks
tcp_timeout = 2.0          # TCP probe timeout
auto_reconnect = true      # auto-restart dead tunnels

[profiles.development]
session_name = "portmux-dev"
default_identity = "~/.ssh/dev_key"
commands = ["portmux add L 3000:localhost:3000 user@dev"]

[profiles.production]
session_name = "portmux-prod"
commands = ["portmux add L 5432:prod-db:5432 user@bastion"]
```

Profile values override base config; unset values inherit from `[general]`.

### Profile Workflows

```bash
portmux init --profile development    # init with dev profile
portmux init --profile production     # init with prod profile
portmux profile list                  # show available profiles
portmux profile active                # show current profile
```

## Architecture

Five-layer design:

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION: cli.py, commands/*, utils.py                 │
│  Click commands, Rich tables, argument validation           │
├─────────────────────────────────────────────────────────────┤
│  SERVICE LAYER: core/service.py, core/config.py,            │
│                 core/profiles.py, core/startup.py,          │
│                 core/output.py                              │
│  Orchestration, configuration, profile merging, output      │
├─────────────────────────────────────────────────────────────┤
│  FORWARD LOGIC: ssh/forwards.py                             │
│  SSH command building, port spec parsing, forward lifecycle │
├─────────────────────────────────────────────────────────────┤
│  BACKEND ABSTRACTION: backend/protocol.py, backend/tmux.py  │
│  TunnelBackend Protocol + TmuxBackend adapter               │
├─────────────────────────────────────────────────────────────┤
│  EXECUTION: tmux/session.py, tmux/windows.py                │
│  tmux operations via libtmux                                │
└─────────────────────────────────────────────────────────────┘
```

## Source Layout

```
src/portmux/
├── cli.py               # Main Click group, global options
├── models.py            # Dataclasses: ForwardInfo, TunnelInfo, *Config, HealthResult
├── exceptions.py        # PortMuxError → TmuxError, SSHError, ConfigError
├── utils.py             # Validation, tables, error handling
├── commands/            # Thin Click wrappers
│   ├── init.py, add.py, list.py, remove.py, refresh.py
│   ├── status.py, watch.py, monitor.py, profile.py
├── core/                # Service layer
│   ├── service.py       # PortmuxService — central orchestrator
│   ├── config.py, profiles.py, startup.py, output.py
├── backend/             # Pluggable tunnel execution
│   ├── protocol.py      # TunnelBackend Protocol
│   └── tmux.py          # TmuxBackend adapter
├── health/              # Health checking subsystem
│   ├── checker.py       # Async health checks (process/pane/TCP)
│   ├── monitor.py       # Continuous monitor with auto-restart
│   ├── logger.py        # Buffered file logger
│   └── state.py         # TunnelHealth state machine
└── tmux/                # libtmux wrappers
    ├── session.py       # Session create/exists/kill
    └── windows.py       # Window create/kill/list/diagnostics
```

## Development

### Phases

- **Phase 1** (done): Core tmux/SSH infrastructure
- **Phase 2** (done): Full CLI with Click, all commands, test suite
- **Phase 3** (done): Configuration system, profiles, startup automation
- **Phase 4** (done): Async health check system
- **Phase 5** (done): Background monitor daemon + health logging
- **Phase 6** (planned): E2E tests in Docker, SSH agent awareness
- **Phase 7** (planned): TUI mode using Rich layouts

### Testing

```bash
uv run pytest              # all tests (332)
uv run pytest -v           # verbose
uv run pytest --cov=portmux  # with coverage
```

### Requirements

- Python 3.10+
- tmux installed
- SSH access to remote servers

## License

This project is open source.
