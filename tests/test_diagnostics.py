"""
Tests for per-adapter IP diagnostics.

Covers the _normalize_string_rows helper and Diagnostics.enrich() with
a mocked PowerShell runner.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from network.adapter import Adapter
from network.diagnostics import Diagnostics, _normalize_string_rows


class TestNormalizeStringRows:
    def test_none(self) -> None:
        assert _normalize_string_rows(None) == []

    def test_empty_string(self) -> None:
        assert _normalize_string_rows("") == []

    def test_single_string(self) -> None:
        assert _normalize_string_rows("192.168.1.1") == ["192.168.1.1"]

    def test_list_of_strings(self) -> None:
        assert _normalize_string_rows(["a", "b", "c"]) == ["a", "b", "c"]

    def test_list_with_blanks(self) -> None:
        assert _normalize_string_rows(["a", "", "b"]) == ["a", "b"]

    def test_single_int(self) -> None:
        assert _normalize_string_rows(42) == ["42"]

    def test_whitespace_stripped(self) -> None:
        assert _normalize_string_rows("  hello  ") == ["hello"]


class TestDiagnosticsEnrich:
    def test_dash_name_returns_unchanged(self) -> None:
        d = Diagnostics()
        adapter = Adapter(name="—")
        result = d.enrich(adapter)
        assert result.ipv4_addresses == []

    def test_empty_name_returns_unchanged(self) -> None:
        d = Diagnostics()
        adapter = Adapter(name="")
        result = d.enrich(adapter)
        assert result.ipv4_addresses == []

    def test_enrich_with_mocked_runner(self) -> None:
        runner = MagicMock()
        # Mock run_json to return IP data on first call, empty on others
        runner.run_json.side_effect = [
            [{"IPAddress": "192.168.1.100", "PrefixLength": 24, "AddressFamily": "IPv4"}],
            ["192.168.1.1"],
            ["8.8.8.8"],
        ]
        d = Diagnostics(runner=runner)
        adapter = Adapter(name="Wi-Fi")
        result = d.enrich(adapter)
        assert "192.168.1.100" in result.ipv4_addresses
