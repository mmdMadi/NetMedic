"""
Network repair service.

Executes a sequence of Windows network repair commands and reports
per-step status.  Designed to be run from a background thread with
progress callbacks so the UI can show a live step-by-step view.

Repair steps
------------

1. ``ipconfig /flushdns``      — clear DNS cache
2. ``ipconfig /release``       — release current DHCP lease
3. ``ipconfig /renew``         — request new DHCP lease
4. ``netsh winsock reset``     — reset Winsock catalog
5. ``netsh int ip reset``      — reset TCP/IP stack
6. ``netsh int ipv4 reset``    — reset IPv4 interface
7. ``netsh int ipv6 reset``    — reset IPv6 interface

Each step is wrapped in error handling so a single failure does not
abort the entire repair sequence.  Steps that require elevation are
flagged so the UI can warn the user.

Cancellation is supported via :class:`threading.Event`.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from utils.logger import get_logger

_log = get_logger(__name__)


# --------------------------------------------------------------------- #
# Step definitions
# --------------------------------------------------------------------- #

class StepStatus(str, Enum):
    """Status of a single repair step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RepairStep:
    """A single repair command with metadata."""

    id: str
    label: str
    command: list[str]
    description: str
    requires_admin: bool = False
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    duration_s: float = 0.0


#: The ordered repair sequence.
REPAIR_STEPS: list[RepairStep] = [
    RepairStep(
        id="flushdns",
        label="Flush DNS Cache",
        command=["ipconfig", "/flushdns"],
        description="Clears cached DNS entries",
    ),
    RepairStep(
        id="release",
        label="Release DHCP Lease",
        command=["ipconfig", "/release"],
        description="Releases the current IP address",
    ),
    RepairStep(
        id="renew",
        label="Renew DHCP Lease",
        command=["ipconfig", "/renew"],
        description="Requests a new IP address from DHCP",
    ),
    RepairStep(
        id="winsock",
        label="Reset Winsock",
        command=["netsh", "winsock", "reset"],
        description="Resets the Winsock catalog to defaults",
        requires_admin=True,
    ),
    RepairStep(
        id="tcpip",
        label="Reset TCP/IP Stack",
        command=["netsh", "int", "ip", "reset"],
        description="Resets TCP/IP configuration to defaults",
        requires_admin=True,
    ),
    RepairStep(
        id="ipv4",
        label="Reset IPv4 Interface",
        command=["netsh", "int", "ipv4", "reset"],
        description="Resets all IPv4 interface settings",
        requires_admin=True,
    ),
    RepairStep(
        id="ipv6",
        label="Reset IPv6 Interface",
        command=["netsh", "int", "ipv6", "reset"],
        description="Resets all IPv6 interface settings",
        requires_admin=True,
    ),
]


# --------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------- #

#: Signature: ``(step_index, total_steps, step_status) -> None``
RepairProgressCallback = Callable[[int, int, RepairStep], None]


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass
class RepairResult:
    """Aggregate result of the full repair sequence."""

    steps: list[RepairStep] = field(default_factory=list)
    total_steps: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_duration_s: float = 0.0
    restart_required: bool = False
    cancelled: bool = False


# --------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------- #

def _run_command(
    cmd: list[str],
    timeout: int = 60,
) -> tuple[bool, str, str]:
    """Run a system command and return ``(success, stdout, stderr)``.

    Uses ``CREATE_NO_WINDOW`` on Windows to suppress the console pop-up.
    """
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        success = proc.returncode == 0
        return success, stdout, stderr

    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"
    except Exception as exc:
        return False, "", str(exc)


def run_repair(
    steps: Optional[list[RepairStep]] = None,
    cancel_event: Optional[threading.Event] = None,
    progress: Optional[RepairProgressCallback] = None,
) -> RepairResult:
    """Execute the full repair sequence.

    Parameters
    ----------
    steps:
        Steps to execute.  Defaults to :data:`REPAIR_STEPS`.
    cancel_event:
        If set, the repair aborts before the next step.
    progress:
        Callback invoked after each step completes.

    Returns
    -------
    RepairResult
        Per-step results and aggregate summary.
    """
    if steps is None:
        # Deep-copy default steps so mutations don't leak
        steps = [
            RepairStep(
                id=s.id,
                label=s.label,
                command=list(s.command),
                description=s.description,
                requires_admin=s.requires_admin,
            )
            for s in REPAIR_STEPS
        ]

    result = RepairResult(total_steps=len(steps))
    start_time = time.perf_counter()

    _log.info("Starting network repair (%d steps)", len(steps))

    for idx, step in enumerate(steps):
        # Check cancellation
        if cancel_event and cancel_event.is_set():
            step.status = StepStatus.SKIPPED
            step.output = "Cancelled by user"
            result.skipped_count += 1
            if progress:
                progress(idx, len(steps), step)
            continue

        # Mark as running
        step.status = StepStatus.RUNNING
        if progress:
            progress(idx, len(steps), step)

        _log.info("Repair step %d/%d: %s", idx + 1, len(steps), step.label)
        step_start = time.perf_counter()

        try:
            success, stdout, stderr = _run_command(step.command, timeout=60)
            step.duration_s = time.perf_counter() - step_start

            if success:
                step.status = StepStatus.SUCCESS
                step.output = stdout or "OK"
                result.success_count += 1
                _log.info("  ✔ %s (%.1fs)", step.label, step.duration_s)
            else:
                step.status = StepStatus.FAILED
                step.error = stderr or stdout or "Unknown error"
                result.failed_count += 1
                _log.warning(
                    "  ✘ %s: %s (%.1fs)",
                    step.label, step.error[:200], step.duration_s,
                )

        except Exception as exc:
            step.duration_s = time.perf_counter() - step_start
            step.status = StepStatus.FAILED
            step.error = str(exc)
            result.failed_count += 1
            _log.error("  ✘ %s exception: %s", step.label, exc)

        # Notify progress after each step
        if progress:
            progress(idx, len(steps), step)

    result.steps = steps
    result.total_duration_s = time.perf_counter() - start_time

    # Winsock / TCP/IP resets require a restart
    result.restart_required = any(
        s.status == StepStatus.SUCCESS
        and s.id in {"winsock", "tcpip", "ipv4", "ipv6"}
        for s in steps
    )

    if cancel_event and cancel_event.is_set():
        result.cancelled = True

    _log.info(
        "Repair complete: %d success, %d failed, %d skipped (%.1fs total)%s",
        result.success_count,
        result.failed_count,
        result.skipped_count,
        result.total_duration_s,
        " — restart required" if result.restart_required else "",
    )

    return result


def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
    except Exception:
        return False
