"""Configuration management functions for PortMUX."""

from __future__ import annotations

from pathlib import Path

import toml

from ..exceptions import ConfigError
from ..models import PortmuxConfig, ProfileConfig, StartupConfig

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
    "session_name": None,
    "default_identity": None,
    "commands": [],
}


def get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to the config file (~/.portmux/config.toml)
    """
    config_dir = Path.home() / ".portmux"
    return config_dir / "config.toml"


def load_config(config_path: str | None = None) -> PortmuxConfig:
    """Load configuration from TOML file.

    Args:
        config_path: Path to config file (optional, uses default if None)

    Returns:
        PortmuxConfig with loaded values

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

    # If config file doesn't exist, return defaults
    if not config_file.exists():
        return _build_config(config)

    try:
        # Load configuration from file
        with open(config_file) as f:
            file_config = toml.load(f)

        # Handle both new structured format and legacy flat format
        if (
            "general" in file_config
            or "startup" in file_config
            or "profiles" in file_config
        ):
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

        return _build_config(config)

    except toml.TomlDecodeError as e:
        raise ConfigError(f"Invalid TOML in config file '{config_file}': {e}")
    except OSError as e:
        raise ConfigError(f"Failed to read config file '{config_file}': {e}")


def _build_config(raw: dict) -> PortmuxConfig:
    """Build a PortmuxConfig from a validated raw dict structure."""
    general = raw.get("general", {})
    startup_raw = raw.get("startup", {})
    profiles_raw = raw.get("profiles", {})

    profiles = {}
    for name, profile_data in profiles_raw.items():
        profiles[name] = ProfileConfig(
            session_name=profile_data.get("session_name"),
            default_identity=profile_data.get("default_identity"),
            commands=list(profile_data.get("commands", [])),
        )

    return PortmuxConfig(
        session_name=general.get("session_name", "portmux"),
        default_identity=general.get("default_identity"),
        reconnect_delay=general.get("reconnect_delay", 1),
        max_retries=general.get("max_retries", 3),
        startup=StartupConfig(
            auto_execute=startup_raw.get("auto_execute", True),
            commands=list(startup_raw.get("commands", [])),
        ),
        profiles=profiles,
    )


def save_config(config: PortmuxConfig, config_path: str | None = None) -> None:
    """Save configuration to TOML file.

    Args:
        config: PortmuxConfig to save
        config_path: Path to config file (optional, uses default if None)

    Raises:
        ConfigError: If config can't be saved
    """
    if config_path is None:
        config_file = get_config_path()
    else:
        config_file = Path(config_path).expanduser()

    # Convert to structured dict for TOML serialization
    toml_dict = _config_to_toml_dict(config)

    # Validate before saving
    validate_config(toml_dict)

    try:
        # Create config directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Save config to file
        with open(config_file, "w") as f:
            toml.dump(toml_dict, f)

    except OSError as e:
        raise ConfigError(f"Failed to save config file '{config_file}': {e}")


def _config_to_toml_dict(config: PortmuxConfig) -> dict:
    """Convert PortmuxConfig to a structured dict for TOML serialization."""
    toml_dict: dict = {
        "general": {
            "session_name": config.session_name,
            "default_identity": config.default_identity,
            "reconnect_delay": config.reconnect_delay,
            "max_retries": config.max_retries,
        },
    }

    toml_dict["startup"] = {
        "auto_execute": config.startup.auto_execute,
        "commands": config.startup.commands,
    }

    if config.profiles:
        toml_dict["profiles"] = {}
        for name, profile in config.profiles.items():
            profile_dict: dict = {}
            if profile.session_name is not None:
                profile_dict["session_name"] = profile.session_name
            if profile.default_identity is not None:
                profile_dict["default_identity"] = profile.default_identity
            if profile.commands:
                profile_dict["commands"] = profile.commands
            toml_dict["profiles"][name] = profile_dict

    return toml_dict


def get_default_identity() -> str | None:
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


def validate_config(config: dict) -> bool:
    """Validate configuration structure and values.

    Operates on raw dicts (used during TOML loading and before saving).

    Args:
        config: Configuration dict to validate
            (either structured or backward-compatible format)

    Returns:
        True if valid

    Raises:
        ConfigError: If configuration is invalid
    """
    # Handle both structured format (during loading) and backward-compatible format
    if "general" in config:
        # Structured format during loading
        general_config = config["general"]
        startup_config = config.get("startup", {})
        profiles_config = config.get("profiles", {})
    else:
        # Backward-compatible format or legacy format
        general_config = {
            k: v for k, v in config.items() if k not in ["startup", "profiles"]
        }
        startup_config = config.get("startup", {})
        profiles_config = config.get("profiles", {})

    # Validate general configuration
    _validate_general_config(general_config)

    # Validate startup configuration
    _validate_startup_config(startup_config)

    # Validate profiles configuration
    _validate_profiles_config(profiles_config)

    return True


def _validate_general_config(config: dict) -> bool:
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
    if not isinstance(reconnect_delay, int | float) or reconnect_delay < 0:
        raise ConfigError("'reconnect_delay' must be a non-negative number")

    # Validate max_retries
    max_retries = config.get("max_retries", 3)
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ConfigError("'max_retries' must be a non-negative integer")

    return True


def _validate_startup_config(config: dict) -> bool:
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


def _validate_profiles_config(config: dict) -> bool:
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


def _validate_profile(profile_name: str, profile_config: dict) -> bool:
    """Validate a single profile configuration."""
    # Validate session_name if provided
    session_name = profile_config.get("session_name")
    if session_name is not None:
        if not isinstance(session_name, str) or not session_name.strip():
            raise ConfigError(
                f"Profile '{profile_name}' session_name must be a non-empty string"
            )

    # Validate default_identity if provided
    default_identity = profile_config.get("default_identity")
    if default_identity is not None:
        if not isinstance(default_identity, str):
            raise ConfigError(
                f"Profile '{profile_name}' default_identity must be a string"
            )

        identity_path = Path(default_identity).expanduser()
        if not identity_path.exists():
            raise ConfigError(
                f"Profile '{profile_name}' identity file not found:"
                f" '{default_identity}'"
            )

    # Validate commands
    commands = profile_config.get("commands", [])
    if not isinstance(commands, list):
        raise ConfigError(f"Profile '{profile_name}' commands must be a list")

    for i, command in enumerate(commands):
        if not isinstance(command, str):
            raise ConfigError(
                f"Profile '{profile_name}' commands[{i}] must be a string"
            )
        if not command.strip():
            raise ConfigError(f"Profile '{profile_name}' commands[{i}] cannot be empty")

    return True


def get_startup_config(config: PortmuxConfig) -> StartupConfig:
    """Get startup configuration from loaded config."""
    return config.startup


def get_profiles_config(config: PortmuxConfig) -> dict[str, ProfileConfig]:
    """Get profiles configuration from loaded config."""
    return config.profiles


def has_startup_commands(config: PortmuxConfig) -> bool:
    """Check if configuration has startup commands enabled."""
    return config.startup.auto_execute and len(config.startup.commands) > 0


def get_profile_names(config: PortmuxConfig) -> list[str]:
    """Get list of available profile names."""
    return list(config.profiles.keys())


def profile_exists(config: PortmuxConfig, profile_name: str) -> bool:
    """Check if a profile exists in configuration."""
    return profile_name in config.profiles


def create_default_config() -> None:
    """Create default configuration file if it doesn't exist.

    Raises:
        ConfigError: If config file can't be created
    """
    config_file = get_config_path()

    if config_file.exists():
        return  # Config already exists

    # Create config with defaults and auto-detected identity
    config = PortmuxConfig()

    # Try to find default identity
    default_identity = get_default_identity()
    if default_identity:
        config.default_identity = default_identity

    save_config(config)
