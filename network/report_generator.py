"""
Diagnostic report generator.

Collects system information, network status, adapter details, and
diagnostic results into a structured report that can be rendered as
plain text, HTML, or copied to the clipboard.

All data collection is synchronous and designed to be called from a
background thread.

Report sections
---------------

1. System Information — date, hostname, Windows version, CPU, RAM
2. Network Status — internet status, local IP, public IP, DNS, gateway
3. Adapter Summary — total/physical/virtual/VPN/ghost counts
4. Diagnostics — ping, packet loss, MTU, DNS resolution
5. Speed Test — download/upload/ping/jitter
6. Warnings & Errors — collected during the session
"""

from __future__ import annotations

import html
import platform
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import psutil

from utils.logger import get_logger

_log = get_logger(__name__)


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class SystemInfo:
    """Static system information."""

    hostname: str
    username: str
    windows_version: str
    python_version: str
    cpu_count: int
    cpu_freq_mhz: float
    ram_total_gb: float
    ram_available_gb: float


@dataclass(frozen=True)
class NetworkStatus:
    """Current network status snapshot."""

    internet_status: str = "—"
    local_ip: str = "—"
    public_ip: str = "—"
    dns_server: str = "—"
    default_gateway: str = "—"
    connected_adapter: str = "—"


@dataclass(frozen=True)
class AdapterSummary:
    """Aggregate adapter counts."""

    total: int = 0
    physical: int = 0
    virtual: int = 0
    vpn: int = 0
    ghost: int = 0
    disabled: int = 0
    connected: int = 0


@dataclass(frozen=True)
class DiagnosticSnapshot:
    """Snapshot of diagnostic results for the report."""

    ping_host: str = "—"
    ping_avg_ms: float = 0.0
    ping_min_ms: float = 0.0
    ping_max_ms: float = 0.0
    ping_jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    mtu: int = 0
    dns_avg_ms: float = 0.0
    dns_servers_ok: int = 0
    dns_servers_tested: int = 0


@dataclass(frozen=True)
class SpeedSnapshot:
    """Snapshot of speed test results for the report."""

    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    jitter_ms: float = 0.0


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""

    generated_at: str = ""
    system: Optional[SystemInfo] = None
    network: Optional[NetworkStatus] = None
    adapters: Optional[AdapterSummary] = None
    diagnostics: Optional[DiagnosticSnapshot] = None
    speed_test: Optional[SpeedSnapshot] = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# --------------------------------------------------------------------- #
# Data collection
# --------------------------------------------------------------------- #

def collect_system_info() -> SystemInfo:
    """Gather static system information."""
    import getpass
    import sys

    hostname = socket.gethostname()
    username = getpass.getuser()
    windows_version = platform.platform()
    python_version = platform.python_version()

    cpu_count = psutil.cpu_count(logical=True) or 0
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = cpu_freq.current if cpu_freq else 0.0

    mem = psutil.virtual_memory()
    ram_total_gb = round(mem.total / (1024**3), 1)
    ram_available_gb = round(mem.available / (1024**3), 1)

    return SystemInfo(
        hostname=hostname,
        username=username,
        windows_version=windows_version,
        python_version=python_version,
        cpu_count=cpu_count,
        cpu_freq_mhz=cpu_freq_mhz,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
    )


def collect_network_status() -> NetworkStatus:
    """Gather current network status from existing modules."""
    try:
        from network.internet import check_internet
        internet_status = check_internet().value
    except Exception:
        internet_status = "Check Failed"

    try:
        from network.local_info import get_local_ip
        local_ip = get_local_ip()
    except Exception:
        local_ip = "—"

    try:
        from network.public_info import get_public_ipv4
        public_ip = get_public_ipv4()
    except Exception:
        public_ip = "—"

    try:
        from network.local_info import get_dns_display
        dns_server = get_dns_display()
    except Exception:
        dns_server = "—"

    try:
        from network.local_info import get_default_gateway
        default_gateway = get_default_gateway()
    except Exception:
        default_gateway = "—"

    try:
        from network.local_info import get_connected_adapter
        connected_adapter = get_connected_adapter()
    except Exception:
        connected_adapter = "—"

    return NetworkStatus(
        internet_status=internet_status,
        local_ip=local_ip,
        public_ip=public_ip,
        dns_server=dns_server,
        default_gateway=default_gateway,
        connected_adapter=connected_adapter,
    )


def collect_adapter_summary() -> AdapterSummary:
    """Gather adapter counts from the scanner."""
    try:
        from network.scanner import AdapterScanner, ScanStats
        from config import Config
        from utils.storage import Storage

        config = Config.from_storage(Storage())
        scanner = AdapterScanner(config)
        result = scanner.scan()
        stats = result.stats

        return AdapterSummary(
            total=stats.total,
            physical=stats.physical,
            virtual=stats.virtual,
            vpn=stats.vpn,
            ghost=stats.ghost,
            disabled=stats.disabled,
            connected=stats.connected,
        )
    except Exception as exc:
        _log.warning("Failed to collect adapter summary: %s", exc)
        return AdapterSummary()


def collect_diagnostics() -> DiagnosticSnapshot:
    """Run basic diagnostics and return a snapshot."""
    try:
        from network.diagnostics_internet import ping_host, measure_packet_loss, detect_mtu, test_dns_resolution

        ping_result = ping_host("8.8.8.8", count=4, timeout=2)
        loss_result = measure_packet_loss("8.8.8.8", count=10, timeout=2)
        mtu_result = detect_mtu("8.8.8.8")
        dns_result = test_dns_resolution(servers=["1.1.1.1", "8.8.8.8"])

        return DiagnosticSnapshot(
            ping_host="8.8.8.8",
            ping_avg_ms=ping_result.avg_ms,
            ping_min_ms=ping_result.min_ms,
            ping_max_ms=ping_result.max_ms,
            ping_jitter_ms=ping_result.jitter_ms,
            packet_loss_pct=loss_result.loss_pct,
            mtu=mtu_result.mtu,
            dns_avg_ms=dns_result.avg_ms,
            dns_servers_ok=dns_result.servers_ok,
            dns_servers_tested=dns_result.servers_tested,
        )
    except Exception as exc:
        _log.warning("Failed to collect diagnostics: %s", exc)
        return DiagnosticSnapshot()


# --------------------------------------------------------------------- #
# Report generation
# --------------------------------------------------------------------- #

def generate_report() -> DiagnosticReport:
    """Generate a complete diagnostic report.

    Collects all system, network, and diagnostic information into a
    single :class:`DiagnosticReport`.
    """
    _log.info("Generating diagnostic report")

    system = collect_system_info()
    network = collect_network_status()
    adapters = collect_adapter_summary()
    diagnostics = collect_diagnostics()

    warnings: list[str] = []
    errors: list[str] = []

    # Collect warnings
    if network.internet_status != "Connected":
        warnings.append(f"Internet status: {network.internet_status}")
    if diagnostics.packet_loss_pct > 2:
        warnings.append(f"Packet loss: {diagnostics.packet_loss_pct:.1f}%")
    if adapters.ghost > 0:
        warnings.append(f"{adapters.ghost} ghost adapter(s) detected")
    if adapters.disabled > 0:
        warnings.append(f"{adapters.disabled} disabled adapter(s)")
    if diagnostics.mtu > 0 and diagnostics.mtu < 1280:
        warnings.append(f"MTU below minimum: {diagnostics.mtu}")

    report = DiagnosticReport(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        system=system,
        network=network,
        adapters=adapters,
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
    )

    _log.info(
        "Report generated: %d warnings, %d errors",
        len(warnings), len(errors),
    )

    return report


# --------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------- #

def render_text(report: DiagnosticReport) -> str:
    """Render the report as plain text."""
    lines: list[str] = []
    sep = "=" * 60

    lines.append(sep)
    lines.append("  NetMedic Diagnostic Report")
    lines.append(sep)
    lines.append(f"  Generated: {report.generated_at}")
    lines.append("")

    # System
    if report.system:
        s = report.system
        lines.append("SYSTEM INFORMATION")
        lines.append("-" * 40)
        lines.append(f"  Hostname:         {s.hostname}")
        lines.append(f"  Username:         {s.username}")
        lines.append(f"  Windows:          {s.windows_version}")
        lines.append(f"  Python:           {s.python_version}")
        lines.append(f"  CPU:              {s.cpu_count} cores @ {s.cpu_freq_mhz:.0f} MHz")
        lines.append(f"  RAM:              {s.ram_total_gb} GB total, {s.ram_available_gb} GB available")
        lines.append("")

    # Network
    if report.network:
        n = report.network
        lines.append("NETWORK STATUS")
        lines.append("-" * 40)
        lines.append(f"  Internet:         {n.internet_status}")
        lines.append(f"  Local IP:         {n.local_ip}")
        lines.append(f"  Public IP:        {n.public_ip}")
        lines.append(f"  DNS Server:       {n.dns_server}")
        lines.append(f"  Default Gateway:  {n.default_gateway}")
        lines.append(f"  Connected:        {n.connected_adapter}")
        lines.append("")

    # Adapters
    if report.adapters:
        a = report.adapters
        lines.append("ADAPTER SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Total:            {a.total}")
        lines.append(f"  Physical:         {a.physical}")
        lines.append(f"  Virtual:          {a.virtual}")
        lines.append(f"  VPN:              {a.vpn}")
        lines.append(f"  Ghost:            {a.ghost}")
        lines.append(f"  Disabled:         {a.disabled}")
        lines.append(f"  Connected:        {a.connected}")
        lines.append("")

    # Diagnostics
    if report.diagnostics:
        d = report.diagnostics
        lines.append("DIAGNOSTICS")
        lines.append("-" * 40)
        lines.append(f"  Ping ({d.ping_host}):")
        lines.append(f"    Average:        {d.ping_avg_ms:.1f} ms")
        lines.append(f"    Min:            {d.ping_min_ms:.1f} ms")
        lines.append(f"    Max:            {d.ping_max_ms:.1f} ms")
        lines.append(f"    Jitter:         {d.ping_jitter_ms:.1f} ms")
        lines.append(f"  Packet Loss:      {d.packet_loss_pct:.1f}%")
        lines.append(f"  MTU:              {d.mtu}")
        lines.append(f"  DNS Resolution:   {d.dns_servers_ok}/{d.dns_servers_tested} servers OK (avg {d.dns_avg_ms:.1f} ms)")
        lines.append("")

    # Warnings
    if report.warnings:
        lines.append("WARNINGS")
        lines.append("-" * 40)
        for w in report.warnings:
            lines.append(f"  ⚠  {w}")
        lines.append("")

    # Errors
    if report.errors:
        lines.append("ERRORS")
        lines.append("-" * 40)
        for e in report.errors:
            lines.append(f"  ✘  {e}")
        lines.append("")

    lines.append(sep)
    lines.append("  End of report")
    lines.append(sep)

    return "\n".join(lines)


def render_html(report: DiagnosticReport) -> str:
    """Render the report as a styled HTML page."""
    html_parts: list[str] = []

    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NetMedic Diagnostic Report</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #e2e8f0; margin: 40px; }
  h1 { color: #3b82f6; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }
  h2 { color: #94a3b8; margin-top: 24px; }
  .meta { color: #64748b; margin-bottom: 24px; }
  table { border-collapse: collapse; width: 100%; max-width: 700px; }
  td { padding: 6px 12px; border-bottom: 1px solid #1e293b; }
  td:first-child { color: #94a3b8; width: 200px; }
  td:last-child { color: #e2e8f0; }
  .warning { color: #facc15; }
  .error { color: #f87171; }
  .ok { color: #4ade80; }
  .section { background: #1e293b; border-radius: 8px; padding: 16px; margin: 16px 0; }
</style>
</head>
<body>
<h1>NetMedic Diagnostic Report</h1>
""")

    html_parts.append(f'<p class="meta">Generated: {report.generated_at}</p>')

    # System
    if report.system:
        s = report.system
        html_parts.append('<div class="section"><h2>System Information</h2><table>')
        html_parts.append(f'<tr><td>Hostname</td><td>{html.escape(s.hostname)}</td></tr>')
        html_parts.append(f'<tr><td>Username</td><td>{html.escape(s.username)}</td></tr>')
        html_parts.append(f'<tr><td>Windows</td><td>{html.escape(s.windows_version)}</td></tr>')
        html_parts.append(f'<tr><td>Python</td><td>{html.escape(s.python_version)}</td></tr>')
        html_parts.append(f'<tr><td>CPU</td><td>{s.cpu_count} cores @ {s.cpu_freq_mhz:.0f} MHz</td></tr>')
        html_parts.append(f'<tr><td>RAM</td><td>{s.ram_total_gb} GB total, {s.ram_available_gb} GB available</td></tr>')
        html_parts.append('</table></div>')

    # Network
    if report.network:
        n = report.network
        status_class = "ok" if n.internet_status == "Connected" else "error"
        html_parts.append('<div class="section"><h2>Network Status</h2><table>')
        html_parts.append(f'<tr><td>Internet</td><td class="{status_class}">{html.escape(n.internet_status)}</td></tr>')
        html_parts.append(f'<tr><td>Local IP</td><td>{html.escape(n.local_ip)}</td></tr>')
        html_parts.append(f'<tr><td>Public IP</td><td>{html.escape(n.public_ip)}</td></tr>')
        html_parts.append(f'<tr><td>DNS Server</td><td>{html.escape(n.dns_server)}</td></tr>')
        html_parts.append(f'<tr><td>Default Gateway</td><td>{html.escape(n.default_gateway)}</td></tr>')
        html_parts.append(f'<tr><td>Connected</td><td>{html.escape(n.connected_adapter)}</td></tr>')
        html_parts.append('</table></div>')

    # Adapters
    if report.adapters:
        a = report.adapters
        html_parts.append('<div class="section"><h2>Adapter Summary</h2><table>')
        html_parts.append(f'<tr><td>Total</td><td>{a.total}</td></tr>')
        html_parts.append(f'<tr><td>Physical</td><td>{a.physical}</td></tr>')
        html_parts.append(f'<tr><td>Virtual</td><td>{a.virtual}</td></tr>')
        html_parts.append(f'<tr><td>VPN</td><td>{a.vpn}</td></tr>')
        html_parts.append(f'<tr><td>Ghost</td><td>{a.ghost}</td></tr>')
        html_parts.append(f'<tr><td>Disabled</td><td>{a.disabled}</td></tr>')
        html_parts.append(f'<tr><td>Connected</td><td>{a.connected}</td></tr>')
        html_parts.append('</table></div>')

    # Diagnostics
    if report.diagnostics:
        d = report.diagnostics
        html_parts.append('<div class="section"><h2>Diagnostics</h2><table>')
        html_parts.append(f'<tr><td>Ping ({d.ping_host})</td><td></td></tr>')
        html_parts.append(f'<tr><td>&nbsp;&nbsp;Average</td><td>{d.ping_avg_ms:.1f} ms</td></tr>')
        html_parts.append(f'<tr><td>&nbsp;&nbsp;Min</td><td>{d.ping_min_ms:.1f} ms</td></tr>')
        html_parts.append(f'<tr><td>&nbsp;&nbsp;Max</td><td>{d.ping_max_ms:.1f} ms</td></tr>')
        html_parts.append(f'<tr><td>&nbsp;&nbsp;Jitter</td><td>{d.ping_jitter_ms:.1f} ms</td></tr>')
        loss_class = "ok" if d.packet_loss_pct <= 2 else "warning" if d.packet_loss_pct <= 10 else "error"
        html_parts.append(f'<tr><td>Packet Loss</td><td class="{loss_class}">{d.packet_loss_pct:.1f}%</td></tr>')
        html_parts.append(f'<tr><td>MTU</td><td>{d.mtu}</td></tr>')
        html_parts.append(f'<tr><td>DNS Resolution</td><td>{d.dns_servers_ok}/{d.dns_servers_tested} OK (avg {d.dns_avg_ms:.1f} ms)</td></tr>')
        html_parts.append('</table></div>')

    # Warnings
    if report.warnings:
        html_parts.append('<div class="section"><h2>Warnings</h2><ul>')
        for w in report.warnings:
            html_parts.append(f'<li class="warning">⚠ {html.escape(w)}</li>')
        html_parts.append('</ul></div>')

    # Errors
    if report.errors:
        html_parts.append('<div class="section"><h2>Errors</h2><ul>')
        for e in report.errors:
            html_parts.append(f'<li class="error">✘ {html.escape(e)}</li>')
        html_parts.append('</ul></div>')

    html_parts.append("</body></html>")

    return "\n".join(html_parts)


def save_report(report: DiagnosticReport, path: str, fmt: str = "txt") -> bool:
    """Save the report to a file.

    Parameters
    ----------
    report:
        The report to save.
    path:
        File path to write to.
    fmt:
        Format: ``"txt"`` or ``"html"``.

    Returns
    -------
    bool
        ``True`` if the file was written successfully.
    """
    try:
        if fmt == "html":
            content = render_html(report)
        else:
            content = render_text(report)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        _log.info("Report saved to %s (%s)", path, fmt)
        return True

    except Exception as exc:
        _log.error("Failed to save report to %s: %s", path, exc)
        return False
