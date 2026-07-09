"""
Network domain sub-package for NetMedic.

Contains everything that talks to Windows networking (PowerShell
wrappers, adapter model, categorization, scanning, diagnostics,
export, internet checks, public/local info, health scoring) -- all
deliberately independent of the Textual UI so it can be unit-tested
or reused as a plain library.
"""

from __future__ import annotations

from .powershell import PowerShellError, PowerShellRunner, run_ps
from .adapter import Adapter, AdapterCategory
from .categorizer import Categorizer
from .scanner import AdapterScanner, ScanResult
from .diagnostics import Diagnostics
from .export import ExportFormat, Exporter
from .internet import InternetStatus, InternetCheckResult, check_internet, check_internet_with_latency, is_connected
from .local_info import (
    LocalNetworkInfo,
    AdapterInfo,
    get_local_ip,
    get_connected_adapter,
    get_hostname,
    get_primary_dns,
    get_dns_provider,
    get_dns_display,
    get_default_gateway,
    gather as gather_local_info,
)
from .public_info import PublicNetworkInfo, get_public_ipv4, gather as gather_public_info
from .health import HealthScore, HealthCheck, compute_health

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
    "InternetStatus",
    "InternetCheckResult",
    "check_internet",
    "check_internet_with_latency",
    "is_connected",
    "LocalNetworkInfo",
    "AdapterInfo",
    "get_local_ip",
    "get_connected_adapter",
    "get_hostname",
    "get_primary_dns",
    "get_dns_provider",
    "get_dns_display",
    "get_default_gateway",
    "gather_local_info",
    "PublicNetworkInfo",
    "get_public_ipv4",
    "gather_public_info",
    "HealthScore",
    "HealthCheck",
    "compute_health",
]
