"""Tests for add command."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from portmux.commands.add import add
from portmux.exceptions import SSHError


class TestAddCommand:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('portmux.commands.add.init_session_if_needed')
    @patch('portmux.commands.add.add_forward')
    @patch('portmux.commands.add.load_config')
    @patch('portmux.commands.add.get_default_identity')
    def test_add_local_forward_success(self, mock_get_identity, mock_load_config, 
                                      mock_add_forward, mock_init_session):
        mock_load_config.return_value = {'default_identity': None}
        mock_get_identity.return_value = '/home/user/.ssh/id_rsa'
        mock_add_forward.return_value = 'L:8080:localhost:80'
        
        result = self.runner.invoke(add, ['L', '8080:localhost:80', 'user@host'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code == 0
        assert 'Successfully created local forward' in result.output
        mock_add_forward.assert_called_once_with(
            direction='L',
            spec='8080:localhost:80',
            host='user@host',
            identity='/home/user/.ssh/id_rsa',
            session_name='portmux'
        )
    
    @patch('portmux.commands.add.init_session_if_needed')
    @patch('portmux.commands.add.add_forward')
    @patch('portmux.commands.add.load_config')
    def test_add_remote_forward_with_identity(self, mock_load_config, mock_add_forward, mock_init_session):
        mock_load_config.return_value = {'default_identity': None}
        mock_add_forward.return_value = 'R:9000:localhost:9000'
        
        result = self.runner.invoke(add, ['R', '9000:localhost:9000', 'user@host', '-i', '/path/to/key'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        if result.exit_code != 0:
            print(f"Error output: {result.output}")
        assert result.exit_code == 0
        assert 'Successfully created remote forward' in result.output
        mock_add_forward.assert_called_once_with(
            direction='R',
            spec='9000:localhost:9000',
            host='user@host',
            identity='/path/to/key',
            session_name='portmux'
        )
    
    def test_add_invalid_direction(self):
        result = self.runner.invoke(add, ['X', '8080:localhost:80', 'user@host'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code != 0
        assert 'Invalid direction' in result.output
    
    def test_add_invalid_port_spec(self):
        result = self.runner.invoke(add, ['L', 'invalid-spec', 'user@host'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code != 0
        assert 'Invalid port specification' in result.output
    
    @patch('portmux.commands.add.init_session_if_needed')
    @patch('portmux.commands.add.add_forward')
    @patch('portmux.commands.add.load_config')
    def test_add_forward_already_exists(self, mock_load_config, mock_add_forward, mock_init_session):
        mock_load_config.return_value = {'default_identity': None}
        mock_add_forward.side_effect = SSHError("Forward 'L:8080:localhost:80' already exists")
        
        result = self.runner.invoke(add, ['L', '8080:localhost:80', 'user@host'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code != 0
        assert 'already exists' in result.output
    
    @patch('portmux.commands.add.init_session_if_needed')
    @patch('portmux.commands.add.add_forward')
    @patch('portmux.commands.add.load_config')
    @patch('portmux.commands.add.get_default_identity')
    def test_add_verbose_output(self, mock_get_identity, mock_load_config, 
                               mock_add_forward, mock_init_session):
        mock_load_config.return_value = {'default_identity': '/default/key'}
        mock_get_identity.return_value = '/default/key'
        mock_add_forward.return_value = 'L:8080:localhost:80'
        
        result = self.runner.invoke(add, ['L', '8080:localhost:80', 'user@host'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': True})
        
        assert result.exit_code == 0
        assert 'Using default identity' in result.output
        assert 'Creating local forward' in result.output