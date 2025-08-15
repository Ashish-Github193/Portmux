"""Tests for SSH forwarding functions."""

from unittest.mock import MagicMock

import pytest

from portmux.forwards import parse_port_spec, add_forward, remove_forward, list_forwards, refresh_forward
from portmux.exceptions import SSHError, TmuxError


class TestParsePortSpec:
    def test_parse_valid_spec(self):
        result = parse_port_spec("8080:localhost:80")
        
        expected = {
            'local_port': '8080',
            'remote_host': 'localhost',
            'remote_port': '80'
        }
        assert result == expected

    def test_parse_with_ip_address(self):
        result = parse_port_spec("9000:192.168.1.10:443")
        
        expected = {
            'local_port': '9000',
            'remote_host': '192.168.1.10',
            'remote_port': '443'
        }
        assert result == expected

    def test_parse_with_hostname(self):
        result = parse_port_spec("3000:example.com:22")
        
        expected = {
            'local_port': '3000',
            'remote_host': 'example.com',
            'remote_port': '22'
        }
        assert result == expected

    def test_parse_invalid_format_missing_colon(self):
        with pytest.raises(SSHError, match="Invalid port specification 'invalid'. Expected format: 'local_port:remote_host:remote_port'"):
            parse_port_spec("invalid")

    def test_parse_invalid_format_too_many_colons(self):
        with pytest.raises(SSHError, match="Invalid port specification '8080:host:80:extra'. Expected format: 'local_port:remote_host:remote_port'"):
            parse_port_spec("8080:host:80:extra")

    def test_parse_invalid_local_port_zero(self):
        with pytest.raises(SSHError, match="Invalid local port 0. Must be between 1 and 65535"):
            parse_port_spec("0:localhost:80")

    def test_parse_invalid_local_port_too_high(self):
        with pytest.raises(SSHError, match="Invalid local port 65536. Must be between 1 and 65535"):
            parse_port_spec("65536:localhost:80")

    def test_parse_invalid_remote_port_zero(self):
        with pytest.raises(SSHError, match="Invalid remote port 0. Must be between 1 and 65535"):
            parse_port_spec("8080:localhost:0")

    def test_parse_invalid_remote_port_too_high(self):
        with pytest.raises(SSHError, match="Invalid remote port 65536. Must be between 1 and 65535"):
            parse_port_spec("8080:localhost:65536")

    def test_parse_non_numeric_ports(self):
        with pytest.raises(SSHError, match="Invalid port specification 'abc:localhost:80'. Expected format: 'local_port:remote_host:remote_port'"):
            parse_port_spec("abc:localhost:80")


class TestAddForward:
    def test_add_local_forward_success(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = False
        mock_create_window = mocker.patch("portmux.forwards.create_window")
        mock_create_window.return_value = True
        
        result = add_forward("L", "8080:localhost:80", "user@host")
        
        assert result == "L:8080:localhost:80"
        mock_window_exists.assert_called_once_with("L:8080:localhost:80", "portmux")
        mock_create_window.assert_called_once_with(
            "L:8080:localhost:80", 
            "ssh -N -L 8080:localhost:80 user@host",
            "portmux"
        )

    def test_add_remote_forward_success(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = False
        mock_create_window = mocker.patch("portmux.forwards.create_window")
        mock_create_window.return_value = True
        
        result = add_forward("R", "9000:localhost:9000", "user@host")
        
        assert result == "R:9000:localhost:9000"
        mock_create_window.assert_called_once_with(
            "R:9000:localhost:9000", 
            "ssh -N -R 9000:localhost:9000 user@host",
            "portmux"
        )

    def test_add_forward_with_identity(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = False
        mock_create_window = mocker.patch("portmux.forwards.create_window")
        mock_create_window.return_value = True
        
        result = add_forward("L", "8080:localhost:80", "user@host", "/path/to/key")
        
        assert result == "L:8080:localhost:80"
        mock_create_window.assert_called_once_with(
            "L:8080:localhost:80", 
            "ssh -N -L 8080:localhost:80 -i /path/to/key user@host",
            "portmux"
        )

    def test_add_forward_custom_session(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = False
        mock_create_window = mocker.patch("portmux.forwards.create_window")
        mock_create_window.return_value = True
        
        result = add_forward("L", "8080:localhost:80", "user@host", None, "custom-session")
        
        assert result == "L:8080:localhost:80"
        mock_window_exists.assert_called_once_with("L:8080:localhost:80", "custom-session")
        mock_create_window.assert_called_once_with(
            "L:8080:localhost:80", 
            "ssh -N -L 8080:localhost:80 user@host",
            "custom-session"
        )

    def test_add_forward_invalid_direction(self):
        with pytest.raises(SSHError, match="Invalid direction 'X'. Must be 'L' \\(local\\) or 'R' \\(remote\\)"):
            add_forward("X", "8080:localhost:80", "user@host")

    def test_add_forward_invalid_spec(self, mocker):
        with pytest.raises(SSHError, match="Invalid port specification 'invalid'. Expected format: 'local_port:remote_host:remote_port'"):
            add_forward("L", "invalid", "user@host")

    def test_add_forward_already_exists(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = True
        
        with pytest.raises(SSHError, match="Forward 'L:8080:localhost:80' already exists"):
            add_forward("L", "8080:localhost:80", "user@host")

    def test_add_forward_create_window_fails(self, mocker):
        mock_window_exists = mocker.patch("portmux.forwards.window_exists")
        mock_window_exists.return_value = False
        mock_create_window = mocker.patch("portmux.forwards.create_window")
        mock_create_window.side_effect = TmuxError("Failed to create window")
        
        with pytest.raises(TmuxError, match="Failed to create window"):
            add_forward("L", "8080:localhost:80", "user@host")


class TestRemoveForward:
    def test_remove_forward_success(self, mocker):
        mock_kill_window = mocker.patch("portmux.forwards.kill_window")
        mock_kill_window.return_value = True
        
        result = remove_forward("L:8080:localhost:80")
        
        assert result is True
        mock_kill_window.assert_called_once_with("L:8080:localhost:80", "portmux")

    def test_remove_forward_custom_session(self, mocker):
        mock_kill_window = mocker.patch("portmux.forwards.kill_window")
        mock_kill_window.return_value = True
        
        result = remove_forward("L:8080:localhost:80", "custom-session")
        
        assert result is True
        mock_kill_window.assert_called_once_with("L:8080:localhost:80", "custom-session")


class TestListForwards:
    def test_list_forwards_success(self, mocker):
        mock_list_windows = mocker.patch("portmux.forwards.list_windows")
        mock_list_windows.return_value = [
            {"name": "L:8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "status": "*", "command": "ssh"},
            {"name": "regular-window", "status": "-", "command": "bash"}  # Should be ignored
        ]
        
        result = list_forwards()
        
        expected = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", "command": "ssh"},
            {"name": "R:9000:localhost:9000", "direction": "R", "spec": "9000:localhost:9000", "status": "*", "command": "ssh"}
        ]
        assert result == expected
        mock_list_windows.assert_called_once_with("portmux")

    def test_list_forwards_empty(self, mocker):
        mock_list_windows = mocker.patch("portmux.forwards.list_windows")
        mock_list_windows.return_value = []
        
        result = list_forwards()
        
        assert result == []

    def test_list_forwards_custom_session(self, mocker):
        mock_list_windows = mocker.patch("portmux.forwards.list_windows")
        mock_list_windows.return_value = [
            {"name": "L:3000:localhost:3000", "status": "-", "command": "ssh"}
        ]
        
        result = list_forwards("custom-session")
        
        expected = [
            {"name": "L:3000:localhost:3000", "direction": "L", "spec": "3000:localhost:3000", "status": "-", "command": "ssh"}
        ]
        assert result == expected
        mock_list_windows.assert_called_once_with("custom-session")

    def test_list_forwards_filters_non_forward_windows(self, mocker):
        mock_list_windows = mocker.patch("portmux.forwards.list_windows")
        mock_list_windows.return_value = [
            {"name": "bash-window", "status": "-", "command": "bash"},
            {"name": "X:invalid", "status": "-", "command": "ssh"},  # Invalid direction
            {"name": "no-colon", "status": "-", "command": "ssh"}    # No colon
        ]
        
        result = list_forwards()
        
        assert result == []


class TestRefreshForward:
    def test_refresh_forward_success(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", "command": "ssh -N -L 8080:localhost:80 user@host"}
        ]
        mock_remove_forward = mocker.patch("portmux.forwards.remove_forward")
        mock_remove_forward.return_value = True
        mock_add_forward = mocker.patch("portmux.forwards.add_forward")
        mock_add_forward.return_value = "L:8080:localhost:80"
        
        result = refresh_forward("L:8080:localhost:80")
        
        assert result is True
        mock_list_forwards.assert_called_once_with("portmux")
        mock_remove_forward.assert_called_once_with("L:8080:localhost:80", "portmux")
        mock_add_forward.assert_called_once_with("L", "8080:localhost:80", "user@host", None, "portmux")

    def test_refresh_forward_with_identity(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", 
             "command": "ssh -N -L 8080:localhost:80 -i /path/to/key user@host"}
        ]
        mock_remove_forward = mocker.patch("portmux.forwards.remove_forward")
        mock_remove_forward.return_value = True
        mock_add_forward = mocker.patch("portmux.forwards.add_forward")
        mock_add_forward.return_value = "L:8080:localhost:80"
        
        result = refresh_forward("L:8080:localhost:80")
        
        assert result is True
        mock_add_forward.assert_called_once_with("L", "8080:localhost:80", "user@host", "/path/to/key", "portmux")

    def test_refresh_forward_not_found(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = []
        
        with pytest.raises(SSHError, match="Forward 'L:8080:localhost:80' not found"):
            refresh_forward("L:8080:localhost:80")

    def test_refresh_forward_invalid_command(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", "command": "bash"}
        ]
        
        with pytest.raises(SSHError, match="Cannot parse SSH command for forward 'L:8080:localhost:80'"):
            refresh_forward("L:8080:localhost:80")

    def test_refresh_forward_custom_session(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", 
             "command": "ssh -N -L 8080:localhost:80 user@host"}
        ]
        mock_remove_forward = mocker.patch("portmux.forwards.remove_forward")
        mock_remove_forward.return_value = True
        mock_add_forward = mocker.patch("portmux.forwards.add_forward")
        mock_add_forward.return_value = "L:8080:localhost:80"
        
        result = refresh_forward("L:8080:localhost:80", "custom-session")
        
        assert result is True
        mock_list_forwards.assert_called_once_with("custom-session")
        mock_remove_forward.assert_called_once_with("L:8080:localhost:80", "custom-session")
        mock_add_forward.assert_called_once_with("L", "8080:localhost:80", "user@host", None, "custom-session")

    def test_refresh_forward_add_fails(self, mocker):
        mock_list_forwards = mocker.patch("portmux.forwards.list_forwards")
        mock_list_forwards.return_value = [
            {"name": "L:8080:localhost:80", "direction": "L", "spec": "8080:localhost:80", "status": "-", 
             "command": "ssh -N -L 8080:localhost:80 user@host"}
        ]
        mock_remove_forward = mocker.patch("portmux.forwards.remove_forward")
        mock_remove_forward.return_value = True
        mock_add_forward = mocker.patch("portmux.forwards.add_forward")
        mock_add_forward.side_effect = SSHError("Failed to add")
        
        with pytest.raises(SSHError, match="Failed to add"):
            refresh_forward("L:8080:localhost:80")