"""Profile management system for PortMUX."""

from typing import Dict, List, Optional

from .config import get_profiles_config, DEFAULT_PROFILE_CONFIG
from .exceptions import ConfigError


def load_profile(profile_name: str, config: Dict) -> Dict:
    """Load a specific profile configuration.

    Args:
        profile_name: Name of the profile to load
        config: Base configuration dict

    Returns:
        Merged profile configuration dict

    Raises:
        ConfigError: If profile doesn't exist or is invalid
    """
    profiles = get_profiles_config(config)
    
    if profile_name not in profiles:
        available_profiles = list_available_profiles(config)
        if available_profiles:
            raise ConfigError(
                f"Profile '{profile_name}' not found. Available profiles: {', '.join(available_profiles)}"
            )
        else:
            raise ConfigError(f"Profile '{profile_name}' not found. No profiles are configured.")

    profile_config = profiles[profile_name]
    
    # Start with base configuration
    merged_config = config.copy()
    
    # Apply profile-specific overrides
    if "session_name" in profile_config and profile_config["session_name"]:
        merged_config["session_name"] = profile_config["session_name"]
    
    if "default_identity" in profile_config and profile_config["default_identity"]:
        merged_config["default_identity"] = profile_config["default_identity"]
    
    # Add profile-specific startup commands
    profile_commands = profile_config.get("commands", [])
    if profile_commands:
        # Replace startup commands with profile commands
        merged_config["startup"] = {
            "auto_execute": True,
            "commands": profile_commands,
        }
    
    # Store the active profile name for reference
    merged_config["_active_profile"] = profile_name
    
    return merged_config


def list_available_profiles(config: Dict) -> List[str]:
    """Get list of available profile names.

    Args:
        config: Configuration dict

    Returns:
        List of profile names sorted alphabetically
    """
    profiles = get_profiles_config(config)
    return sorted(profiles.keys())


def profile_exists(config: Dict, profile_name: str) -> bool:
    """Check if a profile exists in configuration.

    Args:
        config: Configuration dict
        profile_name: Name of profile to check

    Returns:
        True if profile exists
    """
    profiles = get_profiles_config(config)
    return profile_name in profiles


def get_profile_info(config: Dict, profile_name: str) -> Dict:
    """Get detailed information about a profile.

    Args:
        config: Configuration dict
        profile_name: Name of the profile

    Returns:
        Dict with profile information

    Raises:
        ConfigError: If profile doesn't exist
    """
    profiles = get_profiles_config(config)
    
    if profile_name not in profiles:
        raise ConfigError(f"Profile '{profile_name}' not found")

    profile_config = profiles[profile_name]
    base_config = config.copy()
    
    # Build profile information
    info = {
        "name": profile_name,
        "session_name": profile_config.get("session_name") or base_config.get("session_name", "portmux"),
        "default_identity": profile_config.get("default_identity") or base_config.get("default_identity"),
        "commands": profile_config.get("commands", []),
        "command_count": len(profile_config.get("commands", [])),
        "inherits_session_name": "session_name" not in profile_config or not profile_config["session_name"],
        "inherits_identity": "default_identity" not in profile_config or not profile_config["default_identity"],
    }
    
    return info


def validate_profile(profile_name: str, profile_config: Dict) -> bool:
    """Validate a single profile configuration.

    Args:
        profile_name: Name of the profile
        profile_config: Profile configuration dict

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
            raise ConfigError(f"Profile '{profile_name}' session_name must be a non-empty string")

    # Validate default_identity if provided
    default_identity = profile_config.get("default_identity")
    if default_identity is not None:
        if not isinstance(default_identity, str):
            raise ConfigError(f"Profile '{profile_name}' default_identity must be a string")

        from pathlib import Path
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


def get_active_profile(config: Dict) -> Optional[str]:
    """Get the name of the currently active profile.

    Args:
        config: Configuration dict (potentially loaded with a profile)

    Returns:
        Profile name if active, None otherwise
    """
    return config.get("_active_profile")


def create_profile_template(
    profile_name: str,
    session_name: Optional[str] = None,
    default_identity: Optional[str] = None,
    commands: Optional[List[str]] = None
) -> Dict:
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


def profile_summary(config: Dict) -> Dict:
    """Get a summary of all profiles in configuration.

    Args:
        config: Configuration dict

    Returns:
        Dict with profile summary information
    """
    profiles = get_profiles_config(config)
    
    summary = {
        "total_profiles": len(profiles),
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


def merge_profile_with_base(base_config: Dict, profile_config: Dict) -> Dict:
    """Merge profile configuration with base configuration.

    Args:
        base_config: Base configuration dict
        profile_config: Profile-specific configuration dict

    Returns:
        Merged configuration dict
    """
    merged = base_config.copy()
    
    # Override base config with profile-specific values
    for key in ["session_name", "default_identity"]:
        if key in profile_config and profile_config[key] is not None:
            merged[key] = profile_config[key]
    
    # Handle commands specially - replace startup commands
    if "commands" in profile_config and profile_config["commands"]:
        merged["startup"] = merged.get("startup", {}).copy()
        merged["startup"]["commands"] = profile_config["commands"].copy()
        merged["startup"]["auto_execute"] = True
    
    return merged