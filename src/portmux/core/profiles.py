"""Profile management system for PortMUX."""

from __future__ import annotations

from .config import DEFAULT_PROFILE_CONFIG
from ..exceptions import ConfigError
from ..models import PortmuxConfig, ProfileConfig, StartupConfig


def load_profile(profile_name: str, config: PortmuxConfig) -> PortmuxConfig:
    """Load a specific profile configuration.

    Args:
        profile_name: Name of the profile to load
        config: Base PortmuxConfig

    Returns:
        New PortmuxConfig with profile overrides applied

    Raises:
        ConfigError: If profile doesn't exist or is invalid
    """
    profiles = config.profiles

    if profile_name not in profiles:
        available_profiles = list_available_profiles(config)
        if available_profiles:
            raise ConfigError(
                f"Profile '{profile_name}' not found."
                f" Available profiles: {', '.join(available_profiles)}"
            )
        else:
            raise ConfigError(
                f"Profile '{profile_name}' not found. No profiles are configured."
            )

    profile_config = profiles[profile_name]

    # Start with base configuration
    merged = PortmuxConfig(
        session_name=config.session_name,
        default_identity=config.default_identity,
        reconnect_delay=config.reconnect_delay,
        max_retries=config.max_retries,
        startup=StartupConfig(
            auto_execute=config.startup.auto_execute,
            commands=list(config.startup.commands),
        ),
        profiles=config.profiles,
    )

    # Apply profile-specific overrides
    if profile_config.session_name:
        merged.session_name = profile_config.session_name

    if profile_config.default_identity:
        merged.default_identity = profile_config.default_identity

    # Add profile-specific startup commands
    if profile_config.commands:
        merged.startup = StartupConfig(
            auto_execute=True,
            commands=list(profile_config.commands),
        )

    # Store the active profile name for reference
    merged.active_profile = profile_name

    return merged


def list_available_profiles(config: PortmuxConfig) -> list[str]:
    """Get list of available profile names.

    Args:
        config: PortmuxConfig

    Returns:
        List of profile names sorted alphabetically
    """
    return sorted(config.profiles.keys())


def profile_exists(config: PortmuxConfig, profile_name: str) -> bool:
    """Check if a profile exists in configuration.

    Args:
        config: PortmuxConfig
        profile_name: Name of profile to check

    Returns:
        True if profile exists
    """
    return profile_name in config.profiles


def get_profile_info(config: PortmuxConfig, profile_name: str) -> dict:
    """Get detailed information about a profile.

    Args:
        config: PortmuxConfig
        profile_name: Name of the profile

    Returns:
        Dict with profile information

    Raises:
        ConfigError: If profile doesn't exist
    """
    if profile_name not in config.profiles:
        raise ConfigError(f"Profile '{profile_name}' not found")

    profile_config = config.profiles[profile_name]

    # Build profile information
    info = {
        "name": profile_name,
        "session_name": profile_config.session_name or config.session_name,
        "default_identity": profile_config.default_identity or config.default_identity,
        "commands": profile_config.commands,
        "command_count": len(profile_config.commands),
        "inherits_session_name": not profile_config.session_name,
        "inherits_identity": not profile_config.default_identity,
    }

    return info


def validate_profile(profile_name: str, profile_config: dict) -> bool:
    """Validate a single profile configuration.

    Args:
        profile_name: Name of the profile
        profile_config: Profile configuration dict (raw from TOML)

    Returns:
        True if valid

    Raises:
        ConfigError: If profile configuration is invalid
    """
    if not isinstance(profile_name, str) or not profile_name.strip():
        raise ConfigError("Profile names must be non-empty strings")

    if not isinstance(profile_config, dict):
        raise ConfigError(f"Profile '{profile_name}' must be a dictionary")

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

        from pathlib import Path

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


def get_active_profile(config: PortmuxConfig) -> str | None:
    """Get the name of the currently active profile.

    Args:
        config: PortmuxConfig (potentially loaded with a profile)

    Returns:
        Profile name if active, None otherwise
    """
    return config.active_profile


def create_profile_template(
    profile_name: str,
    session_name: str | None = None,
    default_identity: str | None = None,
    commands: list[str] | None = None,
) -> dict:
    """Create a profile configuration template.

    Args:
        profile_name: Name of the profile
        session_name: Custom session name (optional)
        default_identity: Custom identity file (optional)
        commands: List of commands (optional)

    Returns:
        Profile configuration dict
    """
    profile_config = DEFAULT_PROFILE_CONFIG.copy()

    if session_name:
        profile_config["session_name"] = session_name

    if default_identity:
        profile_config["default_identity"] = default_identity

    if commands:
        profile_config["commands"] = commands.copy()

    return profile_config


def profile_summary(config: PortmuxConfig) -> dict:
    """Get a summary of all profiles in configuration.

    Args:
        config: PortmuxConfig

    Returns:
        Dict with profile summary information
    """
    summary = {
        "total_profiles": len(config.profiles),
        "profile_names": list_available_profiles(config),
        "profiles": {},
    }

    for profile_name in summary["profile_names"]:
        try:
            info = get_profile_info(config, profile_name)
            summary["profiles"][profile_name] = {
                "session_name": info["session_name"],
                "command_count": info["command_count"],
                "has_custom_identity": not info["inherits_identity"],
                "has_custom_session": not info["inherits_session_name"],
            }
        except ConfigError:
            summary["profiles"][profile_name] = {
                "error": "Invalid profile configuration"
            }

    return summary


def merge_profile_with_base(
    base_config: PortmuxConfig, profile_config: ProfileConfig
) -> PortmuxConfig:
    """Merge profile configuration with base configuration.

    Args:
        base_config: Base PortmuxConfig
        profile_config: Profile-specific configuration

    Returns:
        New PortmuxConfig with profile overrides
    """
    merged = PortmuxConfig(
        session_name=base_config.session_name,
        default_identity=base_config.default_identity,
        reconnect_delay=base_config.reconnect_delay,
        max_retries=base_config.max_retries,
        startup=StartupConfig(
            auto_execute=base_config.startup.auto_execute,
            commands=list(base_config.startup.commands),
        ),
        profiles=base_config.profiles,
    )

    # Override base config with profile-specific values
    if profile_config.session_name is not None:
        merged.session_name = profile_config.session_name

    if profile_config.default_identity is not None:
        merged.default_identity = profile_config.default_identity

    # Handle commands specially - replace startup commands
    if profile_config.commands:
        merged.startup = StartupConfig(
            auto_execute=True,
            commands=list(profile_config.commands),
        )

    return merged
