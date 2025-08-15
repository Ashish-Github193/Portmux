"""PortMUX - Port Multiplexer and Manager for SSH forwards."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "Ashish Kumar Jha"
__description__ = "Command-line tool for managing SSH port forwards via tmux"


def hello() -> str:
    return "Hello from portmux!"
