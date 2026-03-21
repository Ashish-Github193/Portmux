"""Backend abstraction for tunnel execution."""

from .protocol import TunnelBackend
from .tmux import TmuxBackend

__all__ = ["TunnelBackend", "TmuxBackend"]
