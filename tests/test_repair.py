"""
Tests for the network repair service.

Covers dataclasses, step definitions, and run_repair() with mocked commands.
"""

from __future__ import annotations

import threading
from unittest.mock import patch, MagicMock

import pytest

from network.repair import (
    REPAIR_STEPS,
    RepairResult,
    RepairStep,
    StepStatus,
    run_repair,
)


class TestStepStatus:
    def test_members(self) -> None:
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.SUCCESS == "success"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"


class TestRepairStep:
    def test_creation(self) -> None:
        step = RepairStep(
            id="test",
            label="Test Step",
            command=["echo", "hello"],
            description="A test step",
        )
        assert step.id == "test"
        assert step.requires_admin is False
        assert step.status == StepStatus.PENDING

    def test_admin_required(self) -> None:
        step = RepairStep(
            id="admin",
            label="Admin Step",
            command=["netsh"],
            description="Needs admin",
            requires_admin=True,
        )
        assert step.requires_admin is True


class TestRepairSteps:
    def test_step_count(self) -> None:
        assert len(REPAIR_STEPS) == 7

    def test_all_have_ids(self) -> None:
        ids = [s.id for s in REPAIR_STEPS]
        assert len(ids) == len(set(ids))  # no duplicates

    def test_admin_steps(self) -> None:
        admin_steps = [s for s in REPAIR_STEPS if s.requires_admin]
        assert len(admin_steps) == 4  # winsock, tcpip, ipv4, ipv6

    def test_first_step_flushdns(self) -> None:
        assert REPAIR_STEPS[0].id == "flushdns"
        assert REPAIR_STEPS[0].command == ["ipconfig", "/flushdns"]


class TestRepairResult:
    def test_defaults(self) -> None:
        r = RepairResult()
        assert r.total_steps == 0
        assert r.restart_required is False
        assert r.cancelled is False


class TestRunRepair:
    def test_all_steps_pass(self) -> None:
        with patch("network.repair._run_command", return_value=(True, "OK", "")):
            result = run_repair()
            assert result.success_count == 7
            assert result.failed_count == 0

    def test_one_step_fails(self) -> None:
        call_count = 0

        def mock_cmd(cmd, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                return (False, "", "Error")
            return (True, "OK", "")

        with patch("network.repair._run_command", side_effect=mock_cmd):
            result = run_repair()
            assert result.success_count == 6
            assert result.failed_count == 1

    def test_cancellation(self) -> None:
        cancel = threading.Event()
        cancel.set()
        result = run_repair(cancel_event=cancel)
        assert result.cancelled is True
        assert result.skipped_count == 7

    def test_restart_required_on_winsock(self) -> None:
        def mock_cmd(cmd, timeout=60):
            if "winsock" in cmd:
                return (True, "OK", "")
            return (True, "OK", "")

        with patch("network.repair._run_command", side_effect=mock_cmd):
            result = run_repair()
            assert result.restart_required is True

    def test_progress_callback(self) -> None:
        calls = []

        def on_progress(idx, total, step):
            calls.append((idx, total, step.id))

        with patch("network.repair._run_command", return_value=(True, "OK", "")):
            run_repair(progress=on_progress)
            # Callback fires twice per step: RUNNING + SUCCESS
            assert len(calls) == 14
            assert calls[0] == (0, 7, "flushdns")
            assert calls[2] == (1, 7, "release")
