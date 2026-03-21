"""Tests for health state machine."""

from portmux.health.state import HealthResult, TunnelHealth, can_transition


class TestTunnelHealth:
    def test_all_states_exist(self):
        assert TunnelHealth.STARTING.value == "starting"
        assert TunnelHealth.HEALTHY.value == "healthy"
        assert TunnelHealth.UNHEALTHY.value == "unhealthy"
        assert TunnelHealth.RESTARTING.value == "restarting"
        assert TunnelHealth.DEAD.value == "dead"
        assert TunnelHealth.UNKNOWN.value == "unknown"


class TestCanTransition:
    def test_starting_to_healthy(self):
        assert can_transition(TunnelHealth.STARTING, TunnelHealth.HEALTHY) is True

    def test_starting_to_unhealthy(self):
        assert can_transition(TunnelHealth.STARTING, TunnelHealth.UNHEALTHY) is True

    def test_starting_to_dead(self):
        assert can_transition(TunnelHealth.STARTING, TunnelHealth.DEAD) is True

    def test_starting_to_restarting_invalid(self):
        assert can_transition(TunnelHealth.STARTING, TunnelHealth.RESTARTING) is False

    def test_healthy_to_unhealthy(self):
        assert can_transition(TunnelHealth.HEALTHY, TunnelHealth.UNHEALTHY) is True

    def test_healthy_to_dead(self):
        assert can_transition(TunnelHealth.HEALTHY, TunnelHealth.DEAD) is True

    def test_healthy_to_starting_invalid(self):
        assert can_transition(TunnelHealth.HEALTHY, TunnelHealth.STARTING) is False

    def test_unhealthy_to_restarting(self):
        assert can_transition(TunnelHealth.UNHEALTHY, TunnelHealth.RESTARTING) is True

    def test_unhealthy_to_healthy(self):
        assert can_transition(TunnelHealth.UNHEALTHY, TunnelHealth.HEALTHY) is True

    def test_restarting_to_starting(self):
        assert can_transition(TunnelHealth.RESTARTING, TunnelHealth.STARTING) is True

    def test_restarting_to_dead(self):
        assert can_transition(TunnelHealth.RESTARTING, TunnelHealth.DEAD) is True

    def test_dead_to_starting(self):
        assert can_transition(TunnelHealth.DEAD, TunnelHealth.STARTING) is True

    def test_dead_to_healthy_invalid(self):
        assert can_transition(TunnelHealth.DEAD, TunnelHealth.HEALTHY) is False

    def test_unknown_to_any_valid(self):
        assert can_transition(TunnelHealth.UNKNOWN, TunnelHealth.HEALTHY) is True
        assert can_transition(TunnelHealth.UNKNOWN, TunnelHealth.UNHEALTHY) is True
        assert can_transition(TunnelHealth.UNKNOWN, TunnelHealth.DEAD) is True
        assert can_transition(TunnelHealth.UNKNOWN, TunnelHealth.STARTING) is True


class TestHealthResult:
    def test_create_health_result(self):
        result = HealthResult(
            name="L:8080:localhost:80",
            health=TunnelHealth.HEALTHY,
            detail="SSH alive, port accepting connections",
            process_alive=True,
            port_open=True,
            pane_error=None,
        )
        assert result.name == "L:8080:localhost:80"
        assert result.health == TunnelHealth.HEALTHY
        assert result.process_alive is True
        assert result.port_open is True
        assert result.pane_error is None

    def test_health_result_with_error(self):
        result = HealthResult(
            name="L:8080:localhost:80",
            health=TunnelHealth.UNHEALTHY,
            detail="Detected: Enter passphrase",
            process_alive=True,
            port_open=False,
            pane_error="Enter passphrase",
        )
        assert result.health == TunnelHealth.UNHEALTHY
        assert result.pane_error == "Enter passphrase"

    def test_health_result_dead(self):
        result = HealthResult(
            name="L:8080:localhost:80",
            health=TunnelHealth.DEAD,
            detail="Tunnel window not found",
            process_alive=False,
            port_open=None,
            pane_error=None,
        )
        assert result.health == TunnelHealth.DEAD
        assert result.port_open is None
