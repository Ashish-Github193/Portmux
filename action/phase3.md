# Phase 3: Smart Configuration & Startup Automation System

## Plan Name
**"PortMUX Smart Config"** - Enhanced configuration management with automated startup commands and profile support

## Description
Phase 3 transforms PortMUX from a simple port forwarding tool into an intelligent configuration-driven automation system. This phase introduces startup commands that execute automatically during `portmux init` and can be reloaded during `portmux refresh`, along with profile support for managing different environments (development, staging, production, etc.). The enhanced configuration system maintains full backward compatibility while providing powerful new capabilities for automated setup and management of complex forwarding scenarios.

## Core Features & Implementation

### 1. Enhanced Configuration Structure
**File**: Enhanced `src/portmux/config.py`
- Extend existing configuration to support startup commands and profiles
- New configuration sections: `[startup]`, `[profiles.<name>]`
- Backward compatibility with existing config.toml files
- Enhanced validation with detailed error messages

**Sample Enhanced config.toml**:
```toml
[general]
session_name = "portmux"
default_identity = "~/.ssh/id_rsa"
reconnect_delay = 1
max_retries = 3

[startup]
auto_execute = true
commands = [
    "portmux add L 8080:localhost:80 user@prod-server",
    "portmux add R 9000:localhost:3000 user@dev-server -i ~/.ssh/dev_key"
]

[profiles.development]
session_name = "portmux-dev"
commands = [
    "portmux add L 3000:db.local:5432 user@dev-db",
    "portmux add L 8000:api.local:8000 user@dev-api"
]

[profiles.production]
session_name = "portmux-prod"
commands = [
    "portmux add L 5432:prod-db:5432 user@prod-server",
    "portmux add R 9090:localhost:9090 user@prod-server"
]
```

### 2. Startup Command System
**File**: New `src/portmux/startup.py`
- Execute startup commands during session initialization
- Command parsing and validation
- Error handling for failed startup commands
- Progress reporting for multiple commands
- Integration with profile system

**Key Functions**:
- `execute_startup_commands(config: Dict, session_name: str) -> bool`
- `parse_startup_command(command: str) -> Dict`
- `validate_startup_commands(commands: List[str]) -> bool`

### 3. Profile Management System  
**File**: New `src/portmux/profiles.py`
- Profile loading and switching
- Profile validation
- Profile-specific session management
- Profile inheritance from general config

**Key Functions**:
- `load_profile(profile_name: str, config: Dict) -> Dict`
- `list_available_profiles(config: Dict) -> List[str]`
- `validate_profile(profile: Dict) -> bool`
- `get_active_profile(session_name: str) -> Optional[str]`

### 4. Enhanced CLI Commands

#### Modified Existing Commands
**`portmux init`** (Enhanced):
- `--profile <name>`: Initialize with specific profile
- `--no-startup`: Skip startup command execution
- Automatic startup command execution based on config

**`portmux refresh`** (Enhanced):
- `--reload-startup`: Re-execute startup commands after refresh
- Profile-aware refreshing

#### New CLI Commands
**File**: New `src/portmux/commands/profile.py`
- `portmux profile list`: List available profiles
- `portmux profile show <name>`: Show profile configuration
- `portmux profile active`: Show currently active profile

### 5. Integration Points

#### Configuration Loading
- Extend `load_config()` to handle new sections
- Profile resolution and merging
- Startup command validation during config load

#### Session Management
- Profile-aware session creation
- Startup command execution pipeline
- Enhanced error reporting

#### Error Handling
- Startup command failure handling
- Profile validation errors
- Configuration migration assistance

## File Structure Changes

```
portmux/
├── action/
│   ├── phase1.md
│   ├── phase2.md
│   └── phase3.md           # NEW: This implementation guide
├── src/
│   └── portmux/
│       ├── config.py       # ENHANCED: Extended configuration
│       ├── startup.py      # NEW: Startup command execution
│       ├── profiles.py     # NEW: Profile management
│       ├── commands/
│       │   ├── init.py     # ENHANCED: Profile and startup support
│       │   ├── refresh.py  # ENHANCED: Startup reload support
│       │   └── profile.py  # NEW: Profile management commands
│       └── [existing files unchanged]
├── tests/
│   ├── test_startup.py     # NEW: Startup system tests
│   ├── test_profiles.py    # NEW: Profile system tests
│   ├── test_config.py      # ENHANCED: Extended config tests
│   ├── test_commands/
│   │   ├── test_init.py    # ENHANCED: Profile/startup tests
│   │   ├── test_refresh.py # ENHANCED: Startup reload tests
│   │   └── test_profile.py # NEW: Profile command tests
│   └── [existing test files unchanged]
```

## Testing Strategy

### 1. New Test Files

#### `tests/test_startup.py`
```python
class TestStartupSystem:
    def test_execute_startup_commands_success(self, mocker):
        # Test successful execution of startup commands
    
    def test_execute_startup_commands_partial_failure(self, mocker):
        # Test handling when some startup commands fail
        
    def test_parse_startup_command_valid(self):
        # Test parsing of valid startup commands
        
    def test_parse_startup_command_invalid(self):
        # Test handling of invalid startup command syntax
        
    def test_validate_startup_commands(self):
        # Test startup command validation
```

#### `tests/test_profiles.py`
```python
class TestProfileSystem:
    def test_load_profile_success(self, mocker):
        # Test loading valid profile
        
    def test_load_profile_not_found(self, mocker):
        # Test handling of non-existent profile
        
    def test_list_available_profiles(self, mocker):
        # Test profile listing functionality
        
    def test_validate_profile_valid(self):
        # Test valid profile validation
        
    def test_validate_profile_invalid(self):
        # Test invalid profile handling
```

#### `tests/test_commands/test_profile.py`
```python
class TestProfileCommand:
    def setup_method(self):
        self.runner = CliRunner()
        
    @patch("portmux.commands.profile.list_available_profiles")
    def test_profile_list_success(self, mock_list_profiles):
        # Test profile list command
        
    @patch("portmux.commands.profile.load_profile")
    def test_profile_show_success(self, mock_load_profile):
        # Test profile show command
        
    def test_profile_show_not_found(self, mocker):
        # Test handling of non-existent profile
```

### 2. Enhanced Existing Tests

#### Enhanced `tests/test_config.py`
- Add tests for startup command validation
- Add tests for profile configuration validation
- Add tests for backward compatibility
- Add tests for configuration migration

#### Enhanced `tests/test_commands/test_init.py`
- Add tests for `--profile` option
- Add tests for `--no-startup` option
- Add tests for startup command execution during init
- Add tests for profile-based session naming

#### Enhanced `tests/test_commands/test_refresh.py`
- Add tests for `--reload-startup` option
- Add tests for startup command re-execution
- Add tests for profile-aware refresh behavior

### 3. Testing Patterns (Following Existing Standards)
- Use `CliRunner` for command testing
- Mock external dependencies (`subprocess`, file operations)
- Use `pytest.raises` for exception testing
- Class-based test organization with `setup_method`
- Comprehensive coverage of success and failure scenarios

## Implementation Order

### Phase 3.1: Configuration Enhancement
1. **Extend config.py**
   - Add startup and profile section support
   - Enhance validation functions
   - Maintain backward compatibility

2. **Create startup.py**
   - Implement startup command execution system
   - Add command parsing and validation
   - Create progress reporting

### Phase 3.2: Profile System
3. **Create profiles.py**
   - Implement profile loading and management
   - Add profile validation
   - Create profile resolution logic

4. **Add profile command**
   - Implement profile CLI commands
   - Add profile listing and display
   - Create profile activation tracking

### Phase 3.3: Integration & Enhancement
5. **Enhance init command**
   - Add profile support
   - Integrate startup command execution
   - Add new command options

6. **Enhance refresh command**
   - Add startup reload capability
   - Integrate with profile system
   - Maintain existing functionality

### Phase 3.4: Testing & Documentation
7. **Comprehensive Testing**
   - Create all new test files
   - Enhance existing test files
   - Achieve >90% test coverage

8. **Create Documentation**
   - Write phase3.md implementation guide
   - Update README with new features
   - Create configuration examples

## Success Criteria

### Functional Requirements
- Startup commands execute automatically during `portmux init`
- Profile switching works seamlessly with isolated sessions
- `portmux refresh --reload-startup` re-executes startup commands
- All existing functionality remains unchanged
- Configuration is backward compatible

### Quality Requirements
- >90% test coverage for all new code
- All existing tests continue to pass
- New commands follow existing CLI patterns
- Error handling is comprehensive and user-friendly

### Performance Requirements
- Startup command execution completes within reasonable time
- Profile loading is fast and efficient
- No performance regression in existing functionality

## Backward Compatibility

### Configuration
- Existing config.toml files work without modification
- Missing sections use sensible defaults
- Migration path for enhanced features

### CLI Commands
- All existing commands work exactly as before
- New options are optional and don't break existing usage
- Error messages guide users to new features when appropriate

## Risk Mitigation

### Configuration Complexity
- Comprehensive validation with clear error messages
- Gradual feature adoption (optional by default)
- Detailed documentation and examples

### Command Execution Safety
- Startup command validation before execution
- Graceful handling of command failures
- Progress reporting for long operations

### Testing Coverage
- Unit tests for all new modules
- Integration tests for end-to-end workflows
- Edge case testing for error scenarios

## Example Usage

### Basic Startup Commands
```toml
[startup]
auto_execute = true
commands = [
    "portmux add L 8080:localhost:80 user@server",
    "portmux add R 9000:localhost:3000 user@server"
]
```

### Profile-Based Configuration
```bash
# Initialize with development profile
portmux init --profile development

# List available profiles
portmux profile list

# Show specific profile configuration
portmux profile show production

# Refresh with startup command reload
portmux refresh --reload-startup
```

### Advanced Profile Configuration
```toml
[profiles.development]
session_name = "portmux-dev"
default_identity = "~/.ssh/dev_key"
commands = [
    "portmux add L 3000:db.dev:5432 user@dev-server",
    "portmux add L 8000:api.dev:8000 user@dev-server"
]

[profiles.production]
session_name = "portmux-prod"
default_identity = "~/.ssh/prod_key"
commands = [
    "portmux add L 5432:prod-db:5432 user@prod-server",
    "portmux add R 9090:localhost:9090 user@prod-server"
]
```