"""
Tests for the Internet connectivity module.

Covers status enum, result dataclass, and probe functions.
"""

from __future__ import annotations

import pytest

from network.internet import (
    InternetCheckResult,
    InternetStatus,
    check_internet,
    check_internet_with_latency,
    is_connected,
)


class TestInternetStatus:
    """Tests for the InternetStatus enum."""

    def test_members(self) -> None:
        """Should have all expected members."""
        assert InternetStatus.CONNECTED.value == "Connected"
        assert InternetStatus.NO_INTERNET.value == "No Internet"
        assert InternetStatus.NO_DNS.value == "No DNS"
        assert InternetStatus.CHECK_FAILED.value == "Check Failed"

    def test_from_raw_valid(self) -> None:
        """Should parse valid status strings."""
        assert InternetStatus.from_raw("Connected") == InternetStatus.CONNECTED
        assert InternetStatus.from_raw("No Internet") == InternetStatus.NO_INTERNET

    def test_from_raw_unknown(self) -> None:
        """Should return CHECK_FAILED for unknown strings."""
        assert InternetStatus.from_raw("SomethingElse") == InternetStatus.CHECK_FAILED

    def test_from_raw_case_insensitive(self) -> None:
        """Should handle case variations."""
        assert InternetStatus.from_raw("connected") == InternetStatus.CONNECTED


class TestInternetCheckResult:
    """Tests for the InternetCheckResult dataclass."""

    def test_is_connected_true(self) -> None:
        """Should report connected when status is CONNECTED."""
        result = InternetCheckResult(status=InternetStatus.CONNECTED, latency_ms=10.0)
        assert result.is_connected is True

    def test_is_connected_false(self) -> None:
        """Should report not connected when status is not CONNECTED."""
        result = InternetCheckResult(status=InternetStatus.NO_INTERNET)
        assert result.is_connected is False

    def test_latency_display_with_ms(self) -> None:
        """Should format latency in milliseconds (integer)."""
        result = InternetCheckResult(status=InternetStatus.CONNECTED, latency_ms=12.5)
        assert result.latency_display == "12 ms"

    def test_latency_display_sub_ms(self) -> None:
        """Should show <1 ms for sub-millisecond latency."""
        result = InternetCheckResult(status=InternetStatus.CONNECTED, latency_ms=0.5)
        assert result.latency_display == "<1 ms"

    def test_latency_display_none(self) -> None:
        """Should show dash when latency is None."""
        result = InternetCheckResult(status=InternetStatus.NO_INTERNET)
        assert result.latency_display == "—"


@pytest.mark.network
class TestCheckInternet:
    """Tests for the actual internet check functions.

    These tests make real network calls and are marked as 'network'.
    Run with: pytest -m network
    """

    def test_check_internet_returns_status(self) -> None:
        """Should return an InternetStatus."""
        status = check_internet()
        assert isinstance(status, InternetStatus)

    def test_check_internet_with_latency(self) -> None:
        """Should return an InternetCheckResult."""
        result = check_internet_with_latency()
        assert isinstance(result, InternetCheckResult)

    def test_is_connected_returns_bool(self) -> None:
        """Should return a boolean."""
        assert isinstance(is_connected(), bool)
