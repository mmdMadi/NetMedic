"""
Tests for the PowerShell runner.

Covers dataclasses, error handling, and the runner class.
"""

from __future__ import annotations

import pytest

from network.powershell import PSResult, PowerShellError, PowerShellRunner


class TestPSResult:
    """Tests for the PSResult dataclass."""

    def test_ok_true(self) -> None:
        """Should report ok when exit_code is 0."""
        result = PSResult(stdout="output", stderr="", exit_code=0)
        assert result.ok is True

    def test_ok_false(self) -> None:
        """Should report not ok when exit_code is non-zero."""
        result = PSResult(stdout="", stderr="error", exit_code=1)
        assert result.ok is False

    def test_ok_none(self) -> None:
        """Should report not ok when exit_code is None (timeout)."""
        result = PSResult(stdout="", stderr="", exit_code=None)
        assert result.ok is False


class TestPowerShellError:
    """Tests for the PowerShellError exception."""

    def test_message(self) -> None:
        """Should store the error message."""
        error = PowerShellError("Something failed")
        assert str(error) == "Something failed"

    def test_exit_code(self) -> None:
        """Should store the exit code."""
        error = PowerShellError("Failed", exit_code=1)
        assert error.exit_code == 1

    def test_no_exit_code(self) -> None:
        """Should handle missing exit code (timeout)."""
        error = PowerShellError("Timed out")
        assert error.exit_code is None


class TestPowerShellRunner:
    """Tests for the PowerShellRunner class."""

    def test_custom_timeout(self) -> None:
        """Should accept custom default timeout."""
        runner = PowerShellRunner(default_timeout=30)
        assert runner.default_timeout == 30

    def test_custom_executable(self) -> None:
        """Should accept custom executable path."""
        runner = PowerShellRunner(executable="/usr/bin/pwsh")
        assert runner.executable == "/usr/bin/pwsh"


@pytest.mark.network
class TestPowerShellRun:
    """Tests that make real PowerShell calls.

    Run with: pytest -m network
    """

    def test_run_simple(self) -> None:
        """Should execute a simple PowerShell command."""
        runner = PowerShellRunner(default_timeout=10)
        result = runner.run("Write-Output 'hello'")
        assert result.ok is True
        assert "hello" in result.stdout

    def test_run_error(self) -> None:
        """Should raise PowerShellError on non-zero exit."""
        runner = PowerShellRunner(default_timeout=10)
        with pytest.raises(PowerShellError):
            runner.run("throw 'test error'")

    def test_run_json(self) -> None:
        """Should parse JSON output."""
        runner = PowerShellRunner(default_timeout=10)
        result = runner.run_json('[1, 2, 3]')
        assert result == [1, 2, 3]
