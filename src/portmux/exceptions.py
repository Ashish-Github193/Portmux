"""Custom exceptions for PortMUX."""


class PortMuxError(Exception):
    """Base exception class for all PortMUX errors."""



class TmuxError(PortMuxError):
    """Raised when tmux operations fail."""



class SSHError(PortMuxError):
    """Raised when SSH operations fail."""



class ConfigError(PortMuxError):
    """Raised when configuration is invalid."""

