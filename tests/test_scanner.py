"""
Tests for the adapter scanner.

Covers ScanStats, ScanResult, and ScanError dataclasses.
The AdapterScanner.scan() method requires PowerShell and is tested via
the network-marked test infrastructure.
"""

from __future__ import annotations

import pytest

from network.adapter import Adapter, AdapterCategory
from network.scanner import ScanError, ScanResult, ScanStats


def _make_adapter(name: str = "Wi-Fi", category: AdapterCategory = AdapterCategory.PHYSICAL, status: str = "Up") -> Adapter:
    """Build a minimal Adapter for testing.

    Sets the category directly since ``from_ps()`` defaults to UNKNOWN.
    """
    adapter = Adapter.from_ps({
        "Name": name,
        "InterfaceDescription": "Test Adapter",
        "Status": status,
    })
    adapter.category = category
    return adapter


class TestScanStats:
    def test_empty(self) -> None:
        stats = ScanStats.from_adapters([])
        assert stats.total == 0
        assert stats.physical == 0

    def test_single_physical(self) -> None:
        stats = ScanStats.from_adapters([_make_adapter("Wi-Fi", AdapterCategory.PHYSICAL)])
        assert stats.total == 1
        assert stats.physical == 1
        assert stats.connected == 1

    def test_mixed_categories(self) -> None:
        adapters = [
            _make_adapter("Wi-Fi", AdapterCategory.PHYSICAL),
            _make_adapter("vEthernet", AdapterCategory.VIRTUAL),
            _make_adapter("WireGuard", AdapterCategory.VPN),
            _make_adapter("Ghost", AdapterCategory.GHOST),
        ]
        stats = ScanStats.from_adapters(adapters)
        assert stats.total == 4
        assert stats.physical == 1
        assert stats.virtual == 1
        assert stats.vpn == 1
        assert stats.ghost == 1

    def test_disabled_counted(self) -> None:
        adapters = [_make_adapter("Eth", AdapterCategory.DISABLED, status="Disabled")]
        stats = ScanStats.from_adapters(adapters)
        assert stats.disabled == 1
        assert stats.connected == 0

    def test_disconnected_counted(self) -> None:
        adapters = [_make_adapter("Eth", AdapterCategory.PHYSICAL, status="Disconnected")]
        stats = ScanStats.from_adapters(adapters)
        assert stats.disconnected == 1
        assert stats.connected == 0


class TestScanResult:
    def test_ok_when_no_error(self) -> None:
        result = ScanResult()
        assert result.ok is True

    def test_not_ok_with_error(self) -> None:
        result = ScanResult(error="Something failed")
        assert result.ok is False

    def test_default_stats(self) -> None:
        result = ScanResult()
        assert result.stats.total == 0


class TestScanError:
    def test_message(self) -> None:
        err = ScanError("Scan failed")
        assert str(err) == "Scan failed"
