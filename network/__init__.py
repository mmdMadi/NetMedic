"""
Network domain sub-package for NetMedic.

Contains everything that talks to Windows networking (PowerShell
wrappers, adapter model, categorization, scanning, diagnostics,
export) -- all deliberately independent of the Textual UI so it can be
unit-tested or reused as a plain library.
"""

from __future__ import annotations

from .powershell import PowerShellError, PowerShellRunner, run_ps
from .adapter import Adapter, AdapterCategory
from .categorizer import Categorizer
from .scanner import AdapterScanner, ScanResult
from .diagnostics import Diagnostics
from .export import ExportFormat, Exporter

__all__ = [
    "PowerShellError",
    "PowerShellRunner",
    "run_ps",
    "Adapter",
    "AdapterCategory",
    "Categorizer",
    "AdapterScanner",
    "ScanResult",
    "Diagnostics",
    "ExportFormat",
    "Exporter",
]
