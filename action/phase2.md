# Phase 2 Implementation Plan: CLI Interface

## Overview
Phase 2 builds a complete command-line interface on top of the robust Phase 1 foundation, providing scriptable access to all PortMUX functionality before moving to the TUI in Phase 3.

## Goals
1. **Complete CLI Implementation**: Full command-line interface using Click framework
2. **Scriptability**: Enable automation and integration with other tools
3. **User Experience**: Intuitive commands with helpful error messages and validation
4. **Session Management**: Automatic session initialization and management
5. **Comprehensive Testing**: CLI command testing with integration tests

## New Dependencies
- `click` - Modern CLI framework with excellent UX
- `colorama` - Cross-platform colored terminal output
- `pytest-cov` - Test coverage reporting

## File Structure Changes
```
portmux/
├── action/
│   ├── phase1.md
│   └── phase2.md           # NEW: This implementation guide
├── src/
│   └── portmux/
│       ├── __init__.py     # UPDATED: Add version info
│       ├── cli.py          # NEW: Main CLI interface
│       ├── commands/       # NEW: Command modules
│       │   ├── __init__.py
│       │   ├── add.py      # Add forward command
│       │   ├── remove.py   # Remove forward command
│       │   ├── list.py     # List forwards command
│       │   ├── refresh.py  # Refresh forward command
│       │   ├── status.py   # Session status command
│       │   └── init.py     # Initialize session command
│       ├── utils.py        # NEW: CLI utility functions
│       └── [existing files unchanged]
├── tests/
│   ├── test_cli.py         # NEW: CLI integration tests
│   ├── test_commands/      # NEW: Command-specific tests
│   │   ├── __init__.py
│   │   ├── test_add.py
│   │   ├── test_remove.py
│   │   ├── test_list.py
│   │   ├── test_refresh.py
│   │   ├── test_status.py
│   │   └── test_init.py
│   └── [existing test files unchanged]
└── [existing files unchanged]
```

## Command Interface Design

### Main CLI Entry Point
```bash
portmux --help                 # Show help
portmux --version             # Show version
portmux init                  # Initialize session
portmux status                # Show session status
```

### Forward Management Commands
```bash
# Add forwards
portmux add L 8080:localhost:80 user@host              # Local forward
portmux add R 9000:localhost:9000 user@host            # Remote forward
portmux add L 3000:db.local:5432 user@host -i ~/.ssh/key  # With identity

# List forwards
portmux list                  # List all forwards
portmux list --json         # JSON output for scripting

# Remove forwards
portmux remove L:8080:localhost:80    # Remove specific forward
portmux remove --all                  # Remove all forwards

# Refresh forwards
portmux refresh L:8080:localhost:80   # Refresh specific forward
portmux refresh --all                 # Refresh all forwards
```

### Session Management
```bash
portmux status               # Show session and forwards status
portmux init                 # Create session if not exists
portmux destroy              # Destroy session and all forwards
```

## Implementation Strategy

### Phase 2.1: Core CLI Framework
1. **Set up Click CLI structure**
   - Main `cli.py` with Click group
   - Basic command registration
   - Global options (--verbose, --config, etc.)

2. **Create CLI utilities**
   - Error handling and user-friendly messages
   - Configuration loading with CLI overrides
   - Session initialization helpers

### Phase 2.2: Forward Management Commands
3. **Implement `add` command**
   - Parse direction, spec, and host arguments
   - Validate inputs before calling core functions
   - Auto-initialize session if needed

4. **Implement `list` command**
   - Display forwards in human-readable table format
   - JSON output option for scripting
   - Status indicators and color coding

5. **Implement `remove` command**
   - Single forward removal by name
   - Bulk removal with `--all` flag
   - Confirmation prompts for destructive operations

6. **Implement `refresh` command**
   - Single forward refresh by name
   - Bulk refresh with `--all` flag
   - Progress indicators for multiple operations

### Phase 2.3: Session Management
7. **Implement `status` command**
   - Show session existence and health
   - List all forwards with status
   - Connection health indicators

8. **Implement `init` command**
   - Initialize session if not exists
   - Validate tmux availability
   - Set up default configuration

9. **Implement `destroy` command**
   - Safe session destruction
   - Confirmation prompts
   - Cleanup operations

### Phase 2.4: Advanced Features
10. **Configuration integration**
    - CLI argument overrides for config values
    - Profile support for different environments
    - Validation and error reporting

11. **Error handling and UX**
    - Comprehensive error messages
    - Helpful suggestions for common issues
    - Progress indicators for long operations

## Command Specifications

### `portmux add <direction> <spec> <host> [options]`
- **Arguments**:
  - `direction`: "L" or "R" (local/remote)
  - `spec`: Port specification (local:remote_host:remote_port)
  - `host`: SSH target (user@hostname)
- **Options**:
  - `-i, --identity PATH`: SSH identity file
  - `-s, --session NAME`: Custom session name
  - `--no-check`: Skip connectivity validation
- **Behavior**:
  - Auto-initialize session if needed
  - Validate all inputs before execution
  - Provide clear success/failure feedback

### `portmux list [options]`
- **Options**:
  - `--json`: Output in JSON format
  - `-s, --session NAME`: Custom session name
  - `--status`: Include connection status
- **Output**: Table with columns: Name, Direction, Spec, Status, Uptime

### `portmux remove <name> [options]`
- **Arguments**:
  - `name`: Forward name (e.g., "L:8080:localhost:80")
- **Options**:
  - `--all`: Remove all forwards
  - `-f, --force`: Skip confirmation
  - `-s, --session NAME`: Custom session name

### `portmux refresh <name> [options]`
- **Arguments**:
  - `name`: Forward name to refresh
- **Options**:
  - `--all`: Refresh all forwards
  - `-s, --session NAME`: Custom session name
  - `--delay SECONDS`: Delay between kill and recreate

### `portmux status [options]`
- **Options**:
  - `-s, --session NAME`: Custom session name
  - `--check-connections`: Test forward connectivity
- **Output**: Session info + forward summary table

### `portmux init [options]`
- **Options**:
  - `-s, --session NAME`: Custom session name
  - `--config PATH`: Custom config file
- **Behavior**:
  - Create session if not exists
  - Initialize default configuration
  - Validate tmux availability

### `portmux destroy [options]`
- **Options**:
  - `-s, --session NAME`: Custom session name
  - `-f, --force`: Skip confirmation
- **Behavior**:
  - Destroy session and all forwards
  - Confirmation prompt unless forced
  - Clean shutdown of all connections

## Setup Commands

### Add Dependencies
```bash
uv add click colorama               # CLI framework and colors
uv add --dev pytest-cov            # Coverage reporting
```

### Project Configuration
Update `pyproject.toml` to include CLI entry point:
```toml
[project.scripts]
portmux = "portmux.cli:main"
```

### Development Workflow
```bash
uv run portmux --help              # Test CLI during development
uv run pytest --cov=portmux        # Run tests with coverage
uv run portmux add L 8080:localhost:80 user@host  # Test real commands
```

## Testing Strategy

### Unit Tests
- Each command module tested independently
- Mock all Phase 1 function calls
- Test argument parsing and validation
- Test error handling and edge cases

### Integration Tests
- End-to-end CLI command testing
- Mock tmux operations but test full workflow
- Test configuration loading and overrides
- Test session auto-initialization

### Coverage Goals
- >90% code coverage for all CLI modules
- All command combinations tested
- Error scenarios thoroughly covered

### Test Structure
```
tests/
├── test_cli.py                 # Main CLI entry point tests
├── test_utils.py              # CLI utility function tests
├── test_commands/
│   ├── test_add.py           # Add command tests
│   ├── test_list.py          # List command tests
│   ├── test_remove.py        # Remove command tests
│   ├── test_refresh.py       # Refresh command tests
│   ├── test_status.py        # Status command tests
│   ├── test_init.py          # Init command tests
│   └── test_destroy.py       # Destroy command tests
└── test_integration.py       # End-to-end CLI tests
```

## Success Criteria
Before moving to Phase 3 (TUI), ensure:

1. **Complete CLI Functionality**
   - All planned commands implemented and working
   - Comprehensive help text and documentation
   - Error handling covers all edge cases

2. **Robust Testing**
   - All tests passing with >90% coverage
   - Integration tests validate end-to-end workflows
   - CLI commands work with real tmux (manual testing)

3. **User Experience**
   - Intuitive command structure and help
   - Clear error messages with actionable advice
   - Consistent output formatting

4. **Scriptability**
   - JSON output options where needed
   - Exit codes follow conventions
   - Automation-friendly behavior

5. **Package Installation**
   - CLI entry point works after `uv install`
   - Commands available system-wide
   - Proper version information displayed

## Implementation Order
1. **Setup CLI Framework**
   - Add dependencies (click, colorama, pytest-cov)
   - Create basic CLI structure with Click
   - Set up entry point in pyproject.toml

2. **Core Infrastructure**
   - Implement CLI utilities and helpers
   - Create configuration loading with CLI overrides
   - Set up error handling framework

3. **Session Management Commands**
   - Implement `init` command (foundation)
   - Implement `status` command (visibility)
   - Implement `destroy` command (cleanup)

4. **Forward Management Commands**
   - Implement `add` command (core functionality)
   - Implement `list` command (visibility)
   - Implement `remove` command (management)
   - Implement `refresh` command (maintenance)

5. **Advanced Features and Polish**
   - Add JSON output options
   - Implement progress indicators
   - Enhance error messages and help text
   - Add configuration validation

6. **Comprehensive Testing**
   - Unit tests for all commands
   - Integration tests for workflows
   - Manual testing with real tmux
   - Performance and edge case testing

## Phase 2 Deliverables

Upon completion, Phase 2 will provide:

1. **Complete CLI Tool**: Fully functional `portmux` command-line tool
2. **All Core Operations**: Add, remove, list, refresh forwards via CLI
3. **Session Management**: Initialize, status, destroy tmux sessions
4. **Scriptable Interface**: JSON output and automation-friendly design
5. **Comprehensive Documentation**: Help text and usage examples
6. **Robust Testing**: >90% coverage with integration tests
7. **User-Friendly UX**: Clear error messages and intuitive commands

This foundation makes PortMUX immediately useful for power users and automation, setting the stage for the TUI interface in Phase 3.