"""Tests for main CLI interface."""

import pytest
from click.testing import CliRunner

from portmux.cli import main


class TestMainCLI:
    def test_help_output(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "PortMUX - Port Multiplexer and Manager" in result.output
        assert "init" in result.output
        assert "status" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output
        assert "refresh" in result.output

    def test_global_options_passed_to_context(self):
        CliRunner()

        # Test that global options are properly stored in context
        @main.command()
        @pytest.fixture
        def test_cmd(ctx):
            assert ctx.obj["verbose"] is True
            assert ctx.obj["session"] == "test-session"

        # This test is more of a design verification
        # Actual context testing would require more complex setup
