"""
Tests for local network info.

Covers dataclasses and the DNS provider matching logic.
"""

from __future__ import annotations

import pytest

from network.local_info import AdapterInfo, LocalNetworkInfo, get_dns_provider


class TestAdapterInfo:
    def test_creation(self) -> None:
        info = AdapterInfo(name="Wi-Fi", is_up=True, speed=867, mtu=1500)
        assert info.name == "Wi-Fi"
        assert info.is_up is True
        assert info.ipv4 == []

    def test_frozen(self) -> None:
        info = AdapterInfo(name="Eth", is_up=False, speed=0, mtu=1500)
        with pytest.raises(AttributeError):
            info.name = "X"  # type: ignore[misc]


class TestLocalNetworkInfo:
    def test_creation(self) -> None:
        info = LocalNetworkInfo(hostname="PC", local_ip="10.0.0.1", connected_adapter="Wi-Fi")
        assert info.hostname == "PC"
        assert info.adapters == []


class TestGetDnsProvider:
    def test_cloudflare(self) -> None:
        assert get_dns_provider("1.1.1.1") == "Cloudflare"

    def test_google(self) -> None:
        assert get_dns_provider("8.8.8.8") == "Google"

    def test_quad9(self) -> None:
        assert get_dns_provider("9.9.9.9") == "Quad9"

    def test_opendns(self) -> None:
        assert get_dns_provider("208.67.222.222") == "OpenDNS"

    def test_unknown_returns_ip(self) -> None:
        """Unknown IPs are returned as-is (not empty string)."""
        assert get_dns_provider("1.2.3.4") == "1.2.3.4"

    def test_empty(self) -> None:
        assert get_dns_provider("") == ""

    def test_dash_returns_dash(self) -> None:
        assert get_dns_provider("—") == "—"
