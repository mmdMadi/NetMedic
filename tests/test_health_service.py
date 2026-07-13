"""
Tests for the health score service.

Covers the HealthReport dataclass.
"""

from __future__ import annotations

import pytest

from network.health import HealthScore
from network.health_service import HealthReport


class TestHealthReport:
    def test_creation(self) -> None:
        score = HealthScore(score=85, max_score=100)
        report = HealthReport(score=score)
        assert report.score.score == 85
        assert report.warnings == []

    def test_with_warnings(self) -> None:
        score = HealthScore(score=50, max_score=100)
        report = HealthReport(score=score, warnings=["Low score"])
        assert report.warnings == ["Low score"]

    def test_defaults(self) -> None:
        score = HealthScore(score=0, max_score=100)
        report = HealthReport(score=score)
        assert report.internet_status == ""
        assert report.local_ip == ""
        assert report.packet_loss_pct == 0.0
        assert report.mtu == 0

    def test_frozen(self) -> None:
        score = HealthScore(score=100, max_score=100)
        report = HealthReport(score=score)
        with pytest.raises(AttributeError):
            report.score = HealthScore(score=0, max_score=100)  # type: ignore[misc]
