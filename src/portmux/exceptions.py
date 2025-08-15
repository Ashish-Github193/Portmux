"""Custom exceptions for PortMUX."""


class PortMuxError(Exception):
    """Base exception class for all PortMUX errors."""
    pass


class TmuxError(PortMuxError):
    """Raised when tmux operations fail."""
    pass


class SSHError(PortMuxError):
    """Raised when SSH operations fail."""
    pass


class ConfigError(PortMuxError):
    """Raised when configuration is invalid."""
    pass