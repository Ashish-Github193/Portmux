"""Configuration management functions for PortMUX."""

from pathlib import Path
from typing import Dict, Optional

import toml

from .exceptions import ConfigError

DEFAULT_CONFIG = {
    "session_name": "portmux",
    "default_identity": None,
    "reconnect_delay": 1,
    "max_retries": 3,
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
        Dict with config values

    Raises:
        ConfigError: If config file is invalid
    """
    if config_path is None:
        config_file = get_config_path()
    else:
        config_file = Path(config_path).expanduser()

    # Start with default config
    config = DEFAULT_CONFIG.copy()

    # If config file doesn't exist, return defaults
    if not config_file.exists():
        return config

    try:
        # Load and merge with file config
        with open(config_file, "r") as f:
            file_config = toml.load(f)
            config.update(file_config)

        # Validate the loaded config
        validate_config(config)

        return config

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
        config: Configuration dict to validate

    Returns:
        True if valid

    Raises:
        ConfigError: If configuration is invalid
    """
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
