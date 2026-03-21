"""Tunnel health states, results, and transition rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TunnelHealth(Enum):
    """Health state of an SSH tunnel."""

    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    DEAD = "dead"
    UNKNOWN = "unknown"


VALID_TRANSITIONS: dict[TunnelHealth, set[TunnelHealth]] = {
    TunnelHealth.STARTING: {
        TunnelHealth.HEALTHY,
        TunnelHealth.UNHEALTHY,
        TunnelHealth.DEAD,
    },
    TunnelHealth.HEALTHY: {
        TunnelHealth.UNHEALTHY,
        TunnelHealth.DEAD,
    },
    TunnelHealth.UNHEALTHY: {
        TunnelHealth.RESTARTING,
        TunnelHealth.DEAD,
        TunnelHealth.HEALTHY,
    },
    TunnelHealth.RESTARTING: {
        TunnelHealth.STARTING,
        TunnelHealth.DEAD,
    },
    TunnelHealth.DEAD: {
        TunnelHealth.STARTING,
    },
    TunnelHealth.UNKNOWN: {
        TunnelHealth.HEALTHY,
        TunnelHealth.UNHEALTHY,
        TunnelHealth.DEAD,
        TunnelHealth.STARTING,
    },
}


@dataclass
class HealthResult:
    """Result of a single health check for one tunnel."""

    name: str
    health: TunnelHealth
    detail: str
    process_alive: bool
    port_open: bool | None
    pane_error: str | None


def can_transition(current: TunnelHealth, target: TunnelHealth) -> bool:
    """Check if a state transition is valid."""
    return target in VALID_TRANSITIONS.get(current, set())
