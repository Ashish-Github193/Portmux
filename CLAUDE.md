# PortMUX — Claude Code Project Guide

## What Is PortMUX

PortMUX is a Python CLI tool that manages SSH port forwards through persistent tmux sessions.
It abstracts tmux window/session management so users can create, remove, refresh, and inspect
SSH tunnels with simple commands instead of manual `ssh -N -L` invocations. Each forward runs
in its own tmux window, making them independently manageable and observable.

Current version: **1.2.0** | Python: **3.10+** | Build: **hatchling** | CLI: **Click** | Output: **Rich**

## Architecture

Five-layer design, reflected in directory structure:

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION: cli.py, commands/*, utils.py                  │
│  Click commands, Rich tables, argument validation            │
├─────────────────────────────────────────────────────────────┤
│  SERVICE LAYER: core/service.py, core/config.py,             │
│                 core/profiles.py, core/startup.py,           │
│                 core/output.py                               │
│  Orchestration, configuration, profile merging, output       │
├─────────────────────────────────────────────────────────────┤
│  FORWARD LOGIC: ssh/forwards.py                              │
│  SSH command building, port spec parsing, forward lifecycle  │
├─────────────────────────────────────────────────────────────┤
│  BACKEND ABSTRACTION: backend/protocol.py, backend/tmux.py   │
│  TunnelBackend Protocol + TmuxBackend adapter                │
├─────────────────────────────────────────────────────────────┤
│  EXECUTION: tmux/session.py, tmux/windows.py                 │
│  Direct tmux subprocess calls                                │
└─────────────────────────────────────────────────────────────┘
```

Key design patterns:
- **Service Layer** — `PortmuxService` coordinates all high-level operations; commands are thin Click wrappers
- **Backend Protocol** — `TunnelBackend` Protocol decouples tunnel lifecycle from tmux; `TmuxBackend` is the default implementation
- **Data Models** — Dataclasses in `models.py` replace raw dicts for type safety
- **Output Abstraction** — Single `Output` class (with `ProgressReporter`) replaces per-module `Console()` instances
- **Dependency Injection** — Config, Output, and Backend passed via Click context / constructor, not module globals
- **Custom Exceptions** — `PortMuxError` → `TmuxError`, `SSHError`, `ConfigError`

## Source Layout

```
src/portmux/
├── __init__.py          # Package version
├── __main__.py          # python -m portmux entry
├── cli.py               # Main Click group, global options (--verbose, --session, --config)
├── models.py            # Dataclasses: ForwardInfo, TunnelInfo, ParsedSpec, StartupCommand, *Config
├── exceptions.py        # PortMuxError hierarchy
├── utils.py             # handle_error, validate_direction/port_spec, create_forwards_table
│
├── commands/            # Presentation layer — thin Click wrappers
│   ├── init.py          # portmux init [--force] [--profile NAME] [--no-startup]
│   ├── add.py           # portmux add DIRECTION SPEC HOST [-i IDENTITY] [--no-check]
│   ├── list.py          # portmux list [--json] [--status]
│   ├── remove.py        # portmux remove NAME | --all | --destroy-session [-f]
│   ├── refresh.py       # portmux refresh NAME | --all [--delay N] [--reload-startup]
│   ├── status.py        # portmux status — health table + monitor indicator + recent errors
│   ├── watch.py         # portmux watch [--interval N] — foreground monitor, terminal only
│   ├── monitor.py       # portmux monitor {start|stop|status} + hidden _monitor-daemon
│   └── profile.py       # portmux profile {list|show NAME|active}
│
├── core/                # Service layer — orchestration, config, output
│   ├── service.py       # PortmuxService — orchestrates all operations
│   ├── config.py        # TOML config load/save/validate, identity detection
│   ├── profiles.py      # load_profile, list/get/validate profiles, merge with base config
│   ├── startup.py       # execute_startup_commands, parse/validate startup commands
│   └── output.py        # Output class (success/error/warning/info/verbose/table/panel) + ProgressReporter
│
├── backend/             # Backend abstraction — pluggable tunnel execution
│   ├── __init__.py      # Re-exports TunnelBackend, TmuxBackend
│   ├── protocol.py      # TunnelBackend Protocol (7 methods)
│   └── tmux.py          # TmuxBackend — adapter wrapping tmux/session.py + tmux/windows.py
│
├── ssh/                 # Forward logic — SSH command building
│   └── forwards.py      # add_forward, remove_forward, list_forwards, refresh_forward, parse_port_spec
│
├── health/              # Health checking subsystem
│   ├── __init__.py      # Re-exports HealthChecker, HealthLogger, TunnelMonitor, etc.
│   ├── state.py         # TunnelHealth enum, HealthResult dataclass, transition rules
│   ├── checker.py       # HealthChecker — async process/pane/TCP checks per tunnel
│   ├── monitor.py       # TunnelMonitor — stateful check loop, auto-restart, heartbeat
│   └── logger.py        # HealthLogger — buffered queue, flushes to ~/.portmux/health.log
│
└── tmux/                # Execution layer — raw tmux subprocess calls (via libtmux)
    ├── session.py       # create_session, session_exists, kill_session
    └── windows.py       # create_window, kill_window, list_windows, window_exists, get_window_diagnostics
```

## Data Models (models.py)

```python
@dataclass
class ParsedSpec:
    local_port: int          # 1-65535
    remote_host: str         # hostname or IP
    remote_port: int         # 1-65535

@dataclass
class TunnelInfo:
    name: str                # backend-neutral tunnel identifier
    status: str              # backend-specific status string
    command: str             # command running inside the tunnel

@dataclass
class ForwardInfo:
    name: str                # "L:8080:localhost:80"
    direction: str           # "L" or "R"
    spec: str                # "8080:localhost:80"
    status: str              # window status from tmux
    command: str             # full SSH command string
    health: str | None = None  # TunnelHealth value or None if unchecked

@dataclass
class TunnelDiagnostics:
    pane_pid: int | None
    pane_current_command: str | None
    pane_dead: bool
    pane_dead_status: str | None
    pane_content: list[str]

@dataclass
class HealthResult:
    name: str
    health: TunnelHealth       # HEALTHY, UNHEALTHY, DEAD, etc.
    detail: str
    process_alive: bool
    port_open: bool | None     # None for remote forwards
    pane_error: str | None

@dataclass
class StartupCommand:
    command: str             # executable name
    args: list[str]          # command arguments
    original: str            # original command string

@dataclass
class StartupConfig:
    auto_execute: bool = True
    commands: list[str] = field(default_factory=list)

@dataclass
class ProfileConfig:
    session_name: str | None = None       # overrides general.session_name
    default_identity: str | None = None   # overrides general.default_identity
    commands: list[str] = field(default_factory=list)

@dataclass
class MonitorConfig:
    enabled: bool = True             # auto-start on portmux init
    check_interval: float = 30.0     # seconds between checks
    tcp_timeout: float = 2.0         # TCP probe timeout
    auto_reconnect: bool = True      # auto-restart dead tunnels

@dataclass
class PortmuxConfig:
    session_name: str = "portmux"
    default_identity: str | None = None
    reconnect_delay: float = 1
    max_retries: int = 3
    startup: StartupConfig = field(default_factory=StartupConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str | None = None
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
```

## Configuration (TOML)

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

[profiles.development]
session_name = "portmux-dev"
default_identity = "~/.ssh/dev_key"
commands = ["portmux add L 3000:localhost:3000 user@dev"]

[profiles.production]
session_name = "portmux-prod"
commands = ["portmux add L 5432:prod-db:5432 user@bastion"]

[monitor]
enabled = true             # auto-start background monitor on portmux init
check_interval = 30.0      # seconds between health checks
tcp_timeout = 2.0          # TCP probe timeout
auto_reconnect = true      # auto-restart dead tunnels
```

Profile values override base config; unset values inherit from `[general]`.
Startup commands prefixed with `portmux` get `--session` auto-injected.

## Service Layer (core/service.py)

`PortmuxService(config, output, session_name, backend)` is the central orchestrator. Commands
create an instance and delegate to it. The `backend` parameter defaults to `TmuxBackend()`.

Internal imports use underscore aliases to avoid name collisions with method names:

```python
from ..ssh.forwards import add_forward as _add_forward      # mock as portmux.core.service._add_forward
from ..ssh.forwards import list_forwards as _list_forwards   # mock as portmux.core.service._list_forwards
from ..ssh.forwards import remove_forward as _remove_forward
from ..ssh.forwards import refresh_forward as _refresh_forward
```

Session operations go through `self.backend` (e.g., `self.backend.session_exists()`),
not direct imports from `tmux/session.py`.

Methods: `initialize()`, `add_forward()`, `remove_forward()`, `remove_all_forwards()`,
`list_forwards()`, `refresh_forward()`, `refresh_all()`, `destroy_session()`,
`get_status()`, `session_is_active()`, `handle_startup_reload()`,
`check_health()`, `create_monitor()`, `start_background_monitor()`

`PortmuxService` creates its own `HealthLogger` in `__init__`. All mutation methods
log events and flush immediately. `MONITOR_WINDOW = "_monitor"` is defined here
and imported by `commands/monitor.py` and `commands/status.py`.

## Backend Protocol (backend/protocol.py)

```python
@runtime_checkable
class TunnelBackend(Protocol):
    def create_session(self, session_name: str) -> bool: ...
    def session_exists(self, session_name: str) -> bool: ...
    def kill_session(self, session_name: str) -> bool: ...
    def create_tunnel(self, name: str, command: str, session_name: str) -> bool: ...
    def kill_tunnel(self, name: str, session_name: str) -> bool: ...
    def tunnel_exists(self, name: str, session_name: str) -> bool: ...
    def list_tunnels(self, session_name: str) -> list[TunnelInfo]: ...
```

`TmuxBackend` (in `backend/tmux.py`) implements this by delegating to `tmux/session.py`
and `tmux/windows.py`. Import via `from portmux.backend import TunnelBackend, TmuxBackend`.

## CLI Commands Quick Reference

| Command | Description |
|---------|-------------|
| `portmux init` | Create tmux session, run startup, start monitor |
| `portmux init -p dev` | Initialize with profile |
| `portmux add L 8080:localhost:80 user@host` | Add local forward |
| `portmux add R 9000:localhost:9000 user@host -i key` | Add remote forward with identity |
| `portmux list` | Show active forwards as table |
| `portmux list --json` | Machine-readable output |
| `portmux remove L:8080:localhost:80` | Remove specific forward |
| `portmux remove --all -f` | Remove all without confirmation |
| `portmux remove --destroy-session -f` | Kill entire session |
| `portmux refresh --all --delay 2` | Reconnect all with 2s delay |
| `portmux refresh --all --reload-startup` | Refresh + re-run startup |
| `portmux status` | Health table + monitor status + recent errors |
| `portmux watch` | Foreground health monitor (terminal only) |
| `portmux monitor start` | Start background monitor daemon |
| `portmux monitor stop` | Stop background monitor daemon |
| `portmux monitor status` | Show monitor running state + config |
| `portmux profile list` | Show configured profiles |
| `portmux profile show dev` | Profile details |
| `portmux profile active` | Currently active profile |

Global flags: `--verbose/-v`, `--session/-s NAME`, `--config/-c PATH`, `--version`

## Forward Naming Convention

Window names follow the pattern `{Direction}:{Spec}`:
- Local forward: `L:8080:localhost:80`
- Remote forward: `R:9000:localhost:9000`

SSH commands generated:
- Local: `ssh -N -L 8080:localhost:80 [-i key] user@host`
- Remote: `ssh -N -R 9000:localhost:9000 [-i key] user@host`

## Testing

332 tests across 20 files. Run with:

```bash
uv run pytest              # all tests
uv run pytest -v           # verbose
uv run pytest --cov=portmux  # with coverage
```

### Unit Tests

All subprocess/tmux calls are mocked. No real tmux sessions needed for unit tests.

**Execution layer tests** mock `subprocess.run` directly:
```python
def test_create_session(self, mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    assert create_session("test") is True
```

**Forward tests** inject a mock backend directly (no patching needed):
```python
def test_add_forward(self):
    backend = Mock(spec=TmuxBackend)
    backend.tunnel_exists.return_value = False
    backend.create_tunnel.return_value = True
    result = add_forward("L", "8080:localhost:80", "user@host", backend=backend)
```

**Command tests** use Click's `CliRunner`:
```python
def test_command(self):
    result = self.runner.invoke(
        command_func, ["arg1"],
        obj={"session": "portmux", "config": None, "verbose": False, "output": Output()}
    )
    assert result.exit_code == 0
```

**Mock path convention for service-delegated commands**: When a command delegates to
`PortmuxService`, mock the underscore-prefixed imports in `portmux.core.service`:
- `@patch("portmux.core.service._add_forward")` (not `portmux.core.service.add_forward`)
- `@patch("portmux.core.service._list_forwards")`
- `@patch("portmux.core.service._remove_forward")`
- `@patch("portmux.core.service._refresh_forward")`

Session mocks target `tmux/` modules (called through `TmuxBackend`):
- `@patch("portmux.tmux.session.session_exists")`
- `@patch("portmux.tmux.session.create_session")`
- `@patch("portmux.tmux.session.kill_session")`

### Test File Map

| File | Tests | Covers |
|------|:-----:|--------|
| test_session.py | 14 | tmux/session create/exists/kill |
| test_windows.py | 21 | tmux/window create/kill/list/exists |
| test_window_diagnostics.py | — | get_window_diagnostics for health |
| test_tmux_backend.py | 9 | TmuxBackend adapter delegation |
| test_forwards.py | 30 | ssh/forwards add/remove/list/refresh/parse |
| test_config.py | 8 | core/config load/save/validate |
| test_startup.py | 35 | core/startup command parse/validate/execute |
| test_profiles.py | 41 | core/profiles load/list/merge/validate |
| test_utils.py | 9 | validation, tables, error handling |
| test_cli.py | 2 | CLI entry point |
| test_health_checker.py | — | HealthChecker process/pane/TCP checks |
| test_health_monitor.py | — | TunnelMonitor state transitions, restart |
| test_health_state.py | — | TunnelHealth enum, can_transition() |
| test_health_logger.py | — | HealthLogger buffer/flush/read |
| test_background_monitor.py | — | Monitor+logger, service logging, init/status integration |
| test_commands/*.py | — | all command modules including monitor |

### E2E Tests (planned)

E2E tests run inside a Docker container with real tmux + sshd. No mocks.

**Container setup:**
- Base: `python:3.10-slim` with `tmux` and `openssh-server`
- Passwordless SSH to localhost (ed25519 key, no passphrase)
- portmux installed via `pip install -e ".[dev]"`
- sshd started before test run

**Structure:**
```
tests/e2e/
├── Dockerfile               # Container with tmux + sshd + portmux
├── conftest.py              # Fixtures: unique session names, cleanup
├── test_session_lifecycle.py    # init, init --force, destroy
├── test_forward_lifecycle.py    # add, list, remove, refresh with real SSH
├── test_monitor_lifecycle.py    # monitor start/stop/status, health logging
└── test_health_checks.py        # healthy/unhealthy/dead detection, auto-restart
```

**What e2e covers that unit tests can't:**
- Real tmux session/window creation and cleanup
- Real SSH tunnels (to localhost via sshd in container)
- Health checks returning HEALTHY (TCP probe succeeds)
- Monitor detecting dead tunnels when SSH process is killed
- Auto-restart actually recreating tunnels
- CLI flag ordering (e.g. `--session` before subcommand)
- Health log file written and readable

**Running:**
```bash
docker build -t portmux-e2e -f tests/e2e/Dockerfile .
docker run --rm portmux-e2e
```

## Dependencies

**Runtime**: click>=8.1.0, rich>=14.1.0, toml>=0.10.2, colorama>=0.4.6, libtmux
**Dev**: pytest, pytest-mock, pytest-cov, ruff, bandit

## Code Style

- **Formatter/Linter**: ruff (88 char line length, replaces black/isort/autoflake)
- **Security**: bandit (B404, B603, B607 excluded for subprocess usage)
- **Imports**: ruff-managed, grouped as stdlib → third-party → local
- **Type hints**: `from __future__ import annotations` everywhere; union types with `|`
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_CASE constants
- **Docstrings**: Google style (Args/Returns/Raises sections)
- **No module-level Console()**: Always use the injected `Output` instance

## Development Phases

- **Phase 1** (done): Core tmux/SSH infrastructure, session/window/forward management
- **Phase 2** (done): Full CLI with Click, all commands, JSON output, test suite
- **Phase 3** (done): Configuration system, profiles, startup automation
- **Phase 4** (done): Async health check system — HealthChecker, TunnelMonitor, TunnelHealth state machine
- **Phase 5** (done): Background monitor daemon + buffered health logging + service-level event logging
- **Phase 6** (planned): E2E tests in Docker (real tmux + sshd), SSH agent awareness
- **Phase 7** (planned): TUI mode using Rich layouts — Output abstraction enables this

## Resolved

1. **Tunnel Health Verification** — `HealthChecker` performs three concurrent checks per tunnel: process alive, pane output scan, TCP port probe. `portmux status` runs on-demand health checks. Background monitor daemon runs persistent checks with auto-restart.
2. **Post-Add Connection Validation** — `commands/add.py` performs TCP port probe after creating local forwards (skip with `--no-check`). Results logged to health log.
3. **Status Connection Checking** — `commands/status.py` runs async health checks on all forwards, displays health column, monitor state, and recent error events from log.
4. **`max_retries` Config Field** — `TunnelMonitor` uses `config.max_retries` to limit auto-restart attempts per tunnel. After exhausting retries, tunnel is marked dead.
5. **Forward Failure Detection & Auto-Restart** — `TunnelMonitor` detects dead and vanished tunnels. Auto-restart via `auto_reconnect`. Background monitor persists in `_monitor` tmux window with health logging.
6. **Tunnel Backend Abstraction** — `TunnelBackend` Protocol decouples tunnel lifecycle from tmux. `TmuxBackend` is the default. New backends implement 7 methods.

## Known Gaps

### 1. No Passphrase / SSH Agent Awareness
`config.py:get_default_identity()` checks if key files exist on disk but doesn't verify
they're usable (loaded in agent, passphrase-free, or agent-forwarded). A key with a
passphrase that isn't in `ssh-agent` will cause a silent tunnel failure.
There's no `ssh-add -l` check or `SSH_AUTH_SOCK` validation.

### 2. Startup Command Error Visibility
`startup.py` executes commands via `subprocess.run()` with a 60s timeout. If a startup
command fails, it's reported as a warning ("Some startup commands failed") but the
actual stderr/stdout is not surfaced to the user. Debugging which command failed and
why requires manually re-running the command.

### 3. JSON Output Only on `list`
Only `portmux list --json` supports machine-readable output. `portmux status`,
`portmux monitor status`, `portmux profile list`, and `portmux profile show` have
no `--json` flag. Scripting against these commands requires parsing Rich-formatted output.

### 4. No Duplicate Forward Prevention Across Sessions
`forwards.py` checks `window_exists()` within the current session, but if two
profiles bind the same local port in different sessions, both will try to bind
`localhost:8080` — the second SSH will fail silently inside its tmux window.

## Common Gotchas

1. **Mock paths for service imports**: Use `portmux.core.service._add_forward` not `portmux.core.service.add_forward` — the underscore alias matters
2. **Session mock paths go through tmux/**: Mock `portmux.tmux.session.session_exists`, not `portmux.core.service.session_exists` — service uses `self.backend` which delegates to `tmux/session.py`
3. **Backend import**: Use `from portmux.backend import TunnelBackend, TmuxBackend` — the `backend/__init__.py` re-exports both
4. **Config returns dataclass**: `load_config()` returns `PortmuxConfig`, not a dict. Access with `.session_name` not `["session_name"]`
5. **validate_config() takes raw dict**: It validates TOML dict structure before building `PortmuxConfig`
6. **Startup command injection**: PortMUX startup commands get `--session` auto-injected if not present
7. **Group-level CLI flags**: `--session`, `--verbose`, `--config` are on the `main` Click group — they must come BEFORE the subcommand name (e.g., `portmux --session foo watch`, not `portmux watch --session foo`)
8. **Click context obj**: Commands expect `{"session", "config", "verbose", "output"}` in `ctx.obj`
9. **Profile inheritance**: `ProfileConfig` fields set to `None` inherit from base `PortmuxConfig`
10. **Identity resolution order**: explicit `-i` flag → `config.default_identity` → auto-detected from `~/.ssh/`
11. **MONITOR_WINDOW**: Defined in `core/service.py` as `"_monitor"`. Imported by `commands/monitor.py` and `commands/status.py` — don't redefine it
12. **Foreground vs background watch**: `portmux watch` = terminal output only, no file logging. Background `_monitor-daemon` = file logging only. This prevents duplicate log entries
13. **HealthLogger is buffered**: Events queue in memory. Call `flush()` at natural boundaries. Service methods flush after each operation. Monitor flushes after each check cycle
14. **Init tests need window mocks**: Since `monitor.enabled=True` by default, `initialize()` calls `start_background_monitor()` which needs `tmux.windows.window_exists` and `tmux.windows.create_window` mocked
