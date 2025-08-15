"""Tests for list command."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from portmux.commands.list import list as list_cmd


class TestListCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("portmux.commands.list.session_exists")
    @patch("portmux.commands.list.list_forwards")
    def test_list_active_forwards(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
                "status": "",
                "command": "ssh -N -L 8080:localhost:80 user@host",
            }
        ]

        result = self.runner.invoke(
            list_cmd, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "L:8080:localhost:80" in result.output
        assert "1 forward(s) active" in result.output

    @patch("portmux.commands.list.session_exists")
    @patch("portmux.commands.list.list_forwards")
    def test_list_no_forwards(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = []

        result = self.runner.invoke(
            list_cmd, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "No active forwards" in result.output
        assert "portmux add" in result.output

    @patch("portmux.commands.list.session_exists")
    def test_list_no_session(self, mock_session_exists):
        mock_session_exists.return_value = False

        result = self.runner.invoke(
            list_cmd, [], obj={"session": "portmux", "config": None, "verbose": False}
        )

        assert result.exit_code == 0
        assert "not active" in result.output
        assert "portmux init" in result.output

    @patch("portmux.commands.list.session_exists")
    @patch("portmux.commands.list.list_forwards")
    def test_list_json_output(self, mock_list_forwards, mock_session_exists):
        mock_session_exists.return_value = True
        mock_list_forwards.return_value = [
            {
                "name": "L:8080:localhost:80",
                "direction": "L",
                "spec": "8080:localhost:80",
                "status": "",
                "command": "ssh -N -L 8080:localhost:80 user@host",
            }
        ]

        result = self.runner.invoke(
            list_cmd,
            ["--json"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["session"] == "portmux"
        assert output_data["active"] is True
        assert len(output_data["forwards"]) == 1
        assert output_data["forwards"][0]["name"] == "L:8080:localhost:80"

    @patch("portmux.commands.list.session_exists")
    def test_list_json_no_session(self, mock_session_exists):
        mock_session_exists.return_value = False

        result = self.runner.invoke(
            list_cmd,
            ["--json"],
            obj={"session": "portmux", "config": None, "verbose": False},
        )

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["session"] == "portmux"
        assert output_data["active"] is False
        assert output_data["forwards"] == []
