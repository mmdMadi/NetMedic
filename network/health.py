"""
Internet health score calculator.

Produces a score from 0 to 100 based on multiple network signals.
Each signal contributes a weighted portion of the total score, and
individual check results are surfaced as human-readable status lines.

Scoring weights
---------------

Signal                  Weight   Pass points
─────────────────────   ──────   ──────────
Internet reachable        30       30
DNS working               20       20
Gateway present           15       15
Adapter connected         15       15
No packet loss            10       10
MTU reasonable            10       10
                            ──     ───
                            100     100

A "reasonable" MTU is >= 1280 (IPv6 minimum).
Packet loss is considered acceptable at <= 2%.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from network.internet import InternetStatus
from utils.logger import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class HealthCheck:
    """A single health check result."""

    label: str
    passed: bool
    detail: str
    weight: int


@dataclass(frozen=True)
class HealthScore:
    """Complete health assessment."""

    score: int
    max_score: int
    checks: list[HealthCheck] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        """Score as a percentage (0.0 – 100.0)."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100

    @property
    def grade(self) -> str:
        """Letter grade based on percentage."""
        pct = self.percentage
        if pct >= 90:
            return "Excellent"
        if pct >= 70:
            return "Good"
        if pct >= 50:
            return "Fair"
        if pct >= 30:
            return "Poor"
        return "Critical"

    @property
    def status_symbol(self) -> str:
        """Unicode symbol for the overall status."""
        if self.percentage >= 70:
            return "✔"
        if self.percentage >= 40:
            return "⚠"
        return "✘"


def compute_health(
    *,
    internet_status: InternetStatus = InternetStatus.CHECK_FAILED,
    gateway: str = "—",
    adapter_connected: bool = False,
    packet_loss_pct: float = 0.0,
    mtu: int = 0,
) -> HealthScore:
    """Compute the internet health score from the given signals.

    Parameters
    ----------
    internet_status:
        Result of the internet connectivity check.
    gateway:
        Default gateway address string. ``"—"`` or empty means none.
    adapter_connected:
        Whether the primary adapter reports an Up state.
    packet_loss_pct:
        Packet loss as a percentage (0.0 – 100.0).
    mtu:
        Maximum Transmission Unit of the primary adapter.

    Returns
    -------
    HealthScore
        Contains the numeric score, individual check results, and
        derived grade/status.
    """
    checks: list[HealthCheck] = []
    score = 0

    # 1. Internet reachable (30 pts)
    internet_ok = internet_status == InternetStatus.CONNECTED
    checks.append(
        HealthCheck(
            label="Internet Reachable",
            passed=internet_ok,
            detail="" if internet_ok else f"Status: {internet_status.value}",
            weight=30,
        )
    )
    if internet_ok:
        score += 30

    # 2. DNS working (20 pts) — implied by internet_ok, but also check
    #    for the NO_DNS case explicitly.
    dns_ok = internet_status in (InternetStatus.CONNECTED,)
    checks.append(
        HealthCheck(
            label="DNS Working",
            passed=dns_ok,
            detail="" if dns_ok else "DNS resolution failed",
            weight=20,
        )
    )
    if dns_ok:
        score += 20

    # 3. Gateway present (15 pts)
    gw_ok = bool(gateway) and gateway not in {"—", "", "0.0.0.0"}
    checks.append(
        HealthCheck(
            label="Gateway OK",
            passed=gw_ok,
            detail="" if gw_ok else "No default gateway found",
            weight=15,
        )
    )
    if gw_ok:
        score += 15

    # 4. Adapter connected (15 pts)
    checks.append(
        HealthCheck(
            label="Adapter Connected",
            passed=adapter_connected,
            detail="" if adapter_connected else "Primary adapter is down",
            weight=15,
        )
    )
    if adapter_connected:
        score += 15

    # 5. Packet loss (10 pts) — pass if <= 2%
    loss_ok = packet_loss_pct <= 2.0
    loss_detail = "" if loss_ok else f"Packet loss: {packet_loss_pct:.1f}%"
    checks.append(
        HealthCheck(
            label="Low Packet Loss",
            passed=loss_ok,
            detail=loss_detail,
            weight=10,
        )
    )
    if loss_ok:
        score += 10

    # 6. MTU reasonable (10 pts) — pass if >= 1280 (IPv6 minimum)
    mtu_ok = mtu >= 1280
    mtu_detail = "" if mtu_ok else f"MTU: {mtu} (below 1280 minimum)"
    checks.append(
        HealthCheck(
            label="MTU OK",
            passed=mtu_ok,
            detail=mtu_detail,
            weight=10,
        )
    )
    if mtu_ok:
        score += 10

    result = HealthScore(score=score, max_score=100, checks=checks)

    _log.info(
        "Health score: %d/100 (%s) — internet=%s dns=%s gw=%s adapter=%s loss=%.1f mtu=%d",
        score,
        result.grade,
        internet_ok,
        dns_ok,
        gw_ok,
        adapter_connected,
        packet_loss_pct,
        mtu,
    )

    return result
