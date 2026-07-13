"""
Tests for the adapter manager.

Covers dataclasses and input validation logic.
Functions that call PowerShell are marked ``@pytest.mark.network``.
"""

from __future__ import annotations

import pytest

from network.adapter_manager import (
    AdapterDetail,
    AdapterOperationResult,
    enable_adapter,
    disable_adapter,
)


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

class TestAdapterDetail:
    """Tests for the AdapterDetail dataclass."""

    def test_creation(self) -> None:
        d = AdapterDetail(
            name="Wi-Fi",
            description="Intel Wi-Fi 6",
            status="Up",
            enabled=True,
            category="Physical",
            mac_address="AA:BB:CC:DD:EE:FF",
            link_speed="866.7 Mbps",
            driver_version="22.120.0.3",
            driver_provider="Intel",
        )
        assert d.name == "Wi-Fi"
        assert d.enabled is True
        assert d.ipv4_addresses == []
        assert d.mtu == 0

    def test_with_ip_data(self) -> None:
        d = AdapterDetail(
            name="Eth",
            description="Realtek",
            status="Up",
            enabled=True,
            category="Physical",
            mac_address="11:22:33:44:55:66",
            link_speed="1 Gbps",
            driver_version="1.0",
            driver_provider="Realtek",
            ipv4_addresses=["192.168.1.100"],
            ipv6_addresses=["fe80::1"],
            default_gateways=["192.168.1.1"],
            dns_servers=["8.8.8.8"],
            mtu=1500,
            if_index=12,
        )
        assert d.ipv4_addresses == ["192.168.1.100"]
        assert d.mtu == 1500

    def test_frozen(self) -> None:
        d = AdapterDetail(
            name="X", description="", status="", enabled=False,
            category="", mac_address="", link_speed="",
            driver_version="", driver_provider="",
        )
        with pytest.raises(AttributeError):
            d.name = "Y"  # type: ignore[misc]


class TestAdapterOperationResult:
    """Tests for the AdapterOperationResult dataclass."""

    def test_success(self) -> None:
        r = AdapterOperationResult(success=True, message="OK", adapter_name="Wi-Fi")
        assert r.success is True
        assert r.adapter_name == "Wi-Fi"

    def test_failure(self) -> None:
        r = AdapterOperationResult(success=False, message="Failed")
        assert r.success is False
        assert r.adapter_name == ""


# --------------------------------------------------------------------- #
# Validation logic (no PS calls)
# --------------------------------------------------------------------- #

class TestEnableAdapterValidation:
    """Tests for enable_adapter input validation."""

    def test_empty_name(self) -> None:
        result = enable_adapter("")
        assert result.success is False
        assert "No adapter" in result.message

    def test_dash_name(self) -> None:
        result = enable_adapter("—")
        assert result.success is False


class TestDisableAdapterValidation:
    """Tests for disable_adapter input validation."""

    def test_empty_name(self) -> None:
        result = disable_adapter("")
        assert result.success is False
        assert "No adapter" in result.message

    def test_dash_name(self) -> None:
        result = disable_adapter("—")
        assert result.success is False
