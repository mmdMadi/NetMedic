"""
Tests for the Health Score computation.

Covers scoring logic, grade calculation, and edge cases.
"""

from __future__ import annotations

import pytest

from network.health import HealthCheck, HealthScore, compute_health
from network.internet import InternetStatus


class TestHealthCheck:
    """Tests for the HealthCheck dataclass."""

    def test_creation(self) -> None:
        """Should create a HealthCheck with all fields."""
        check = HealthCheck(label="Test", passed=True, detail="OK", weight=10)
        assert check.label == "Test"
        assert check.passed is True
        assert check.detail == "OK"
        assert check.weight == 10

    def test_frozen(self) -> None:
        """Should be immutable."""
        check = HealthCheck(label="Test", passed=True, detail="", weight=10)
        with pytest.raises(AttributeError):
            check.label = "Changed"  # type: ignore[misc]


class TestHealthScore:
    """Tests for the HealthScore dataclass."""

    def test_percentage(self) -> None:
        """Should compute percentage correctly."""
        score = HealthScore(score=80, max_score=100)
        assert score.percentage == 80.0

    def test_percentage_zero_max(self) -> None:
        """Should handle zero max_score."""
        score = HealthScore(score=0, max_score=0)
        assert score.percentage == 0.0

    def test_grade_excellent(self) -> None:
        """Should return Excellent for ≥90%."""
        score = HealthScore(score=95, max_score=100)
        assert score.grade == "Excellent"

    def test_grade_good(self) -> None:
        """Should return Good for ≥70%."""
        score = HealthScore(score=75, max_score=100)
        assert score.grade == "Good"

    def test_grade_fair(self) -> None:
        """Should return Fair for ≥50%."""
        score = HealthScore(score=55, max_score=100)
        assert score.grade == "Fair"

    def test_grade_poor(self) -> None:
        """Should return Poor for ≥30%."""
        score = HealthScore(score=35, max_score=100)
        assert score.grade == "Poor"

    def test_grade_critical(self) -> None:
        """Should return Critical for <30%."""
        score = HealthScore(score=10, max_score=100)
        assert score.grade == "Critical"

    def test_status_symbol_high(self) -> None:
        """Should return checkmark for ≥70%."""
        score = HealthScore(score=70, max_score=100)
        assert score.status_symbol == "✔"

    def test_status_symbol_medium(self) -> None:
        """Should return warning for ≥40%."""
        score = HealthScore(score=45, max_score=100)
        assert score.status_symbol == "⚠"

    def test_status_symbol_low(self) -> None:
        """Should return cross for <40%."""
        score = HealthScore(score=20, max_score=100)
        assert score.status_symbol == "✘"


class TestComputeHealth:
    """Tests for the compute_health function."""

    def test_all_passing(self) -> None:
        """Should return 100/100 when all checks pass."""
        score = compute_health(
            internet_status=InternetStatus.CONNECTED,
            gateway="192.168.1.1",
            adapter_connected=True,
            packet_loss_pct=0.0,
            mtu=1500,
        )
        assert score.score == 100
        assert score.grade == "Excellent"
        assert len(score.checks) == 6

    def test_all_failing(self) -> None:
        """Should return 0/100 when all checks fail."""
        score = compute_health(
            internet_status=InternetStatus.NO_INTERNET,
            gateway="—",
            adapter_connected=False,
            packet_loss_pct=50.0,
            mtu=0,
        )
        assert score.score == 0
        assert score.grade == "Critical"

    def test_partial_score(self) -> None:
        """Should compute partial score correctly."""
        score = compute_health(
            internet_status=InternetStatus.CONNECTED,  # 30 pts (Internet) + 20 pts (DNS)
            gateway="—",                                # 0 pts
            adapter_connected=True,                     # 15 pts
            packet_loss_pct=0.0,                        # 10 pts
            mtu=1500,                                   # 10 pts
        )
        # Internet=30, DNS=20 (passes because CONNECTED), Gateway=0, Adapter=15, Loss=10, MTU=10
        assert score.score == 85

    def test_packet_loss_warning(self) -> None:
        """Should fail packet loss check when >2%."""
        score = compute_health(
            internet_status=InternetStatus.CONNECTED,
            gateway="192.168.1.1",
            adapter_connected=True,
            packet_loss_pct=5.0,  # Above 2% threshold
            mtu=1500,
        )
        loss_check = next(c for c in score.checks if c.label == "Low Packet Loss")
        assert loss_check.passed is False

    def test_mtu_warning(self) -> None:
        """Should fail MTU check when <1280."""
        score = compute_health(
            internet_status=InternetStatus.CONNECTED,
            gateway="192.168.1.1",
            adapter_connected=True,
            packet_loss_pct=0.0,
            mtu=1200,  # Below 1280 minimum
        )
        mtu_check = next(c for c in score.checks if c.label == "MTU OK")
        assert mtu_check.passed is False

    def test_checks_have_weights(self) -> None:
        """All checks should have non-zero weights."""
        score = compute_health()
        for check in score.checks:
            assert check.weight > 0
