# Phase 1 Implementation Guide

## Overview
This phase establishes the core infrastructure for PortMUX using a simplified, flat structure with uv for package management. Each component is thoroughly tested before proceeding.

## Project Structure
```
portmux/
├── action/
│   └── phase1.md           # This file
├── src/
│   └── portmux/
│       ├── __init__.py
│       ├── session.py      # Tmux session functions
│       ├── windows.py      # Tmux window functions  
│       ├── forwards.py     # SSH forward functions
│       ├── config.py       # Configuration functions
│       └── exceptions.py   # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_session.py     # Tests for session functions
│   ├── test_windows.py     # Tests for window functions
│   ├── test_forwards.py    # Tests for forward functions
│   ├── test_config.py      # Tests for config functions
│   └── fixtures/           # Test data and mocks
├── pyproject.toml          # uv project configuration
└── uv.lock                 # uv lockfile (auto-generated)
```

## Setup Commands

### 1. Initialize uv Project
```bash
uv init --name portmux --lib
```

### 2. Add Dependencies
```bash
uv add rich                    # For future TUI
uv add --dev pytest pytest-mock  # Testing framework
```

### 3. Run Tests
```bash
uv run pytest                 # Run all tests
uv run pytest -v             # Verbose output
uv run pytest --cov=portmux  # With coverage (after adding pytest-cov)
```

## Implementation Details

### session.py Functions

#### `create_session(session_name: str = "portmux") -> bool`
- Creates a new tmux session dedicated to port forwards
- Returns True if successful, False if session already exists
- Uses: `tmux new-session -d -s {session_name}`

#### `session_exists(session_name: str = "portmux") -> bool`
- Checks if the portmux tmux session exists
- Returns True/False
- Uses: `tmux has-session -t {session_name}`

#### `kill_session(session_name: str = "portmux") -> bool`
- Destroys the portmux tmux session and all its windows
- Returns True if successful
- Uses: `tmux kill-session -t {session_name}`

### windows.py Functions

#### `create_window(name: str, command: str, session_name: str = "portmux") -> bool`
- Creates a new tmux window with given name and runs command
- Returns True if successful
- Uses: `tmux new-window -t {session_name} -n {name} {command}`

#### `kill_window(name: str, session_name: str = "portmux") -> bool`
- Kills a specific tmux window by name
- Returns True if successful
- Uses: `tmux kill-window -t {session_name}:{name}`

#### `list_windows(session_name: str = "portmux") -> List[dict]`
- Returns list of all windows in session with their details
- Each dict contains: name, status, command
- Uses: `tmux list-windows -t {session_name} -F "#{window_name}|#{window_flags}|#{pane_current_command}"`

#### `window_exists(name: str, session_name: str = "portmux") -> bool`
- Checks if a window with given name exists
- Returns True/False
- Implementation: checks if name in list_windows() results

### forwards.py Functions

#### `add_forward(direction: str, spec: str, host: str, identity: str = None) -> str`
- Creates SSH port forward in new tmux window
- direction: "L" for local, "R" for remote
- spec: port specification like "8080:localhost:80"
- host: SSH target like "user@hostname"
- identity: path to SSH key file (optional)
- Returns: window name created
- Window name format: "{direction}:{spec}"

#### `remove_forward(name: str) -> bool`
- Removes SSH forward by killing its tmux window
- name: window name (e.g., "L:8080:localhost:80")
- Returns True if successful

#### `list_forwards() -> List[dict]`
- Lists all active SSH forwards
- Returns list of dicts with: name, direction, spec, host, uptime, status
- Parses window names to extract forward details

#### `refresh_forward(name: str) -> bool`
- Removes existing forward and recreates it with same parameters
- Useful for reconnecting after network issues
- Returns True if successful

#### `parse_port_spec(spec: str) -> dict`
- Validates and parses port specifications
- Returns dict with parsed components
- Validates format: "local_port:remote_host:remote_port"

### config.py Functions

#### `load_config(config_path: str = "~/.portmux/config.toml") -> dict`
- Loads configuration from TOML file
- Returns dict with config values
- Creates default config if file doesn't exist

#### `get_default_identity() -> str`
- Returns path to default SSH identity file
- Checks common locations: ~/.ssh/id_rsa, ~/.ssh/id_ed25519
- Returns None if no default found

#### `validate_config(config: dict) -> bool`
- Validates configuration structure and values
- Returns True if valid, raises exception if invalid

### exceptions.py Classes

#### `PortMuxError(Exception)`
- Base exception class for all PortMux errors

#### `TmuxError(PortMuxError)`
- Raised when tmux operations fail

#### `SSHError(PortMuxError)`
- Raised when SSH operations fail

#### `ConfigError(PortMuxError)`
- Raised when configuration is invalid

## Testing Strategy

### Test Structure
- Each module has corresponding test file
- Use pytest-mock for mocking subprocess calls
- Test both success and failure scenarios
- Include edge cases and error conditions

### Mock Strategy
- Mock all `subprocess.run()` calls to avoid actual tmux operations
- Use fixtures for common test data
- Test tmux command generation without execution

### Coverage Goals
- Aim for >90% code coverage
- Test all public functions
- Include error handling tests

## Implementation Order

1. **Setup Project**: Initialize uv, create structure
2. **exceptions.py**: Define custom exceptions
3. **session.py + tests**: Basic tmux session management
4. **windows.py + tests**: Tmux window operations
5. **forwards.py + tests**: SSH forward logic
6. **config.py + tests**: Configuration handling
7. **Integration tests**: End-to-end testing

## Validation Criteria

Before moving to Phase 2, ensure:
- All tests pass with >90% coverage
- Can create/destroy tmux sessions
- Can manage tmux windows
- Can parse and validate port specifications
- Error handling works correctly
- Configuration loading works

## Next Phase Preview

Phase 2 will add:
- CLI interface using click
- Basic command-line operations
- Integration with Phase 1 functions