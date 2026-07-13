"""
Health score service.

Collects all network signals and computes a health score from 0 to 100.
This module orchestrates the individual diagnostic functions and feeds
their results into :func:`compute_health`.

The service is designed to be called from a background thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from network.health import HealthCheck, HealthScore, compute_health
from utils.logger import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class HealthReport:
    """Complete health assessment with all collected signals."""

    score: HealthScore
    internet_status: str = ""
    local_ip: str = ""
    public_ip: str = ""
    dns_server: str = ""
    default_gateway: str = ""
    connected_adapter: str = ""
    packet_loss_pct: float = 0.0
    mtu: int = 0
    ping_avg_ms: float = 0.0
    dns_avg_ms: float = 0.0
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            object.__setattr__(self, "warnings", [])


def gather_health_signals() -> dict:
    """Collect all network signals needed for health scoring.

    Returns a dict with keys matching :func:`compute_health` parameters
    plus additional diagnostic data.
    """
    signals: dict = {}

    # Internet status
    try:
        from network.internet import check_internet
        signals["internet_status"] = check_internet()
    except Exception:
        from network.internet import InternetStatus
        signals["internet_status"] = InternetStatus.CHECK_FAILED

    # Gateway
    try:
        from network.local_info import get_default_gateway
        signals["gateway"] = get_default_gateway()
    except Exception:
        signals["gateway"] = "—"

    # Connected adapter
    try:
        from network.local_info import get_connected_adapter
        name = get_connected_adapter()
        signals["adapter_connected"] = name != "—"
        signals["connected_adapter"] = name
    except Exception:
        signals["adapter_connected"] = False
        signals["connected_adapter"] = "—"

    # Packet loss
    try:
        from network.diagnostics_internet import ping_host
        result = ping_host("8.8.8.8", count=10, timeout=2)
        signals["packet_loss_pct"] = result.loss_pct
        signals["ping_avg_ms"] = result.avg_ms
    except Exception:
        signals["packet_loss_pct"] = 0.0
        signals["ping_avg_ms"] = 0.0

    # MTU
    try:
        from network.diagnostics_internet import detect_mtu
        mtu_result = detect_mtu("8.8.8.8")
        signals["mtu"] = mtu_result.mtu
    except Exception:
        signals["mtu"] = 0

    # Local IP
    try:
        from network.local_info import get_local_ip
        signals["local_ip"] = get_local_ip()
    except Exception:
        signals["local_ip"] = "—"

    # Public IP
    try:
        from network.public_info import get_public_ipv4
        signals["public_ip"] = get_public_ipv4()
    except Exception:
        signals["public_ip"] = "—"

    # DNS
    try:
        from network.local_info import get_dns_display
        signals["dns_server"] = get_dns_display()
    except Exception:
        signals["dns_server"] = "—"

    # DNS resolution speed
    try:
        from network.diagnostics_internet import test_dns_resolution
        dns_result = test_dns_resolution(servers=["1.1.1.1", "8.8.8.8"])
        signals["dns_avg_ms"] = dns_result.avg_ms
    except Exception:
        signals["dns_avg_ms"] = 0.0

    return signals


def compute_health_report() -> HealthReport:
    """Compute a complete health report.

    Gathers all signals, computes the health score, and generates
    warning explanations for any failed checks.
    """
    _log.info("Computing health report")
    signals = gather_health_signals()

    # Compute score
    score = compute_health(
        internet_status=signals.get("internet_status"),
        gateway=signals.get("gateway", "—"),
        adapter_connected=signals.get("adapter_connected", False),
        packet_loss_pct=signals.get("packet_loss_pct", 0.0),
        mtu=signals.get("mtu", 0),
    )

    # Generate warnings for failed checks
    warnings: list[str] = []
    for check in score.checks:
        if not check.passed and check.detail:
            warnings.append(check.detail)

    report = HealthReport(
        score=score,
        internet_status=signals.get("internet_status", "").value if hasattr(signals.get("internet_status", ""), "value") else str(signals.get("internet_status", "")),
        local_ip=signals.get("local_ip", "—"),
        public_ip=signals.get("public_ip", "—"),
        dns_server=signals.get("dns_server", "—"),
        default_gateway=signals.get("gateway", "—"),
        connected_adapter=signals.get("connected_adapter", "—"),
        packet_loss_pct=signals.get("packet_loss_pct", 0.0),
        mtu=signals.get("mtu", 0),
        ping_avg_ms=signals.get("ping_avg_ms", 0.0),
        dns_avg_ms=signals.get("dns_avg_ms", 0.0),
        warnings=warnings,
    )

    _log.info(
        "Health report: %d/100 (%s) — %d warnings",
        score.score, score.grade, len(warnings),
    )

    return report
