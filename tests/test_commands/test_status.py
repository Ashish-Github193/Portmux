"""Tests for status command."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch

from portmux.commands.status import status


class TestStatusCommand:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('portmux.commands.status.session_exists')
    @patch('portmux.commands.status.list_forwards')
    def test_status_active_session_with_forwards(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                'name': 'L:8080:localhost:80',
                'direction': 'L',
                'spec': '8080:localhost:80',
                'status': '',
                'command': 'ssh -N -L 8080:localhost:80 user@host'
            },
            {
                'name': 'R:9000:localhost:9000',
                'direction': 'R',
                'spec': '9000:localhost:9000',
                'status': '',
                'command': 'ssh -N -R 9000:localhost:9000 user@host'
            }
        ]
        
        result = self.runner.invoke(status, [], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code == 0
        assert 'is active' in result.output
        assert '2 active forward(s)' in result.output
        assert 'Active Forwards:' in result.output
        assert 'L:8080:localhost:80' in result.output
        assert 'R:9000:localhost:9000' in result.output
    
    @patch('portmux.commands.status.session_exists')
    @patch('portmux.commands.status.list_forwards')
    def test_status_active_session_no_forwards(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = []
        
        result = self.runner.invoke(status, [], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code == 0
        assert 'is active' in result.output
        assert 'No active forwards' in result.output
        assert 'No forwards to display' in result.output
        assert 'portmux add' in result.output
    
    @patch('portmux.commands.status.session_exists')
    def test_status_no_session(self, mock_session_exists):
        mock_session_exists.return_value = False
        
        result = self.runner.invoke(status, [], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code == 0
        assert 'not active' in result.output
        assert 'portmux init' in result.output
    
    @patch('portmux.commands.status.session_exists')
    @patch('portmux.commands.status.list_forwards')
    def test_status_check_connections_placeholder(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                'name': 'L:8080:localhost:80',
                'direction': 'L',
                'spec': '8080:localhost:80',
                'status': '',
                'command': 'ssh -N -L 8080:localhost:80 user@host'
            }
        ]
        
        result = self.runner.invoke(status, ['--check-connections'], 
                                  obj={'session': 'portmux', 'config': None, 'verbose': False})
        
        assert result.exit_code == 0
        assert 'Connection checking not implemented yet' in result.output