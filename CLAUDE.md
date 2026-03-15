# PortMUX — Claude Code Project Guide

## What Is PortMUX

PortMUX is a Python CLI tool that manages SSH port forwards through persistent tmux sessions.
It abstracts tmux window/session management so users can create, remove, refresh, and inspect
SSH tunnels with simple commands instead of manual `ssh -N -L` invocations. Each forward runs
in its own tmux window, making them independently manageable and observable.

Current version: **1.2.0** | Python: **3.10+** | Build: **hatchling** | CLI: **Click** | Output: **Rich**

## Architecture

Three-layer design:

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION: cli.py, commands/*, output.py, utils.py      │
│  Click commands, Rich output, argument validation           │
├─────────────────────────────────────────────────────────────┤
│  BUSINESS LOGIC: service.py, config.py, profiles.py,        │
│                  startup.py, models.py                       │
│  Orchestration, configuration, profile merging, startup exec│
├─────────────────────────────────────────────────────────────┤
│  EXECUTION: session.py, windows.py, forwards.py             │
│  Direct tmux subprocess calls, SSH command generation        │
└─────────────────────────────────────────────────────────────┘
```

Key design patterns:
- **Service Layer** — `PortmuxService` coordinates all high-level operations; commands are thin Click wrappers
- **Data Models** — Dataclasses in `models.py` replace raw dicts for type safety
- **Output Abstraction** — Single `Output` class replaces per-module `Console()` instances
- **Dependency Injection** — Config and Output passed via Click context, not module globals
- **Custom Exceptions** — `PortMuxError` → `TmuxError`, `SSHError`, `ConfigError`

## Source Layout

```
src/portmux/
├── __init__.py          # Package version
├── __main__.py          # python -m portmux entry
├── cli.py               # Main Click group, global options (--verbose, --session, --config)
├── models.py            # Dataclasses: ForwardInfo, ParsedSpec, StartupCommand, *Config
├── exceptions.py        # PortMuxError hierarchy
├── output.py            # Centralized Output class (success/error/warning/info/verbose/table/panel)
├── service.py           # PortmuxService — orchestrates all operations
├── config.py            # TOML config load/save/validate, identity detection
├── session.py           # create_session, session_exists, kill_session
├── windows.py           # create_window, kill_window, list_windows, window_exists
├── forwards.py          # add_forward, remove_forward, list_forwards, refresh_forward, parse_port_spec
├── startup.py           # execute_startup_commands, parse/validate startup commands
├── profiles.py          # load_profile, list/get/validate profiles, merge with base config
├── utils.py             # handle_error, validate_direction/port_spec, create_forwards_table
└── commands/
    ├── init.py          # portmux init [--force] [--profile NAME] [--no-startup]
    ├── add.py           # portmux add DIRECTION SPEC HOST [-i IDENTITY] [--no-check]
    ├── list.py          # portmux list [--json] [--status]
    ├── remove.py        # portmux remove NAME | --all | --destroy-session [-f]
    ├── refresh.py       # portmux refresh NAME | --all [--delay N] [--reload-startup]
    ├── status.py        # portmux status [--check-connections]
    └── profile.py       # portmux profile {list|show NAME|active}
```

## Data Models (models.py)

```python
@dataclass
class ParsedSpec:
    local_port: int          # 1-65535
    remote_host: str         # hostname or IP
    remote_port: int         # 1-65535

@dataclass
class ForwardInfo:
    name: str                # "L:8080:localhost:80"
    direction: str           # "L" or "R"
    spec: str                # "8080:localhost:80"
    status: str              # window status from tmux
    command: str             # full SSH command string

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
class PortmuxConfig:
    session_name: str = "portmux"
    default_identity: str | None = None
    reconnect_delay: float = 1
    max_retries: int = 3
    startup: StartupConfig = field(default_factory=StartupConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str | None = None
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
```

Profile values override base config; unset values inherit from `[general]`.
Startup commands prefixed with `portmux` get `--session` auto-injected.

## Service Layer (service.py)

`PortmuxService(config, output, session_name)` is the central orchestrator. Commands create
an instance and delegate to it. Internal imports use underscore aliases to avoid name collisions:

```python
from .forwards import add_forward as _add_forward      # mock as portmux.service._add_forward
from .forwards import list_forwards as _list_forwards   # mock as portmux.service._list_forwards
from .forwards import remove_forward as _remove_forward
from .forwards import refresh_forward as _refresh_forward
```

Methods: `initialize()`, `add_forward()`, `remove_forward()`, `remove_all_forwards()`,
`list_forwards()`, `refresh_forward()`, `refresh_all()`, `destroy_session()`,
`get_status()`, `session_is_active()`

## CLI Commands Quick Reference

| Command | Description |
|---------|-------------|
| `portmux init` | Create tmux session, run startup commands |
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
| `portmux status` | Session and forwards overview |
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

210 tests across 15 files. Run with:

```bash
uv run pytest              # all tests
uv run pytest -v           # verbose
uv run pytest --cov=portmux  # with coverage
```

### Test Patterns

All subprocess/tmux calls are mocked. No real tmux sessions needed for tests.

**Module tests** use pytest-mock (`mocker.patch`):
```python
def test_create_session(self, mocker):
    mock_run = mocker.patch("portmux.session.subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    assert create_session("test") is True
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
`PortmuxService`, mock the underscore-prefixed imports in `portmux.service`:
- `@patch("portmux.service._add_forward")` (not `portmux.service.add_forward`)
- `@patch("portmux.service._list_forwards")`
- `@patch("portmux.service._remove_forward")`
- `@patch("portmux.service._refresh_forward")`
- `@patch("portmux.service.session_exists")` (no underscore — imported directly)
- `@patch("portmux.service.create_session")`
- `@patch("portmux.service.kill_session")`

### Test File Map

| File | Tests | Covers |
|------|:-----:|--------|
| test_session.py | 14 | session create/exists/kill |
| test_windows.py | 21 | window create/kill/list/exists |
| test_forwards.py | 30 | add/remove/list/refresh/parse |
| test_config.py | 8 | load/save/validate config |
| test_startup.py | 35 | startup command parse/validate/execute |
| test_profiles.py | 41 | profile load/list/merge/validate |
| test_utils.py | 11 | validation, tables, error handling |
| test_cli.py | 2 | CLI entry point |
| test_commands/*.py | 48 | all 7 command modules |

## Dependencies

**Runtime**: click>=8.1.0, rich>=14.1.0, toml>=0.10.2, colorama>=0.4.6
**Dev**: pytest, pytest-mock, pytest-cov, black, isort, autoflake

## Code Style

- **Formatter**: Black (88 char line length)
- **Imports**: isort, grouped as stdlib → third-party → local
- **Type hints**: `from __future__ import annotations` everywhere; union types with `|`
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_CASE constants
- **Docstrings**: Google style (Args/Returns/Raises sections)
- **No module-level Console()**: Always use the injected `Output` instance

## Development Phases

- **Phase 1** (done): Core tmux/SSH infrastructure, session/window/forward management
- **Phase 2** (done): Full CLI with Click, all commands, JSON output, test suite
- **Phase 3** (done): Configuration system, profiles, startup automation
- **Phase 4** (planned): TUI mode using Rich layouts — Output abstraction enables this

## Missing Pieces & Known Gaps

### 1. No Tunnel Health Verification (Critical)
SSH forwards run in detached tmux windows. PortMUX has **zero visibility** into whether a
tunnel is actually working. If the SSH key has a passphrase and isn't in the agent, SSH
prompts for input inside the hidden tmux window — the tunnel silently never connects, but
`portmux status` and `portmux list` both report it as "Running" because the tmux window
exists and the `ssh` process is alive (just stuck on the prompt).

**Affected code:**
- `utils.py:88-89` — status is hardcoded to `"Running"` based solely on window existence
- `ForwardInfo.status` — always `""` from tmux, never reflects actual tunnel health
- No TCP probe, no SSH exit code check, no port-open validation anywhere

### 2. Post-Add Connection Validation (Stub)
`commands/add.py:67-70` — after creating a forward, the `--no-check` flag exists but
the check itself is unimplemented. Every `portmux add` prints:
```
Note: Connection validation not implemented yet
```
The intended behavior: after creating the forward, TCP connect to `localhost:<local_port>`
to verify the tunnel is actually passing traffic before reporting success.

### 3. Status Connection Checking (Stub)
`commands/status.py:14-17` — the `--check-connections` flag is declared but prints:
```
Connection checking not implemented yet
```
The intended behavior: for each active forward, probe the local port to confirm the
tunnel is live, and report per-forward health (healthy/unhealthy/timeout).

### 4. List Status Column (Fake)
`commands/list.py:18` — the `--status` flag is accepted but does nothing meaningful.
`utils.py:88-89` always shows "Running" for every forward regardless of actual state.
There's no mechanism to distinguish between a healthy tunnel, a stuck SSH prompt, a
crashed connection, or a port that's bound but not forwarding.

### 5. `max_retries` Config Field (Unused)
`PortmuxConfig.max_retries` (default: 3) is loaded from config, validated, and stored —
but never read by any operation. `refresh_forward()` does a single kill+recreate with no
retry loop. `service.refresh_all()` catches exceptions per-forward but doesn't retry.

### 6. No Passphrase / SSH Agent Awareness
`config.py:get_default_identity()` checks if key files exist on disk but doesn't verify
they're usable (loaded in agent, passphrase-free, or agent-forwarded). A key with a
passphrase that isn't in `ssh-agent` will cause a silent tunnel failure (see gap #1).
There's no `ssh-add -l` check or `SSH_AUTH_SOCK` validation.

### 7. No Forward Failure Detection or Auto-Restart
When an SSH process inside a tmux window dies (network drop, server reboot, timeout),
the tmux window closes silently. The forward disappears from `portmux list` with no
notification. There's no watchdog, no monitoring loop, no event hook. The user must
manually notice and run `portmux refresh`.

### 8. No Tunnel Backend Abstraction
`forwards.py` is hardcoded to tmux windows. There's no interface/protocol separating
the "tunnel" concept from the "tmux window" implementation. Adding an alternative
backend (direct subprocess, systemd, containers) requires rewriting `forwards.py`.
This was identified as Pattern 4 in the isolation plan but deferred as future work.

### 9. Startup Command Error Visibility
`startup.py` executes commands via `subprocess.run()` with a 60s timeout. If a startup
command fails, it's reported as a warning ("Some startup commands failed") but the
actual stderr/stdout is not surfaced to the user. Debugging which command failed and
why requires manually re-running the command.

### 10. No Config File Watcher or Reload
Changing `~/.portmux/config.toml` has no effect on a running session. There's no
`portmux reload` command, no file watcher, and no way to apply config changes without
destroying and re-initializing the session.

### 11. No Session Persistence Across Reboots
PortMUX relies on tmux sessions which don't survive system restarts. There's no
systemd unit, no autostart mechanism, and no `portmux restore` command to recreate
the previous session state from config.

### 12. JSON Output Only on `list`
Only `portmux list --json` supports machine-readable output. `portmux status`,
`portmux profile list`, and `portmux profile show` have no `--json` flag. Scripting
against these commands requires parsing Rich-formatted terminal output.

### 13. No Dynamic Forward Support
Only static local (`-L`) and remote (`-R`) forwards are supported. SSH dynamic
forwards (`-D` for SOCKS proxy) and newer `-W` stdio forwarding are not handled.
`validate_direction()` only accepts `L`/`R`.

### 14. No Duplicate Forward Prevention Across Sessions
`forwards.py:86` checks `window_exists()` within the current session, but if two
profiles bind the same local port in different sessions, both will try to bind
`localhost:8080` — the second SSH will fail silently inside its tmux window.

### 15. `list --status` Flag Accepted But Ignored
`commands/list.py:18-19` declares `--status` / `include_status` and passes it to
`create_forwards_table()`, but the table always shows the status column with the
hardcoded "Running" value. The flag changes nothing visible.

## Common Gotchas

1. **Mock paths for service imports**: Use `portmux.service._add_forward` not `portmux.service.add_forward` — the underscore alias matters
2. **Config returns dataclass**: `load_config()` returns `PortmuxConfig`, not a dict. Access with `.session_name` not `["session_name"]`
3. **validate_config() takes raw dict**: It validates TOML dict structure before building `PortmuxConfig`
4. **Startup command injection**: PortMUX startup commands get `--session` auto-injected if not present
5. **Forward status field**: Always `""` currently — `status` column exists for future health checks
6. **Click context obj**: Commands expect `{"session", "config", "verbose", "output"}` in `ctx.obj`
7. **Profile inheritance**: `ProfileConfig` fields set to `None` inherit from base `PortmuxConfig`
8. **Identity resolution order**: explicit `-i` flag → `config.default_identity` → auto-detected from `~/.ssh/`
