"""
PowerShell invocation wrapper.

Every PowerShell call in NetMedic goes through this module so that:

- encoding is handled once (UTF-8 on both directions),
- errors are normalized into a single :class:`PowerShellError`,
- timeouts are honored so a hung cmdlet cannot freeze the TUI,
- structured JSON is the preferred return type (so we never parse
  free-form text).

The module is Windows-aware but degrades gracefully on other platforms
so that the import graph and unit tests do not require Windows.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger

_log = get_logger(__name__)

#: Path to Windows PowerShell 5.1 (the only host guaranteed to ship with
#: the NetAdapter module). PowerShell 7+ would also work but is optional.
POWERSHELL_EXE: str = (
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    if sys.platform == "win32"
    else "powershell"
)

#: Default per-call timeout (seconds). Callers may override.
DEFAULT_TIMEOUT_SECONDS: int = 60

#: Header prepended to every script so cmdlets emit UTF-8 JSON, errors are
#: surfaced as non-terminating records, and progressive ResultSets work.
_COMMON_HEADER: str = (
    "$ErrorActionPreference = 'Stop';"
    "$OutputEncoding = [System.Text.Encoding]::UTF8;"
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
)


class PowerShellError(RuntimeError):
    """Raised when a PowerShell invocation fails for any reason.

    The :attr:`exit_code` attribute lets callers distinguish a missing
    cmdlet (non-zero exit) from a timeout (``None``).
    """

    def __init__(self, message: str, *, exit_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class PSResult:
    """Outcome of a single PowerShell execution.

    Attributes
    ----------
    stdout:
        Decoded standard output (UTF-8), with surrounding whitespace
        stripped. May be the empty string.
    stderr:
        Decoded standard error, useful for diagnostics.
    exit_code:
        Process exit status. ``None`` indicates the call timed out.
    """

    stdout: str
    stderr: str
    exit_code: Optional[int]

    @property
    def ok(self) -> bool:
        """``True`` when the process exited with status ``0``."""
        return self.exit_code == 0


class PowerShellRunner:
    """Encapsulates a PowerShell invocation policy.

    A single instance is cheap to construct and immutable in practice;
    tests can subclass it to inject fakes without touching call sites.
    """

    def __init__(
        self,
        *,
        executable: str = POWERSHELL_EXE,
        default_timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.executable = executable
        self.default_timeout = default_timeout

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run(
        self,
        script: str,
        *,
        timeout: Optional[int] = None,
    ) -> PSResult:
        """Run ``script`` and return a :class:`PSResult`.

        Raises :class:`PowerShellError` if the executable is missing,
        the call times out, or the process returns a non-zero exit
        status. Stderr is logged but not treated as failure on its own
        (many NetAdapter cmdlets write progress to stderr).
        """
        if sys.platform != "win32":
            raise PowerShellError(
                "PowerShell invocations are only supported on Windows."
            )
        effective_timeout = timeout if timeout is not None else self.default_timeout
        full_script = _COMMON_HEADER + script
        _log.debug("Running PowerShell (timeout=%ss).", effective_timeout)
        try:
            proc = subprocess.run(  # noqa: S603 -- trusted, internal script
                [
                    self.executable,
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    full_script,
                ],
                capture_output=True,
                timeout=effective_timeout,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise PowerShellError(
                f"PowerShell executable not found: {self.executable}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise PowerShellError(
                f"PowerShell timed out after {effective_timeout}s."
            ) from exc

        result = PSResult(
            stdout=(proc.stdout or "").strip(),
            stderr=(proc.stderr or "").strip(),
            exit_code=proc.returncode,
        )

        if not result.ok:
            _log.error(
                "PowerShell exit=%s stderr=%s",
                result.exit_code,
                result.stderr[:500],
            )
            raise PowerShellError(
                f"PowerShell failed (exit={result.exit_code}): "
                f"{result.stderr or 'no stderr'}",
                exit_code=result.exit_code,
            )
        if result.stderr:
            # Non-fatal: log at debug so we keep a breadcrumb.
            _log.debug("PowerShell stderr: %s", result.stderr[:500])
        return result

    def run_json(self, script: str, *, timeout: Optional[int] = None) -> list:
        """Run ``script`` and parse the output as a JSON array.

        The convention is that callers append ``| ConvertTo-Json -Depth N``
        (or ``-AsArray``) to their script. Empty output is treated as an
        empty list rather than an error so that "no adapters of this
        kind" yields ``[]`` instead of an exception.
        """
        import json

        result = self.run(script, timeout=timeout)
        if not result.stdout:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PowerShellError(
                f"PowerShell produced invalid JSON: {exc}"
            ) from exc
        # ConvertTo-Json returns a single object (not a list) for one row.
        if isinstance(data, list):
            return data
        return [data]


# --------------------------------------------------------------------- #
# Module-level convenience (stateless; safe to import anywhere).
# --------------------------------------------------------------------- #
_DEFAULT_RUNNER = PowerShellRunner()


def run_ps(script: str, *, timeout: Optional[int] = None) -> PSResult:
    """Run ``script`` via the shared default runner.

    Prefer constructing a dedicated :class:`PowerShellRunner` inside
    long-lived services so that an explicit timeout policy is visible at
    the construction site. This helper exists for one-off call sites
    (mostly tests and diagnostics).
    """
    return _DEFAULT_RUNNER.run(script, timeout=timeout)
