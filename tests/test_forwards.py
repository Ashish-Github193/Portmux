"""Tests for SSH forwarding functions."""

from unittest.mock import Mock

import pytest

from portmux.exceptions import SSHError, TmuxError
from portmux.ssh.forwards import (
    add_forward,
    list_forwards,
    parse_port_spec,
    refresh_forward,
    remove_forward,
)
from portmux.models import ForwardInfo, ParsedSpec, TunnelInfo
from portmux.backend import TmuxBackend


class TestParsePortSpec:
    def test_parse_valid_spec(self):
        result = parse_port_spec("8080:localhost:80")

        assert result == ParsedSpec(
            local_port=8080, remote_host="localhost", remote_port=80
        )

    def test_parse_with_ip_address(self):
        result = parse_port_spec("9000:192.168.1.10:443")

        assert result == ParsedSpec(
            local_port=9000, remote_host="192.168.1.10", remote_port=443
        )

    def test_parse_with_hostname(self):
        result = parse_port_spec("3000:example.com:22")

        assert result == ParsedSpec(
            local_port=3000, remote_host="example.com", remote_port=22
        )

    def test_parse_invalid_format_missing_colon(self):
        with pytest.raises(
            SSHError,
            match="Invalid port specification 'invalid'",
        ):
            parse_port_spec("invalid")

    def test_parse_invalid_format_too_many_colons(self):
        with pytest.raises(
            SSHError,
            match="Invalid port specification '8080:host:80:extra'",
        ):
            parse_port_spec("8080:host:80:extra")

    def test_parse_invalid_local_port_zero(self):
        with pytest.raises(
            SSHError, match="Invalid local port 0. Must be between 1 and 65535"
        ):
            parse_port_spec("0:localhost:80")

    def test_parse_invalid_local_port_too_high(self):
        with pytest.raises(
            SSHError, match="Invalid local port 65536. Must be between 1 and 65535"
        ):
            parse_port_spec("65536:localhost:80")

    def test_parse_invalid_remote_port_zero(self):
        with pytest.raises(
            SSHError, match="Invalid remote port 0. Must be between 1 and 65535"
        ):
            parse_port_spec("8080:localhost:0")

    def test_parse_invalid_remote_port_too_high(self):
        with pytest.raises(
            SSHError, match="Invalid remote port 65536. Must be between 1 and 65535"
        ):
            parse_port_spec("8080:localhost:65536")

    def test_parse_non_numeric_ports(self):
        with pytest.raises(
            SSHError,
            match="Invalid port specification 'abc:localhost:80'",
        ):
            parse_port_spec("abc:localhost:80")


class TestAddForward:
    def _make_backend(self, tunnel_exists=False, create_tunnel=True):
        backend = Mock(spec=TmuxBackend)
        backend.tunnel_exists.return_value = tunnel_exists
        backend.create_tunnel.return_value = create_tunnel
        return backend

    def test_add_local_forward_success(self):
        backend = self._make_backend()

        result = add_forward("L", "8080:localhost:80", "user@host", backend=backend)

        assert result == "L:8080:localhost:80"
        backend.tunnel_exists.assert_called_once_with("L:8080:localhost:80", "portmux")
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80", "ssh -N -L 8080:localhost:80 user@host", "portmux"
        )

    def test_add_remote_forward_success(self):
        backend = self._make_backend()

        result = add_forward("R", "9000:localhost:9000", "user@host", backend=backend)

        assert result == "R:9000:localhost:9000"
        backend.create_tunnel.assert_called_once_with(
            "R:9000:localhost:9000",
            "ssh -N -R 9000:localhost:9000 user@host",
            "portmux",
        )

    def test_add_forward_with_identity(self):
        backend = self._make_backend()

        result = add_forward(
            "L", "8080:localhost:80", "user@host", "/path/to/key", backend=backend
        )

        assert result == "L:8080:localhost:80"
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80",
            "ssh -N -L 8080:localhost:80 -i /path/to/key user@host",
            "portmux",
        )

    def test_add_forward_custom_session(self):
        backend = self._make_backend()

        result = add_forward(
            "L",
            "8080:localhost:80",
            "user@host",
            None,
            "custom-session",
            backend=backend,
        )

        assert result == "L:8080:localhost:80"
        backend.tunnel_exists.assert_called_once_with(
            "L:8080:localhost:80", "custom-session"
        )
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80",
            "ssh -N -L 8080:localhost:80 user@host",
            "custom-session",
        )

    def test_add_forward_invalid_direction(self):
        with pytest.raises(
            SSHError,
            match="Invalid direction 'X'. Must be 'L' \\(local\\) or 'R' \\(remote\\)",
        ):
            add_forward("X", "8080:localhost:80", "user@host")

    def test_add_forward_invalid_spec(self):
        with pytest.raises(
            SSHError,
            match="Invalid port specification 'invalid'",
        ):
            add_forward("L", "invalid", "user@host")

    def test_add_forward_already_exists(self):
        backend = self._make_backend(tunnel_exists=True)

        with pytest.raises(
            SSHError, match="Forward 'L:8080:localhost:80' already exists"
        ):
            add_forward("L", "8080:localhost:80", "user@host", backend=backend)

    def test_add_forward_create_window_fails(self):
        backend = self._make_backend()
        backend.create_tunnel.side_effect = TmuxError("Failed to create window")

        with pytest.raises(TmuxError, match="Failed to create window"):
            add_forward("L", "8080:localhost:80", "user@host", backend=backend)


class TestRemoveForward:
    def test_remove_forward_success(self):
        backend = Mock(spec=TmuxBackend)
        backend.kill_tunnel.return_value = True

        result = remove_forward("L:8080:localhost:80", backend=backend)

        assert result is True
        backend.kill_tunnel.assert_called_once_with("L:8080:localhost:80", "portmux")

    def test_remove_forward_custom_session(self):
        backend = Mock(spec=TmuxBackend)
        backend.kill_tunnel.return_value = True

        result = remove_forward(
            "L:8080:localhost:80", "custom-session", backend=backend
        )

        assert result is True
        backend.kill_tunnel.assert_called_once_with(
            "L:8080:localhost:80", "custom-session"
        )


class TestListForwards:
    def test_list_forwards_success(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = [
            TunnelInfo(name="L:8080:localhost:80", status="-", command="ssh"),
            TunnelInfo(name="R:9000:localhost:9000", status="*", command="ssh"),
            TunnelInfo(name="regular-window", status="-", command="bash"),
        ]

        result = list_forwards(backend=backend)

        expected = [
            ForwardInfo(
                name="L:8080:localhost:80",
                direction="L",
                spec="8080:localhost:80",
                status="-",
                command="ssh",
            ),
            ForwardInfo(
                name="R:9000:localhost:9000",
                direction="R",
                spec="9000:localhost:9000",
                status="*",
                command="ssh",
            ),
        ]
        assert result == expected
        backend.list_tunnels.assert_called_once_with("portmux")

    def test_list_forwards_empty(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = []

        result = list_forwards(backend=backend)

        assert result == []

    def test_list_forwards_custom_session(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = [
            TunnelInfo(name="L:3000:localhost:3000", status="-", command="ssh")
        ]

        result = list_forwards("custom-session", backend=backend)

        expected = [
            ForwardInfo(
                name="L:3000:localhost:3000",
                direction="L",
                spec="3000:localhost:3000",
                status="-",
                command="ssh",
            ),
        ]
        assert result == expected
        backend.list_tunnels.assert_called_once_with("custom-session")

    def test_list_forwards_filters_non_forward_windows(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = [
            TunnelInfo(name="bash-window", status="-", command="bash"),
            TunnelInfo(name="X:invalid", status="-", command="ssh"),
            TunnelInfo(name="no-colon", status="-", command="ssh"),
        ]

        result = list_forwards(backend=backend)

        assert result == []


class TestRefreshForward:
    def _make_backend_with_forward(
        self, command="ssh -N -L 8080:localhost:80 user@host"
    ):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = [
            TunnelInfo(name="L:8080:localhost:80", status="-", command=command)
        ]
        backend.kill_tunnel.return_value = True
        backend.tunnel_exists.return_value = False
        backend.create_tunnel.return_value = True
        return backend

    def test_refresh_forward_success(self):
        backend = self._make_backend_with_forward()

        result = refresh_forward("L:8080:localhost:80", backend=backend)

        assert result is True
        backend.kill_tunnel.assert_called_once_with("L:8080:localhost:80", "portmux")
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80", "ssh -N -L 8080:localhost:80 user@host", "portmux"
        )

    def test_refresh_forward_with_identity(self):
        backend = self._make_backend_with_forward(
            command="ssh -N -L 8080:localhost:80 -i /path/to/key user@host"
        )

        result = refresh_forward("L:8080:localhost:80", backend=backend)

        assert result is True
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80",
            "ssh -N -L 8080:localhost:80 -i /path/to/key user@host",
            "portmux",
        )

    def test_refresh_forward_not_found(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = []

        with pytest.raises(SSHError, match="Forward 'L:8080:localhost:80' not found"):
            refresh_forward("L:8080:localhost:80", backend=backend)

    def test_refresh_forward_invalid_command(self):
        backend = Mock(spec=TmuxBackend)
        backend.list_tunnels.return_value = [
            TunnelInfo(name="L:8080:localhost:80", status="-", command="bash")
        ]

        with pytest.raises(
            SSHError, match="Cannot parse SSH command for forward 'L:8080:localhost:80'"
        ):
            refresh_forward("L:8080:localhost:80", backend=backend)

    def test_refresh_forward_custom_session(self):
        backend = self._make_backend_with_forward()

        result = refresh_forward(
            "L:8080:localhost:80", "custom-session", backend=backend
        )

        assert result is True
        backend.list_tunnels.assert_called_once_with("custom-session")
        backend.kill_tunnel.assert_called_once_with(
            "L:8080:localhost:80", "custom-session"
        )
        backend.create_tunnel.assert_called_once_with(
            "L:8080:localhost:80",
            "ssh -N -L 8080:localhost:80 user@host",
            "custom-session",
        )

    def test_refresh_forward_add_fails(self):
        backend = self._make_backend_with_forward()
        backend.create_tunnel.side_effect = SSHError("Failed to add")

        with pytest.raises(SSHError, match="Failed to add"):
            refresh_forward("L:8080:localhost:80", backend=backend)
