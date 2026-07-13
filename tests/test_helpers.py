"""
Tests for the helper utilities.

Covers formatting functions, string helpers, and utility functions.
"""

from __future__ import annotations

import pytest

from utils.helpers import (
    coalesce,
    first_non_blank,
    format_mac,
    format_speed,
    safe_str,
    score_color,
    truncate,
)


class TestSafeStr:
    """Tests for the safe_str function."""

    def test_string_passthrough(self) -> None:
        """Should return strings as-is."""
        assert safe_str("hello") == "hello"

    def test_none_returns_dash(self) -> None:
        """Should return dash for None."""
        assert safe_str(None) == "—"

    def test_none_custom_default(self) -> None:
        """Should return custom default for None."""
        assert safe_str(None, default="N/A") == "N/A"

    def test_empty_string(self) -> None:
        """Should return dash for empty string (falsy values treated as None)."""
        assert safe_str("") == "—"

    def test_int_to_string(self) -> None:
        """Should convert integers to strings."""
        assert safe_str(42) == "42"

    def test_whitespace_stripped(self) -> None:
        """Should strip whitespace."""
        assert safe_str("  hello  ") == "hello"


class TestTruncate:
    """Tests for the truncate function."""

    def test_short_string(self) -> None:
        """Should not truncate short strings."""
        assert truncate("hello", 10) == "hello"

    def test_long_string(self) -> None:
        """Should truncate long strings and add ellipsis."""
        result = truncate("hello world", 5)
        assert "hell" in result
        assert "…" in result

    def test_empty_string(self) -> None:
        """Should handle empty strings."""
        assert truncate("", 10) == ""


class TestFormatMac:
    """Tests for the format_mac function."""

    def test_dash_separated(self) -> None:
        """Should normalize dash-separated MAC."""
        assert format_mac("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"

    def test_colon_separated(self) -> None:
        """Should keep colon-separated MAC."""
        assert format_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"

    def test_empty(self) -> None:
        """Should handle empty MAC."""
        assert format_mac("") == "—"

    def test_none(self) -> None:
        """Should handle None MAC."""
        assert format_mac(None) == "—"


class TestFormatSpeed:
    """Tests for the format_speed function."""

    def test_mbps(self) -> None:
        """Should format Mbps speeds."""
        result = format_speed("1 Gbps")
        assert "Mbps" in result or "Gbps" in result

    def test_bps(self) -> None:
        """Should handle bps speeds."""
        result = format_speed("0 bps")
        assert "bps" in result

    def test_none(self) -> None:
        """Should handle None."""
        assert format_speed(None) == "—"


class TestCoalesce:
    """Tests for the coalesce function."""

    def test_first_non_none(self) -> None:
        """Should return the first non-None value."""
        assert coalesce(None, "second", "third") == "second"

    def test_all_none(self) -> None:
        """Should return None when all are None."""
        assert coalesce(None, None, None) is None

    def test_first_value(self) -> None:
        """Should return the first value when it's not None."""
        assert coalesce("first", "second") == "first"


class TestFirstNonBlank:
    """Tests for the first_non_blank function."""

    def test_first_blank(self) -> None:
        """Should return the first non-blank value."""
        assert first_non_blank(["", "hello", "world"]) == "hello"

    def test_all_blank(self) -> None:
        """Should return default when all are blank."""
        assert first_non_blank(["", "", ""], default="N/A") == "N/A"

    def test_first_non_blank(self) -> None:
        """Should return the first non-blank value."""
        assert first_non_blank(["hello", "world"]) == "hello"


class TestScoreColor:
    """Tests for the score_color function."""

    def test_excellent(self) -> None:
        """Should return green for scores >= 90."""
        assert score_color(90) == "green"
        assert score_color(100) == "green"

    def test_good(self) -> None:
        """Should return yellow for scores >= 70."""
        assert score_color(70) == "yellow"
        assert score_color(89) == "yellow"

    def test_fair(self) -> None:
        """Should return orange for scores >= 50."""
        assert score_color(50) == "orange"
        assert score_color(69) == "orange"

    def test_poor(self) -> None:
        """Should return red for scores < 50."""
        assert score_color(0) == "red"
        assert score_color(49) == "red"

    def test_boundary_89(self) -> None:
        """Score 89 should be yellow (just below excellent)."""
        assert score_color(89) == "yellow"

    def test_boundary_90(self) -> None:
        """Score 90 should be green (excellent threshold)."""
        assert score_color(90) == "green"

    def test_boundary_69(self) -> None:
        """Score 69 should be orange (just below good)."""
        assert score_color(69) == "orange"

    def test_boundary_70(self) -> None:
        """Score 70 should be yellow (good threshold)."""
        assert score_color(70) == "yellow"
