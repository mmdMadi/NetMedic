"""
Textual TUI sub-package for NetMedic.

Contains every widget, screen, and dialog. UI components depend on
:mod:`netmedic.network` for data and :mod:`netmedic.utils` for
infrastructure, never the other way around.
"""

from __future__ import annotations

from .dashboard import Dashboard
from .actions_bar import ActionsBar
from .adapter_table import AdapterTable, FilterKey
from .details import DetailsPanel
from .status import StatusBar, ProgressBar
from .diagnostics import DiagnosticsScreen
from .speed_test import SpeedTestScreen
from .dns_tools import DnsToolsScreen
from .repair import RepairScreen
from .dialogs import (
    ConfirmDialog,
    ConfirmResult,
    BulkRemoveConfirmDialog,
    ErrorDialog,
    ExportDialog,
    FilterDialog,
    RemoveConfirmDialog,
)

__all__ = [
    "Dashboard",
    "ActionsBar",
    "AdapterTable",
    "FilterKey",
    "DetailsPanel",
    "StatusBar",
    "ProgressBar",
    "DiagnosticsScreen",
    "SpeedTestScreen",
    "DnsToolsScreen",
    "RepairScreen",
    "ConfirmDialog",
    "ConfirmResult",
    "BulkRemoveConfirmDialog",
    "ErrorDialog",
    "ExportDialog",
    "FilterDialog",
    "RemoveConfirmDialog",
]
