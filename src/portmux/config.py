"""Configuration management functions for PortMUX."""

from pathlib import Path
from typing import Dict, List, Optional

import toml

from .exceptions import ConfigError

DEFAULT_CONFIG = {
    "session_name": "portmux",
    "default_identity": None,
    "reconnect_delay": 1,
    "max_retries": 3,
}

DEFAULT_STARTUP_CONFIG = {
    "auto_execute": True,
    "commands": [],
}

DEFAULT_PROFILE_CONFIG = {
    "session_name": None,  # Will inherit from general config if not specified
    "default_identity": None,  # Will inherit from general config if not specified
    "commands": [],
}


def get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to the config file (~/.portmux/config.toml)
    """
    config_dir = Path.home() / ".portmux"
    return config_dir / "config.toml"


def load_config(config_path: Optional[str] = None) -> Dict:
    """Load configuration from TOML file.

    Args:
        config_path: Path to config file (optional, uses default if None)

    Returns:
        Dict with config values including startup and profiles sections

    Raises:
        ConfigError: If config file is invalid
    """
    if config_path is None:
        config_file = get_config_path()
    else:
        config_file = Path(config_path).expanduser()

    # Start with default config structure
    config = {
        "general": DEFAULT_CONFIG.copy(),
        "startup": DEFAULT_STARTUP_CONFIG.copy(),
        "profiles": {},
    }

    # If config file doesn't exist, return defaults with backward compatibility
    if not config_file.exists():
        # For backward compatibility, flatten general config to root level
        backward_compatible_config = config["general"].copy()
        backward_compatible_config["startup"] = config["startup"]
        backward_compatible_config["profiles"] = config["profiles"]
        return backward_compatible_config

    try:
        # Load configuration from file
        with open(config_file, "r") as f:
            file_config = toml.load(f)

        # Handle both new structured format and legacy flat format
        if "general" in file_config or "startup" in file_config or "profiles" in file_config:
            # New structured format
            if "general" in file_config:
                config["general"].update(file_config["general"])
            if "startup" in file_config:
                config["startup"].update(file_config["startup"])
            if "profiles" in file_config:
                config["profiles"].update(file_config["profiles"])
                
            # Also check for any root-level config for partial migration
            for key in DEFAULT_CONFIG.keys():
                if key in file_config:
                    config["general"][key] = file_config[key]
        else:
            # Legacy flat format - migrate to new structure
            for key in DEFAULT_CONFIG.keys():
                if key in file_config:
                    config["general"][key] = file_config[key]

        # Validate the loaded config
        validate_config(config)

        # Return backward compatible format for existing code
        backward_compatible_config = config["general"].copy()
        backward_compatible_config["startup"] = config["startup"]
        backward_compatible_config["profiles"] = config["profiles"]
        
        return backward_compatible_config

    except toml.TomlDecodeError as e:
        raise ConfigError(f"Invalid TOML in config file '{config_file}': {e}")
    except (OSError, IOError) as e:
        raise ConfigError(f"Failed to read config file '{config_file}': {e}")


def save_config(config: Dict, config_path: Optional[str] = None) -> None:
    """Save configuration to TOML file.

    Args:
        config: Configuration dict to save
        config_path: Path to config file (optional, uses default if None)

    Raises:
        ConfigError: If config is invalid or can't be saved
    """
    if config_path is None:
        config_file = get_config_path()
    else:
        config_file = Path(config_path).expanduser()

    # Validate config before saving
    validate_config(config)

    try:
        # Create config directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Save config to file
        with open(config_file, "w") as f:
            toml.dump(config, f)

    except (OSError, IOError) as e:
        raise ConfigError(f"Failed to save config file '{config_file}': {e}")


def get_default_identity() -> Optional[str]:
    """Get path to default SSH identity file.

    Returns:
        Path to default SSH key or None if not found
    """
    ssh_dir = Path.home() / ".ssh"

    # Common identity file names in order of preference
    identity_files = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]

    for filename in identity_files:
        identity_path = ssh_dir / filename
        if identity_path.exists():
            return str(identity_path)

    return None


def validate_config(config: Dict) -> bool:
    """Validate configuration structure and values.

    Args:
        config: Configuration dict to validate (either structured or backward-compatible format)

    Returns:
        True if valid

    Raises:
        ConfigError: If configuration is invalid
    """
    # Handle both structured format (during loading) and backward-compatible format (final result)
    if "general" in config:
        # Structured format during loading
        general_config = config["general"]
        startup_config = config.get("startup", {})
        profiles_config = config.get("profiles", {})
    else:
        # Backward-compatible format or legacy format
        general_config = {k: v for k, v in config.items() 
                         if k not in ["startup", "profiles"]}
        startup_config = config.get("startup", {})
        profiles_config = config.get("profiles", {})

    # Validate general configuration
    _validate_general_config(general_config)
    
    # Validate startup configuration
    _validate_startup_config(startup_config)
    
    # Validate profiles configuration
    _validate_profiles_config(profiles_config)

    return True


def _validate_general_config(config: Dict) -> bool:
    """Validate general configuration section."""
    required_keys = ["session_name"]

    # Check required keys exist
    for key in required_keys:
        if key not in config:
            raise ConfigError(f"Missing required config key: '{key}'")

    # Validate session_name
    session_name = config.get("session_name")
    if not isinstance(session_name, str) or not session_name.strip():
        raise ConfigError("'session_name' must be a non-empty string")

    # Validate default_identity if provided
    default_identity = config.get("default_identity")
    if default_identity is not None:
        if not isinstance(default_identity, str):
            raise ConfigError("'default_identity' must be a string or None")

        identity_path = Path(default_identity).expanduser()
        if not identity_path.exists():
            raise ConfigError(f"Default identity file not found: '{default_identity}'")

    # Validate reconnect_delay
    reconnect_delay = config.get("reconnect_delay", 1)
    if not isinstance(reconnect_delay, (int, float)) or reconnect_delay < 0:
        raise ConfigError("'reconnect_delay' must be a non-negative number")

    # Validate max_retries
    max_retries = config.get("max_retries", 3)
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ConfigError("'max_retries' must be a non-negative integer")

    return True


def _validate_startup_config(config: Dict) -> bool:
    """Validate startup configuration section."""
    if not config:
        return True  # Empty startup config is valid

    # Validate auto_execute
    auto_execute = config.get("auto_execute", True)
    if not isinstance(auto_execute, bool):
        raise ConfigError("'startup.auto_execute' must be a boolean")

    # Validate commands
    commands = config.get("commands", [])
    if not isinstance(commands, list):
        raise ConfigError("'startup.commands' must be a list")

    # Validate each command
    for i, command in enumerate(commands):
        if not isinstance(command, str):
            raise ConfigError(f"'startup.commands[{i}]' must be a string")
        if not command.strip():
            raise ConfigError(f"'startup.commands[{i}]' cannot be empty")

    return True


def _validate_profiles_config(config: Dict) -> bool:
    """Validate profiles configuration section."""
    if not config:
        return True  # Empty profiles config is valid

    if not isinstance(config, dict):
        raise ConfigError("'profiles' must be a dictionary")

    # Validate each profile
    for profile_name, profile_config in config.items():
        if not isinstance(profile_name, str) or not profile_name.strip():
            raise ConfigError("Profile names must be non-empty strings")

        if not isinstance(profile_config, dict):
            raise ConfigError(f"Profile '{profile_name}' must be a dictionary")

        _validate_profile(profile_name, profile_config)

    return True


def _validate_profile(profile_name: str, profile_config: Dict) -> bool:
    """Validate a single profile configuration."""
    # Validate session_name if provided
    session_name = profile_config.get("session_name")
    if session_name is not None:
        if not isinstance(session_name, str) or not session_name.strip():
            raise ConfigError(f"Profile '{profile_name}' session_name must be a non-empty string")

    # Validate default_identity if provided
    default_identity = profile_config.get("default_identity")
    if default_identity is not None:
        if not isinstance(default_identity, str):
            raise ConfigError(f"Profile '{profile_name}' default_identity must be a string")

        identity_path = Path(default_identity).expanduser()
        if not identity_path.exists():
            raise ConfigError(f"Profile '{profile_name}' identity file not found: '{default_identity}'")

    # Validate commands
    commands = profile_config.get("commands", [])
    if not isinstance(commands, list):
        raise ConfigError(f"Profile '{profile_name}' commands must be a list")

    for i, command in enumerate(commands):
        if not isinstance(command, str):
            raise ConfigError(f"Profile '{profile_name}' commands[{i}] must be a string")
        if not command.strip():
            raise ConfigError(f"Profile '{profile_name}' commands[{i}] cannot be empty")

    return True


def get_startup_config(config: Dict) -> Dict:
    """Get startup configuration from loaded config.
    
    Args:
        config: Loaded configuration dict
        
    Returns:
        Startup configuration dict
    """
    return config.get("startup", DEFAULT_STARTUP_CONFIG.copy())


def get_profiles_config(config: Dict) -> Dict:
    """Get profiles configuration from loaded config.
    
    Args:
        config: Loaded configuration dict
        
    Returns:
        Profiles configuration dict
    """
    return config.get("profiles", {})


def has_startup_commands(config: Dict) -> bool:
    """Check if configuration has startup commands enabled.
    
    Args:
        config: Loaded configuration dict
        
    Returns:
        True if startup commands should be executed
    """
    startup_config = get_startup_config(config)
    return (startup_config.get("auto_execute", True) and 
            len(startup_config.get("commands", [])) > 0)


def get_profile_names(config: Dict) -> List[str]:
    """Get list of available profile names.
    
    Args:
        config: Loaded configuration dict
        
    Returns:
        List of profile names
    """
    profiles = get_profiles_config(config)
    return list(profiles.keys())


def profile_exists(config: Dict, profile_name: str) -> bool:
    """Check if a profile exists in configuration.
    
    Args:
        config: Loaded configuration dict
        profile_name: Name of profile to check
        
    Returns:
        True if profile exists
    """
    return profile_name in get_profiles_config(config)


def create_default_config() -> None:
    """Create default configuration file if it doesn't exist.

    Raises:
        ConfigError: If config file can't be created
    """
    config_file = get_config_path()

    if config_file.exists():
        return  # Config already exists

    # Create config with defaults and auto-detected identity
    config = DEFAULT_CONFIG.copy()

    # Try to find default identity
    default_identity = get_default_identity()
    if default_identity:
        config["default_identity"] = default_identity

    save_config(config)
