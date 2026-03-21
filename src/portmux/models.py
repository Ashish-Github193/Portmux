"""Data models for PortMUX."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedSpec:
    """Parsed port specification."""

    local_port: int
    remote_host: str
    remote_port: int


@dataclass
class TunnelInfo:
    """Backend-neutral information about a running tunnel."""

    name: str
    status: str
    command: str


@dataclass
class ForwardInfo:
    """Information about an active SSH forward."""

    name: str
    direction: str  # "L" or "R"
    spec: str
    status: str
    command: str
    health: str | None = None  # TunnelHealth value or None if unchecked


@dataclass
class TunnelDiagnostics:
    """Raw diagnostic data from the backend for a single tunnel."""

    pane_pid: int | None
    pane_current_command: str | None
    pane_dead: bool
    pane_dead_status: str | None
    pane_content: list[str]


@dataclass
class StartupCommand:
    """Parsed startup command."""

    command: str
    args: list[str]
    original: str


@dataclass
class StartupConfig:
    """Startup command configuration."""

    auto_execute: bool = True
    commands: list[str] = field(default_factory=list)


@dataclass
class ProfileConfig:
    """Profile configuration."""

    session_name: str | None = None
    default_identity: str | None = None
    commands: list[str] = field(default_factory=list)


@dataclass
class MonitorConfig:
    """Monitor configuration."""

    enabled: bool = True
    check_interval: float = 30.0
    tcp_timeout: float = 2.0
    auto_reconnect: bool = True


@dataclass
class PortmuxConfig:
    """Main PortMUX configuration."""

    session_name: str = "portmux"
    default_identity: str | None = None
    reconnect_delay: float = 1
    max_retries: int = 3
    startup: StartupConfig = field(default_factory=StartupConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str | None = None
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
