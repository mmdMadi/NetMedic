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
from .diagnostics_internet import (
    PingResult,
    MultiPingResult,
    TracerouteHop,
    TracerouteResult,
    MtuResult,
    DnsResolution,
    DnsTestResult,
    GatewayResult,
    ping_host,
    ping_multi_host,
    measure_packet_loss,
    trace_route,
    detect_mtu,
    test_dns_resolution,
    detect_gateway,
    measure_latency,
)
from .speed_test import SpeedTestResult, run_speed_test, test_download, test_upload, test_ping_jitter
from .dns_tools import (
    DnsPreset,
    DNS_PRESETS,
    AdapterDns,
    DnsOperationResult,
    get_current_dns_servers,
    get_active_adapter_dns,
    set_dns_servers,
    reset_dns_automatic,
    flush_dns_cache,
    register_dns,
    reset_tcpip_stack,
)
from .repair import RepairStep, RepairResult, StepStatus, REPAIR_STEPS, run_repair, is_admin
from .adapter_manager import AdapterDetail, AdapterOperationResult, list_adapters, get_adapter_detail, enable_adapter, disable_adapter, restart_adapter
from .report_generator import DiagnosticReport, SystemInfo, NetworkStatus, AdapterSummary, DiagnosticSnapshot, SpeedSnapshot, generate_report, render_text, render_html, save_report
from .health_service import HealthReport, compute_health_report, gather_health_signals
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
    "PingResult",
    "MultiPingResult",
    "TracerouteHop",
    "TracerouteResult",
    "MtuResult",
    "DnsResolution",
    "DnsTestResult",
    "GatewayResult",
    "ping_host",
    "ping_multi_host",
    "measure_packet_loss",
    "trace_route",
    "detect_mtu",
    "test_dns_resolution",
    "detect_gateway",
    "measure_latency",
    "SpeedTestResult",
    "run_speed_test",
    "test_download",
    "test_upload",
    "test_ping_jitter",
    "DnsPreset",
    "DNS_PRESETS",
    "AdapterDns",
    "DnsOperationResult",
    "get_current_dns_servers",
    "get_active_adapter_dns",
    "set_dns_servers",
    "reset_dns_automatic",
    "flush_dns_cache",
    "register_dns",
    "reset_tcpip_stack",
    "RepairStep",
    "RepairResult",
    "StepStatus",
    "REPAIR_STEPS",
    "run_repair",
    "is_admin",
    "AdapterDetail",
    "AdapterOperationResult",
    "list_adapters",
    "get_adapter_detail",
    "enable_adapter",
    "disable_adapter",
    "restart_adapter",
    "DiagnosticReport",
    "SystemInfo",
    "NetworkStatus",
    "AdapterSummary",
    "DiagnosticSnapshot",
    "SpeedSnapshot",
    "generate_report",
    "render_text",
    "render_html",
    "save_report",
    "HealthReport",
    "compute_health_report",
    "gather_health_signals",
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
