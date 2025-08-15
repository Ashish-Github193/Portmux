"""Tests for CLI utility functions."""

import pytest
from unittest.mock import patch, MagicMock
import click

from portmux.utils import (
    validate_direction, 
    validate_port_spec, 
    init_session_if_needed,
    create_forwards_table,
    confirm_destructive_action
)
from portmux.exceptions import TmuxError


class TestValidateDirection:
    def test_valid_directions(self):
        assert validate_direction('L') == 'L'
        assert validate_direction('R') == 'R'
        assert validate_direction('l') == 'L'
        assert validate_direction('r') == 'R'
        assert validate_direction('LOCAL') == 'L'
        assert validate_direction('REMOTE') == 'R'
        assert validate_direction('local') == 'L'
        assert validate_direction('remote') == 'R'
    
    def test_invalid_direction(self):
        with pytest.raises(click.BadParameter):
            validate_direction('X')
        
        with pytest.raises(click.BadParameter):
            validate_direction('INVALID')


class TestValidatePortSpec:
    def test_valid_port_specs(self):
        assert validate_port_spec('8080:localhost:80') == '8080:localhost:80'
        assert validate_port_spec('3000:192.168.1.10:5432') == '3000:192.168.1.10:5432'
    
    def test_invalid_port_specs(self):
        with pytest.raises(click.BadParameter):
            validate_port_spec('invalid')
        
        with pytest.raises(click.BadParameter):
            validate_port_spec('8080:80')  # Missing host
        
        with pytest.raises(click.BadParameter):
            validate_port_spec('999999:localhost:80')  # Invalid port number


class TestInitSessionIfNeeded:
    @patch('portmux.utils.session_exists')
    @patch('portmux.utils.create_session')
    def test_session_already_exists(self, mock_create, mock_exists):
        mock_exists.return_value = True
        
        result = init_session_if_needed('test-session')
        
        assert result is True
        mock_create.assert_not_called()
    
    @patch('portmux.utils.session_exists')
    @patch('portmux.utils.create_session')
    def test_session_created_successfully(self, mock_create, mock_exists):
        mock_exists.return_value = False
        mock_create.return_value = True
        
        result = init_session_if_needed('test-session')
        
        assert result is True
        mock_create.assert_called_once_with('test-session')


class TestCreateForwardsTable:
    def test_empty_forwards_list(self):
        table = create_forwards_table([])
        assert table.columns[0].header == "Name"
        assert table.columns[1].header == "Direction"
        assert table.columns[2].header == "Specification"
    
    def test_forwards_with_status(self):
        forwards = [
            {
                'name': 'L:8080:localhost:80',
                'direction': 'L',
                'spec': '8080:localhost:80',
                'status': ''
            }
        ]
        
        table = create_forwards_table(forwards, include_status=True)
        assert len(table.columns) == 4
        assert table.columns[3].header == "Status"
    
    def test_forwards_without_status(self):
        forwards = [
            {
                'name': 'L:8080:localhost:80',
                'direction': 'L',
                'spec': '8080:localhost:80',
                'status': ''
            }
        ]
        
        table = create_forwards_table(forwards, include_status=False)
        assert len(table.columns) == 3


class TestConfirmDestructiveAction:
    def test_force_skips_confirmation(self):
        result = confirm_destructive_action("Are you sure?", force=True)
        assert result is True
    
    @patch('click.confirm')
    def test_user_confirmation_called(self, mock_confirm):
        mock_confirm.return_value = True
        
        result = confirm_destructive_action("Are you sure?", force=False)
        
        assert result is True
        mock_confirm.assert_called_once_with("Are you sure?")