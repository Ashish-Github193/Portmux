# PortMUX — AI Development Guide

See [README.md](README.md) for architecture, CLI reference, configuration, and source layout.

This file covers internal conventions, mock patterns, and gotchas for working on the codebase.

## Key Internals

### Service Layer (core/service.py)

`PortmuxService(config, output, session_name, backend)` is the central orchestrator.
Commands are thin Click wrappers that delegate to it.

Internal imports use underscore aliases to avoid name collisions:

```python
from ..ssh.forwards import add_forward as _add_forward      # mock as portmux.core.service._add_forward
from ..ssh.forwards import list_forwards as _list_forwards   # mock as portmux.core.service._list_forwards
from ..ssh.forwards import remove_forward as _remove_forward
from ..ssh.forwards import refresh_forward as _refresh_forward
```

Session operations go through `self.backend` (e.g., `self.backend.session_exists()`),
not direct imports from `tmux/session.py`.

`PortmuxService` creates its own `HealthLogger` in `__init__`. All mutation methods
log events and flush immediately. `MONITOR_WINDOW = "_monitor"` is defined here
and imported by `commands/monitor.py` and `commands/status.py`.

### Background Monitor Daemon

The `_monitor` tmux window runs `portmux --session <name> _monitor-daemon` — a hidden
Click command in `commands/monitor.py`. It creates a `HealthLogger` and runs the monitor
loop with file logging. Foreground `watch` = terminal only (no file logging). This
prevents duplicate log entries when both are running.

### Forward Naming Convention

Window names follow `{Direction}:{Spec}`:
- `L:8080:localhost:80` / `R:9000:localhost:9000`
- `_monitor` window is excluded from forward listings (doesn't match `L:`/`R:` prefix)

### Data Models (models.py)

```python
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
class MonitorConfig:
    enabled: bool = True             # auto-start on portmux init
    check_interval: float = 30.0
    tcp_timeout: float = 2.0
    auto_reconnect: bool = True

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

### Backend Protocol (backend/protocol.py)

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

## Testing

332 tests across 20 files. All unit tests — tmux/subprocess calls are mocked.

### Mock Patterns

**Service-delegated commands** — mock the underscore-prefixed imports:
- `@patch("portmux.core.service._add_forward")`
- `@patch("portmux.core.service._list_forwards")`
- `@patch("portmux.core.service._remove_forward")`
- `@patch("portmux.core.service._refresh_forward")`

**Session mocks** target `tmux/` modules (called through `TmuxBackend`):
- `@patch("portmux.tmux.session.session_exists")`
- `@patch("portmux.tmux.session.create_session")`
- `@patch("portmux.tmux.session.kill_session")`

**Command tests** use Click's `CliRunner`:
```python
result = self.runner.invoke(
    command_func, ["arg1"],
    obj={"session": "portmux", "config": None, "verbose": False, "output": Output()}
)
assert result.exit_code == 0
```

**Forward tests** inject a mock backend directly:
```python
backend = Mock(spec=TmuxBackend)
backend.tunnel_exists.return_value = False
backend.create_tunnel.return_value = True
result = add_forward("L", "8080:localhost:80", "user@host", backend=backend)
```

### E2E Tests (planned)

Docker container with real tmux + sshd. No mocks. See README.md for details.

```
tests/e2e/
├── Dockerfile
├── conftest.py
├── test_session_lifecycle.py
├── test_forward_lifecycle.py
├── test_monitor_lifecycle.py
└── test_health_checks.py
```

## Code Style

- **Formatter/Linter**: ruff (88 char line length)
- **Security**: bandit (B404, B603, B607 excluded for subprocess usage)
- **Type hints**: `from __future__ import annotations` everywhere; union types with `|`
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_CASE constants
- **Docstrings**: Google style (Args/Returns/Raises sections)
- **No module-level Console()**: Always use the injected `Output` instance

## Known Gaps

1. **No SSH Agent Awareness** — `get_default_identity()` checks if key files exist but doesn't verify they're usable (loaded in agent, passphrase-free). Silent tunnel failure.
2. **Startup Command Error Visibility** — stderr/stdout from failed startup commands not surfaced. User must re-run manually.
3. **JSON Output Only on `list`** — `status`, `monitor status`, `profile` commands have no `--json` flag.
4. **No Duplicate Forward Prevention Across Sessions** — two profiles binding the same local port in different sessions will silently conflict.

## Common Gotchas

1. **Mock paths for service imports**: Use `portmux.core.service._add_forward` not `portmux.core.service.add_forward` — the underscore alias matters
2. **Session mock paths go through tmux/**: Mock `portmux.tmux.session.session_exists`, not `portmux.core.service.session_exists`
3. **Backend import**: Use `from portmux.backend import TunnelBackend, TmuxBackend`
4. **Config returns dataclass**: `load_config()` returns `PortmuxConfig`, not a dict
5. **validate_config() takes raw dict**: Validates TOML dict structure before building `PortmuxConfig`
6. **Startup command injection**: PortMUX startup commands get `--session` auto-injected if not present
7. **Group-level CLI flags**: `--session`, `--verbose`, `--config` must come BEFORE the subcommand name (e.g., `portmux --session foo watch`, not `portmux watch --session foo`)
8. **Click context obj**: Commands expect `{"session", "config", "verbose", "output"}` in `ctx.obj`
9. **Profile inheritance**: `ProfileConfig` fields set to `None` inherit from base `PortmuxConfig`
10. **Identity resolution order**: explicit `-i` flag → `config.default_identity` → auto-detected from `~/.ssh/`
11. **MONITOR_WINDOW**: Defined in `core/service.py` as `"_monitor"` — don't redefine elsewhere
12. **Foreground vs background**: `portmux watch` = terminal only. `_monitor-daemon` = file logging only. No duplication.
13. **HealthLogger is buffered**: Call `flush()` at natural boundaries. Service flushes after each op. Monitor flushes after each cycle.
14. **Init tests need window mocks**: `monitor.enabled=True` by default, so `initialize()` calls `start_background_monitor()` which needs `tmux.windows.window_exists` and `tmux.windows.create_window` mocked
