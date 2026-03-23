# PortMUX: SSH Port Forward Manager with Health Monitoring

---

**A Project Synopsis**
**Submitted in Partial Fulfillment of the Requirements for the Degree of**
**Bachelor of Technology in Information Technology**

---

**Submitted by:**

| | |
|---|---|
| **Student Name** | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
| **Roll Number** | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
| **Enrollment No.** | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |

**Under the Guidance of:**

| | |
|---|---|
| **Guide Name** | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
| **Designation** | \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |

---

**Department of Information Technology**
**\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ (College Name)**
**\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ (University Name)**
**Academic Year 2025–2026**

---

\newpage

## Table of Contents

1. Abstract
2. Introduction
3. Objectives
4. Scope
5. Literature Survey
6. Proposed System
7. System Architecture
8. Technology Stack
9. Module Description
10. Implementation Details
11. Testing Strategy
12. Project Statistics
13. Results and Output
14. Future Scope
15. Conclusion
16. References

\newpage

## 1. Abstract

SSH port forwarding is a fundamental technique used by developers, system administrators, and DevOps engineers to securely access remote services through encrypted tunnels. In practice, managing multiple concurrent SSH tunnels is a tedious and error-prone process — tunnels die silently, ports conflict without warning, and there is no centralized way to monitor or restart forwarding sessions.

**PortMUX** is a command-line tool built in Python that solves this problem by orchestrating multiple SSH port forwards through persistent tmux sessions. Each forward runs in its own isolated tmux window, making it independently manageable, observable, and restartable. The tool provides a complete lifecycle management system: session initialization, forward creation and removal, bulk refresh, configuration profiles, and automated startup sequences.

A key differentiator of PortMUX is its asynchronous health monitoring subsystem. The health checker performs three independent checks per tunnel — process liveness detection, terminal output scanning for SSH error patterns, and TCP port probing — all running concurrently via Python's `asyncio` framework. A background monitor daemon runs inside a dedicated tmux window, continuously watching tunnel health, logging events to disk, and automatically restarting dead tunnels with configurable retry limits.

The project follows a layered architecture with a protocol-based backend abstraction, enabling future extensibility to backends beyond tmux. It includes 364 automated tests (332 unit tests with mocked dependencies and 32 end-to-end tests running in Docker with real tmux and SSH servers), achieving comprehensive coverage of all subsystems.

PortMUX is implemented in approximately 4,000 lines of Python across 35 source files organized into 8 modules, with an additional 6,100 lines of test code across 43 test files.

\newpage

## 2. Introduction

### 2.1 Background

SSH (Secure Shell) port forwarding, also known as SSH tunneling, is a method of transporting arbitrary networking data over an encrypted SSH connection. It allows users to access services on remote networks that are not directly reachable, or to encrypt traffic that would otherwise travel in plaintext. There are two primary types:

- **Local forwarding (`-L`)**: Binds a port on the local machine and forwards traffic through the SSH connection to a specified host and port on the remote network. This is commonly used to access databases, web services, or APIs behind firewalls.
- **Remote forwarding (`-R`)**: Binds a port on the remote machine and forwards traffic back to a specified host and port on the local network. This is used for exposing local development servers or enabling reverse shell access.

### 2.2 Problem Statement

While SSH port forwarding is powerful, managing multiple tunnels simultaneously presents several operational challenges:

1. **Silent failures**: SSH tunnels can die without any visible indication. A network disruption, server restart, or authentication timeout can terminate the underlying SSH process, leaving the user unaware that their forward is no longer functional.

2. **No centralized management**: The standard approach involves running multiple `ssh -N -L ...` commands in separate terminals or background processes. There is no unified interface to list active forwards, check their status, or restart them.

3. **Manual reconnection**: When a tunnel dies, the user must manually identify which tunnel failed, recall the original command (with the correct port specification, host, and identity file), and re-execute it. In environments with many tunnels, this is time-consuming and error-prone.

4. **Configuration duplication**: Developers working across multiple environments (development, staging, production) often need different sets of tunnels. Without a configuration system, tunnel parameters must be remembered or maintained in ad-hoc shell scripts.

5. **Lack of health visibility**: There is no built-in mechanism to verify that an SSH tunnel is actually passing traffic, as opposed to merely having a live SSH process. A tunnel can appear "connected" while the port it forwards is unresponsive.

### 2.3 Motivation

The motivation for PortMUX arises from real-world development workflows where engineers routinely maintain 3-10 concurrent SSH tunnels to access databases, internal APIs, monitoring dashboards, and CI/CD infrastructure. Managing these tunnels manually across working sessions, system reboots, and network changes is a significant productivity drain. PortMUX aims to reduce this operational overhead to a single command while providing continuous assurance that all tunnels are healthy.

\newpage

## 3. Objectives

The primary objectives of the PortMUX project are:

1. **Centralized tunnel lifecycle management**: Provide a single CLI tool to create, list, remove, and refresh SSH port forwards, with all tunnels organized in a persistent tmux session.

2. **Independent tunnel isolation**: Run each SSH forward in its own tmux window so that individual tunnels can be inspected, restarted, or killed without affecting others.

3. **Automated health monitoring**: Implement an asynchronous health checking system that detects dead processes, SSH error conditions, and unresponsive ports — then automatically restarts failed tunnels.

4. **Configuration-driven workflows**: Support TOML-based configuration files with named profiles, allowing users to define environment-specific tunnel sets and switch between them with a single command.

5. **Startup automation**: Enable users to define startup commands that execute automatically when a session is initialized, eliminating the need to manually add tunnels after each reboot or re-initialization.

6. **Extensible backend architecture**: Design the system with a protocol-based backend abstraction so that the tunnel execution layer (currently tmux) can be replaced with alternative backends (e.g., systemd units, subprocess management) without modifying the core logic.

7. **Comprehensive test coverage**: Maintain a thorough test suite with both mocked unit tests for fast development feedback and Docker-based end-to-end tests for validating real SSH tunnel behavior.

\newpage

## 4. Scope

### 4.1 In Scope

- Management of SSH local (`-L`) and remote (`-R`) port forwards
- Persistent session management through tmux
- Real-time and background health monitoring with auto-restart
- TOML-based configuration with profile inheritance
- Startup command automation with session injection
- Rich terminal output with tables, colors, and progress indicators
- JSON output mode for machine-readable forward listings
- Comprehensive test suite (unit + E2E in Docker)

### 4.2 Out of Scope

- Dynamic SOCKS proxy (`-D`) forwarding
- Graphical user interface (GUI)
- Multi-host SSH jump chains (ProxyJump)
- SSH key management or agent lifecycle
- Windows operating system support (requires tmux)
- TUI (Text User Interface) mode — planned for a future phase

\newpage

## 5. Literature Survey

### 5.1 Existing Tools and Approaches

The following table compares existing solutions for SSH tunnel management with PortMUX:

| Feature | Manual SSH | autossh | sshuttle | Shell Scripts | PortMUX |
|---|---|---|---|---|---|
| Multiple tunnel management | No | One per instance | VPN-style, not per-port | Ad-hoc | Yes, centralized |
| Health monitoring | None | Heartbeat only | None | Manual | 3-layer async checks |
| Auto-restart on failure | No | Yes (process-level) | No | Manual | Yes, with retry limits |
| Configuration profiles | No | No | No | Possible | Yes, TOML with inheritance |
| Tunnel isolation | N/A | Per-process | N/A | N/A | Per-tmux-window |
| Tunnel observability | None | None | None | None | Pane inspection + logs |
| Startup automation | No | No | No | Possible | Built-in |
| Error pattern detection | No | No | No | No | Yes (8 SSH patterns) |
| TCP port verification | No | No | No | No | Yes |
| Bulk operations | No | No | No | Possible | Yes (refresh/remove all) |

### 5.2 Detailed Analysis

**Manual SSH**: The baseline approach — running `ssh -N -L port:host:port user@server` in separate terminals. Offers no monitoring, no restart capability, and no centralized view. Tunnels are lost when the terminal closes unless backgrounded, in which case they become invisible.

**autossh**: A widely-used utility that monitors an SSH connection and restarts it if it drops. autossh uses a heartbeat mechanism (sending data through a monitoring port) to detect failures. However, it manages only a single connection per instance, provides no centralized management of multiple tunnels, and its heartbeat mechanism only detects process death — not application-level issues like an unresponsive port or a passphrase prompt. There is no configuration file support, and each tunnel requires its own autossh invocation.

**sshuttle**: A "poor man's VPN" that creates a transparent proxy using SSH. While sshuttle solves the problem of accessing multiple remote services, it operates at the network level (routing all traffic through the SSH connection) rather than at the port level. It does not support selective per-port forwarding, offers no health monitoring, and is not suitable for scenarios where only specific ports need to be forwarded.

**Shell scripts**: Many developers maintain ad-hoc Bash/Zsh scripts to start their tunnel sets. While this approach can work, it lacks health monitoring, auto-restart, profile management, and observability. Scripts are typically fragile and tightly coupled to a specific environment.

### 5.3 Research Gap

None of the existing solutions provide the combination of per-tunnel isolation, multi-layer health checking (process + terminal output + TCP probe), automatic reconnection with retry limits, and a configuration-driven profile system. PortMUX addresses this gap by combining tmux's session management capabilities with an async health monitoring system.

\newpage

## 6. Proposed System

### 6.1 Design Philosophy

PortMUX is built on three core design principles:

1. **One tunnel, one window**: Each SSH forward runs in its own tmux window. This provides natural isolation — if one tunnel crashes, others are unaffected. Users can attach to any window to inspect the SSH process output, see error messages, or manually interact with the tunnel.

2. **Backend abstraction via protocols**: The system uses Python's `Protocol` type to define a `TunnelBackend` interface. The current implementation (`TmuxBackend`) delegates to tmux via the `libtmux` library, but the protocol could be implemented by a systemd backend, a subprocess backend, or any other execution layer without changing the service or command layers.

3. **Async health checking**: Health checks use Python's `asyncio` to run all tunnel checks concurrently. For a session with 10 tunnels, all 10 are checked in parallel rather than sequentially, keeping the monitoring cycle fast regardless of tunnel count.

### 6.2 Key Design Decisions

**Window naming convention**: Each tmux window is named `{Direction}:{Spec}` (e.g., `L:8080:localhost:80`). This encoding serves as both a unique identifier and a human-readable description. The monitor window uses the reserved name `_monitor` and is excluded from forward listings.

**Service layer pattern**: Commands are thin Click wrappers that parse arguments and delegate to `PortmuxService`. This keeps the CLI framework decoupled from business logic, making the service independently testable.

**Health state machine**: Tunnel health follows a finite state machine with six states (`STARTING`, `HEALTHY`, `UNHEALTHY`, `RESTARTING`, `DEAD`, `UNKNOWN`) and validated transitions. Invalid state transitions are silently ignored, preventing oscillation in noisy network conditions.

**Dual monitoring modes**: The foreground `watch` command writes to the terminal only, while the background `_monitor-daemon` writes to the log file only. This design prevents duplicate log entries when both are running simultaneously.

\newpage

## 7. System Architecture

### 7.1 Layered Architecture

PortMUX follows a five-layer architecture where each layer has a well-defined responsibility and only communicates with adjacent layers:

```
+--------------------------------------------------+
|              PRESENTATION LAYER                   |
|          cli.py + commands/*.py (Click)           |
|   Parses CLI arguments, delegates to service      |
+--------------------------------------------------+
                        |
+--------------------------------------------------+
|                 CORE LAYER                        |
|     PortmuxService — central orchestrator         |
|     Config + Profiles — TOML configuration        |
|     Health Monitor — async health checking        |
+--------------------------------------------------+
                        |
+--------------------------------------------------+
|            INFRASTRUCTURE LAYER                   |
|     ssh/forwards.py — SSH command construction     |
|     TunnelBackend Protocol — backend interface     |
+--------------------------------------------------+
                        |
+--------------------------------------------------+
|              EXECUTION LAYER                      |
|     tmux/ via libtmux — session/window mgmt       |
|     TmuxBackend — protocol implementation         |
+--------------------------------------------------+
                        |
+--------------------------------------------------+
|              EXTERNAL SYSTEMS                     |
|         tmux server  |  SSH processes             |
+--------------------------------------------------+
```

### 7.2 Data Flow

The following sequence describes the lifecycle of adding a new forward:

1. User runs `portmux add L 8080:localhost:80 user@server`
2. Click parses the arguments and passes them to the `add` command
3. The command creates/retrieves a `PortmuxService` instance and calls `service.add_forward()`
4. The service resolves the SSH identity (explicit → config → auto-detected)
5. The service ensures the tmux session exists (auto-initializes if needed)
6. `ssh/forwards.py` validates the port specification and constructs the SSH command string
7. The `TunnelBackend.create_tunnel()` method is called to create a new tmux window
8. `TmuxBackend` uses `libtmux` to create the window and send the SSH command
9. The health logger records the event and flushes to disk
10. Rich terminal output confirms success to the user

### 7.3 Health Monitoring Data Flow

1. The `TunnelMonitor` enters its check cycle (every 30 seconds by default)
2. It calls `list_forwards()` to discover all active tunnels
3. `HealthChecker.check_all()` runs three checks concurrently for each tunnel:
   - **Process check**: Queries tmux pane diagnostics to verify the SSH process is alive
   - **Pane output check**: Reads the last lines of the tmux pane and pattern-matches against 8 known SSH error strings (e.g., "Permission denied", "Connection refused", "Enter passphrase")
   - **TCP port probe**: For local forwards, opens a TCP connection to `127.0.0.1:<port>` with a configurable timeout
4. Results are combined into a `HealthResult` with a health verdict
5. The monitor processes state transitions, logs events, and triggers auto-restart for dead tunnels

\newpage

## 8. Technology Stack

### 8.1 Runtime Technologies

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core programming language; chosen for asyncio support and rich ecosystem |
| **Click** | 8.1+ | CLI framework; provides command groups, argument parsing, context passing |
| **Rich** | 14.1+ | Terminal formatting; tables, colored output, progress bars, spinners |
| **libtmux** | 0.55+ | Python wrapper for tmux; session, window, and pane management |
| **toml** | 0.10+ | TOML configuration file parser |
| **colorama** | 0.4+ | Cross-platform ANSI color support for terminal output |
| **asyncio** | stdlib | Async framework for concurrent health checks and TCP probing |
| **tmux** | system | Terminal multiplexer; provides the persistent session execution layer |
| **OpenSSH** | system | SSH client for port forwarding tunnels |

### 8.2 Development and Testing Tools

| Tool | Purpose |
|---|---|
| **pytest** | Test framework with fixtures, markers, and parametrize |
| **pytest-mock** | Provides `mocker` fixture for clean mocking |
| **pytest-cov** | Code coverage measurement and reporting |
| **pytest-asyncio** | Async test support for health checker tests |
| **ruff** | Fast Python linter and formatter (replaces flake8 + black) |
| **bandit** | Security-focused static analysis |
| **vulture** | Dead code detection |
| **pre-commit** | Git hook framework for automated quality checks |
| **Docker** | Container runtime for E2E test environment |
| **Hatchling** | Python build system (PEP 517 compliant) |

\newpage

## 9. Module Description

The source code is organized into 8 modules across 35 files:

### 9.1 Root Module (`src/portmux/`)

Contains the application entry point, shared models, and utilities.

- **`cli.py`**: Defines the main Click command group with global options (`--session`, `--verbose`, `--config`, `--version`). Initializes the `PortmuxService` and passes it through Click's context object.
- **`models.py`**: Contains 8 dataclass definitions: `ParsedSpec`, `TunnelInfo`, `ForwardInfo`, `TunnelDiagnostics`, `StartupCommand`, `StartupConfig`, `ProfileConfig`, `MonitorConfig`, and `PortmuxConfig`. These serve as the shared data contracts between all modules.
- **`exceptions.py`**: Defines the exception hierarchy: `PortMuxError` (base) with subclasses `TmuxError`, `SSHError`, and `ConfigError`.
- **`utils.py`**: Input validation, table formatting helpers, and error handling utilities.

### 9.2 Commands Module (`commands/`)

Thin Click command wrappers — each file defines one CLI command:

- **`init.py`**: `portmux init` — creates the tmux session, loads profiles, runs startup commands, starts the background monitor.
- **`add.py`**: `portmux add` — adds a local or remote forward with identity resolution.
- **`list.py`**: `portmux list` — shows active forwards with optional `--json` output.
- **`remove.py`**: `portmux remove` — removes a specific forward, all forwards, or destroys the entire session.
- **`refresh.py`**: `portmux refresh` — reconnects a single forward or all forwards with configurable delay.
- **`status.py`**: `portmux status` — runs an on-demand health check and displays a status table with monitor state and recent errors.
- **`watch.py`**: `portmux watch` — runs a foreground health monitor loop with live terminal output.
- **`monitor.py`**: `portmux monitor start/stop/status` — manages the background monitor daemon. Also contains the hidden `_monitor-daemon` command.
- **`profile.py`**: `portmux profile list/show/active` — displays profile configuration.

### 9.3 Core Module (`core/`)

The central orchestration layer:

- **`service.py`**: `PortmuxService` class — the heart of PortMUX. Coordinates session lifecycle, forward management, health checking, monitor control, and startup execution. All mutation methods log events through `HealthLogger` and flush immediately.
- **`config.py`**: `load_config()` reads TOML files and returns a `PortmuxConfig` dataclass. `validate_config()` validates raw TOML dictionaries. `get_default_identity()` auto-detects SSH keys from `~/.ssh/`.
- **`profiles.py`**: Profile loading and inheritance logic. `load_profile()` merges profile values with base config; `None` values inherit from the parent.
- **`startup.py`**: Parses and executes startup commands. Auto-injects `--session` flag into PortMUX commands if not present.
- **`output.py`**: `Output` class wrapping Rich console — provides `success()`, `error()`, `warning()`, `info()`, `verbose()`, `dim()`, and `progress_context()` methods. Injected into all commands; no module-level console instances.

### 9.4 Backend Module (`backend/`)

Pluggable execution layer:

- **`protocol.py`**: Defines the `TunnelBackend` Protocol — a runtime-checkable interface with 8 methods: `create_session`, `session_exists`, `kill_session`, `create_tunnel`, `kill_tunnel`, `tunnel_exists`, `list_tunnels`, and `get_tunnel_diagnostics`.
- **`tmux.py`**: `TmuxBackend` — the concrete implementation using `libtmux`. Translates protocol calls into tmux session and window operations.

### 9.5 Health Module (`health/`)

The asynchronous health monitoring subsystem:

- **`checker.py`**: `HealthChecker` class — runs three checks per tunnel concurrently using `asyncio.gather()`. Detects 8 SSH error patterns (passphrase prompts, permission denied, host key failures, DNS errors, connection refused/timed out, network unreachable, no route to host).
- **`monitor.py`**: `TunnelMonitor` class — runs continuous check cycles with configurable interval. Maintains per-tunnel state and retry counts. Handles state transitions via the state machine. Triggers auto-restart for dead tunnels. Prints heartbeat summaries.
- **`logger.py`**: `HealthLogger` — buffered file logger that writes events to `~/.portmux/health.log`. Supports `info()`, `warning()`, `error()`, and `heartbeat()` methods. Must be explicitly flushed at natural boundaries.
- **`state.py`**: Defines the `TunnelHealth` enum (6 states), `HealthResult` dataclass, the `VALID_TRANSITIONS` map, and the `can_transition()` validation function.

### 9.6 SSH Module (`ssh/`)

SSH command construction and forward management:

- **`forwards.py`**: Core forward operations: `add_forward()`, `remove_forward()`, `list_forwards()`, `refresh_forward()`, and `parse_port_spec()`. Validates port specifications via regex, constructs SSH command strings, and delegates tunnel lifecycle to the backend.

### 9.7 Tmux Module (`tmux/`)

Low-level tmux operations via `libtmux`:

- **`session.py`**: `create_session()`, `session_exists()`, `kill_session()` — direct libtmux wrappers.
- **`windows.py`**: `create_window()`, `kill_window()`, `window_exists()`, `list_windows()`, `get_window_diagnostics()` — window and pane operations including diagnostic data extraction for health checking.

\newpage

## 10. Implementation Details

### 10.1 Health State Machine

The health monitoring system uses a finite state machine to track tunnel health:

```
                  +----------+
                  | UNKNOWN  |
                  +----+-----+
                       |
            +----------+----------+
            |          |          |
            v          v          v
       +---------+ +--------+ +------+
       |STARTING | |HEALTHY | | DEAD |
       +----+----+ +---+----+ +--+---+
            |          |         |
            v          v         v
       +---------+ +----------+ +-----------+
       | HEALTHY | |UNHEALTHY | | STARTING  |
       +---------+ +----+-----+ +-----------+
                        |
                        v
                   +-----------+
                   |RESTARTING |
                   +-----+-----+
                         |
                    +----+----+
                    |         |
                    v         v
               +--------+ +------+
               |STARTING| | DEAD |
               +--------+ +------+
```

**States:**
- `UNKNOWN` — initial state before first check
- `STARTING` — tunnel recently created or restarted, awaiting first health check
- `HEALTHY` — SSH process alive, no errors detected, port accepting connections (for local forwards)
- `UNHEALTHY` — SSH process alive but exhibiting problems (error patterns in output, port not responding)
- `RESTARTING` — tunnel is being killed and recreated
- `DEAD` — SSH process not running or tunnel window vanished

**Transition validation**: Only transitions defined in the `VALID_TRANSITIONS` map are allowed. Invalid transitions are silently dropped, preventing state oscillation during transient network issues.

### 10.2 Three-Layer Health Check

Each check cycle runs three independent checks per tunnel:

**Layer 1 — Process Liveness**: Queries tmux pane diagnostics to determine if the pane's active process is `ssh`. If the pane is marked as dead (process exited), the tunnel is immediately classified as `DEAD`.

**Layer 2 — Terminal Output Scanning**: Reads the visible content of the tmux pane and scans for 8 known error patterns:

| Pattern | Indicates |
|---|---|
| `Enter passphrase` | Key requires passphrase, tunnel is stuck |
| `Permission denied` | Authentication failure |
| `Host key verification failed` | Unknown or changed host key |
| `Could not resolve hostname` | DNS resolution failure |
| `Connection refused` | Target port not listening |
| `Connection timed out` | Network path blocked |
| `Network is unreachable` | No route at network level |
| `No route to host` | No route at IP level |

**Layer 3 — TCP Port Probe**: For local forwards only, the checker opens a TCP connection to `127.0.0.1:<local_port>` with a configurable timeout (default 2 seconds). This verifies that the tunnel is actually passing traffic, not just maintaining an SSH session.

### 10.3 Backend Protocol

The `TunnelBackend` protocol defines 8 methods that any backend must implement:

```python
class TunnelBackend(Protocol):
    def create_session(self, session_name: str) -> bool
    def session_exists(self, session_name: str) -> bool
    def kill_session(self, session_name: str) -> bool
    def create_tunnel(self, name: str, command: str, session_name: str) -> bool
    def kill_tunnel(self, name: str, session_name: str) -> bool
    def tunnel_exists(self, name: str, session_name: str) -> bool
    def list_tunnels(self, session_name: str) -> list[TunnelInfo]
    def get_tunnel_diagnostics(self, name: str, session_name: str) -> TunnelDiagnostics | None
```

Using Python's `@runtime_checkable` decorator enables structural subtyping — any class implementing these methods satisfies the protocol without explicit inheritance. This design choice allows future backends to be added without modifying existing code.

### 10.4 Configuration and Profile Inheritance

Configuration uses a TOML file (`~/.portmux/config.toml`) parsed into a `PortmuxConfig` dataclass. Profiles are defined under `[profiles.<name>]` sections. When a profile is loaded, its fields are merged with the base configuration:

- Fields set to a value override the base config
- Fields set to `None` (or omitted) inherit from the base config
- Startup commands in a profile replace (not append to) base startup commands

Identity resolution follows a three-tier priority:
1. Explicit `-i` flag on the command line
2. `default_identity` from config (or active profile)
3. Auto-detected from `~/.ssh/` (checks for common key filenames)

\newpage

## 11. Testing Strategy

### 11.1 Overview

PortMUX maintains 364 automated tests organized into two categories:

| Category | Tests | Files | Strategy |
|---|---|---|---|
| Unit tests | 332 | 28 | Mocked dependencies, fast execution |
| E2E tests | 32 | 5 | Docker container, real tmux + SSH |

### 11.2 Unit Testing

Unit tests use Python's `unittest.mock` to isolate each layer. The test directory structure mirrors the source layout, making it easy to locate tests for any module.

**Service layer mocking**: Internal imports use underscore aliases (`_add_forward`, `_list_forwards`, etc.), and mocks target these aliased paths:

```python
@patch("portmux.core.service._add_forward")
@patch("portmux.core.service._list_forwards")
def test_add_and_list(self, mock_list, mock_add):
    ...
```

**Command testing**: Uses Click's `CliRunner` to invoke commands programmatically:

```python
result = runner.invoke(add_command, ["L", "8080:localhost:80", "user@host"],
                       obj={"session": "portmux", "config": None,
                            "verbose": False, "output": Output()})
assert result.exit_code == 0
```

**Backend testing**: Injects a `Mock(spec=TmuxBackend)` directly into forward functions:

```python
backend = Mock(spec=TmuxBackend)
backend.tunnel_exists.return_value = False
backend.create_tunnel.return_value = True
result = add_forward("L", "8080:localhost:80", "user@host", backend=backend)
```

**Async health testing**: Uses `pytest-asyncio` for testing the health checker and monitor:

```python
@pytest.mark.asyncio
async def test_check_healthy_tunnel(self):
    result = await checker.check_one(forward)
    assert result.health == TunnelHealth.HEALTHY
```

### 11.3 End-to-End Testing

E2E tests run in a Docker container that provides a controlled environment with real tmux and SSH servers. No mocks are used.

**Docker environment**:
- Base image with Python 3.10+, tmux, and OpenSSH server
- SSH server configured for localhost connections with key-based authentication
- Entry point script that starts sshd and runs pytest

**Key fixtures**:
- `session_name` — generates a unique session name per test with automatic teardown
- `portmux_service` / `monitored_service` — real `PortmuxService` with a real `TmuxBackend`
- `tcp_server` — threaded echo server on a dynamically allocated port (for health check verification)
- `free_port` — factory function that returns unused ephemeral ports
- `wait_for_port()` / `wait_for_condition()` — polling helpers that avoid fixed sleeps

**E2E test coverage**:

| Area | Tests | What's Verified |
|---|---|---|
| Session lifecycle | 8 | Init, destroy, force recreate, session isolation |
| Forward lifecycle | 10 | Add/remove local and remote forwards, refresh, traffic flow |
| Health checks | 8 | Healthy detection, dead detection, unhealthy detection, diagnostics |
| Monitor | 6 | Auto-restart, max retries, logging output, daemon lifecycle |

\newpage

## 12. Project Statistics

### 12.1 Codebase Metrics

| Metric | Value |
|---|---|
| Source files | 35 |
| Source lines of code | ~3,991 |
| Test files | 43 |
| Test lines of code | ~6,113 |
| Total lines of code | ~10,104 |
| Test functions | 364 |
| Source modules | 8 |
| Data model classes | 8 dataclasses + 1 enum |
| CLI commands | 12 (including subcommands) |
| Runtime dependencies | 5 |
| Development dependencies | 8 |

### 12.2 Development Timeline

| Phase | Period | Deliverable |
|---|---|---|
| Phase 1 | Aug 2025 | Core tmux/SSH infrastructure |
| Phase 2 | Sep 2025 | Full CLI with Click, all commands, unit test suite |
| Phase 3 | Oct 2025 | Configuration system, profiles, startup automation |
| Phase 4 | Dec 2025 | Async health check system |
| Phase 5 | Jan 2026 | Background monitor daemon + health logging |
| Phase 6 | Feb 2026 | E2E tests in Docker |
| Refinement | Mar 2026 | Documentation, bug fixes, known issues |

**Total commits**: 30 | **Development duration**: ~7 months

### 12.3 Version

Current release: **v1.2.0**

\newpage

## 13. Results and Output

### 13.1 Session Initialization

```
$ portmux init
✓ Successfully initialized PortMUX session 'portmux'
✓ Startup commands completed successfully
✓ Background health monitor started
ℹ Use 'portmux status' to view session details
```

### 13.2 Adding Forwards

```
$ portmux add L 8080:localhost:80 user@server.com
✓ Successfully created local forward 'L:8080:localhost:80'

$ portmux add R 9000:localhost:3000 user@server.com
✓ Successfully created remote forward 'R:9000:localhost:3000'
```

### 13.3 Listing Forwards

```
$ portmux list
┌─────────────────────────┬───────────┬──────────────────────┐
│ Name                    │ Direction │ Status               │
├─────────────────────────┼───────────┼──────────────────────┤
│ L:8080:localhost:80     │ Local     │ running              │
│ R:9000:localhost:3000   │ Remote    │ running              │
└─────────────────────────┴───────────┴──────────────────────┘
```

### 13.4 Health Status

```
$ portmux status
Session: portmux (active)

┌─────────────────────────┬─────────┬──────────┬──────────┐
│ Tunnel                  │ Process │ Port     │ Health   │
├─────────────────────────┼─────────┼──────────┼──────────┤
│ L:8080:localhost:80     │ alive   │ open     │ healthy  │
│ R:9000:localhost:3000   │ alive   │ n/a      │ healthy  │
└─────────────────────────┴─────────┴──────────┴──────────┘

Monitor: running (background)
Last check: 15s ago | Next check: in 15s
```

### 13.5 Health Monitor Watch Mode

```
$ portmux watch
[L:8080:localhost:80] Healthy: SSH alive, port accepting connections
[R:9000:localhost:3000] Healthy: SSH process alive, no errors detected
✓ 2/2 healthy — 14:32:15

[L:8080:localhost:80] Dead: SSH process not running (exit: 255)
[L:8080:localhost:80] Restarting (attempt 1/3)...
[L:8080:localhost:80] Healthy: SSH alive, port accepting connections
✓ 2/2 healthy — 14:32:47
```

### 13.6 Profile Workflow

```
$ portmux init --profile production
✓ Profile 'production' loaded
✓ Successfully initialized PortMUX session 'portmux-prod'
✓ Startup commands completed successfully
✓ Background health monitor started

$ portmux profile list
Available profiles:
  - development (session: portmux-dev)
  - production  (session: portmux-prod)
```

\newpage

## 14. Future Scope

The following enhancements are planned or identified for future development:

1. **SSH Agent Awareness** (Phase 7): Verify that SSH keys are not only present on disk but also loaded in the SSH agent and usable without passphrase prompts. This would prevent the common failure mode where a tunnel silently hangs on an `Enter passphrase` prompt.

2. **TUI Mode** (Phase 7): A full-screen terminal user interface using a library like Textual, providing real-time tunnel status, interactive management, and log viewing in a single dashboard.

3. **Health Detail Surfacing**: Currently, the health checker produces detailed diagnostic strings (e.g., "SSH alive but port not responding"), but these details are not fully surfaced to the user through `portmux status`. Future work would expose these details in the status table and via `--json` output.

4. **Cross-Session Port Conflict Detection**: Two profiles can currently bind the same local port in different sessions, causing silent failures. A port reservation system would detect and warn about conflicts.

5. **Extended JSON Output**: Add `--json` support to `status`, `monitor status`, and `profile` commands for scripting and automation integration.

6. **Startup Command Error Visibility**: Capture and display stderr/stdout from failed startup commands, which are currently invisible to the user.

7. **systemd Backend**: An alternative `TunnelBackend` implementation using systemd units instead of tmux, enabling tunnel management on headless servers without tmux.

8. **SSH ProxyJump Support**: Enable multi-hop SSH tunneling through jump hosts, a common pattern in enterprise environments.

\newpage

## 15. Conclusion

PortMUX successfully addresses the operational challenges of managing multiple SSH port forwards by providing a unified CLI tool with persistent session management, automated health monitoring, and configuration-driven workflows. The project demonstrates the application of several software engineering principles:

- **Layered architecture** for separation of concerns and maintainability
- **Protocol-based polymorphism** for backend extensibility without inheritance
- **Asynchronous programming** for concurrent health checking across multiple tunnels
- **Finite state machines** for predictable and debuggable health state management
- **Comprehensive testing** with both isolated unit tests and realistic end-to-end tests in Docker

With approximately 4,000 lines of production code and 6,100 lines of test code, the project maintains a healthy test-to-code ratio of 1.5:1, reflecting a commitment to code quality and reliability. The phased development approach over 7 months allowed for iterative refinement, with each phase building on the previous one's foundation.

PortMUX fills a genuine gap in the SSH tooling ecosystem — no existing tool combines per-tunnel isolation, multi-layer async health monitoring, automatic reconnection, and profile-based configuration management in a single, cohesive package.

\newpage

## 16. References

1. OpenSSH Manual Pages — `ssh(1)`, specifically the `-L` and `-R` options for port forwarding. Available at: https://man.openbsd.org/ssh

2. tmux Manual — Terminal multiplexer documentation for session, window, and pane management. Available at: https://man.openbsd.org/tmux

3. Python `asyncio` Documentation — Asynchronous I/O framework used for concurrent health checking. Available at: https://docs.python.org/3/library/asyncio.html

4. Click Documentation — Python CLI framework used for command-line interface design. Available at: https://click.palletsprojects.com/

5. Rich Documentation — Python library for rich terminal formatting. Available at: https://rich.readthedocs.io/

6. libtmux Documentation — Python scripting library for tmux. Available at: https://libtmux.git-pull.com/

7. TOML Specification — Configuration file format used by PortMUX. Available at: https://toml.io/

8. autossh — Automatically restart SSH sessions and tunnels. Available at: https://www.harding.motd.ca/autossh/

9. sshuttle — Transparent proxy server that works as a poor man's VPN. Available at: https://github.com/sshuttle/sshuttle

10. Python Protocols (PEP 544) — Structural subtyping for Python. Available at: https://peps.python.org/pep-0544/

11. pytest Documentation — Python testing framework. Available at: https://docs.pytest.org/

12. Docker Documentation — Container platform used for E2E testing environment. Available at: https://docs.docker.com/
