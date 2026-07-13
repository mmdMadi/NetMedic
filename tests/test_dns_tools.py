"""
Tests for DNS tools.

Covers dataclasses, presets, and input validation logic.
Functions that call PowerShell/subprocess are marked ``@pytest.mark.network``.
"""

from __future__ import annotations

import pytest

from network.dns_tools import (
    DNS_PRESETS,
    AdapterDns,
    DnsOperationResult,
    DnsPreset,
    set_dns_servers,
    reset_dns_automatic,
)


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

class TestDnsPreset:
    """Tests for the DnsPreset dataclass."""

    def test_creation(self) -> None:
        p = DnsPreset(name="Test", primary="1.1.1.1")
        assert p.name == "Test"
        assert p.primary == "1.1.1.1"
        assert p.secondary == ""
        assert p.description == ""

    def test_with_secondary(self) -> None:
        p = DnsPreset(name="Dual", primary="1.1.1.1", secondary="1.0.0.1")
        assert p.secondary == "1.0.0.1"

    def test_frozen(self) -> None:
        p = DnsPreset(name="Frozen", primary="1.1.1.1")
        with pytest.raises(AttributeError):
            p.name = "Changed"  # type: ignore[misc]


class TestAdapterDns:
    """Tests for the AdapterDns dataclass."""

    def test_defaults(self) -> None:
        d = AdapterDns(adapter_name="Wi-Fi")
        assert d.dns_servers == []
        assert d.is_dhcp is True

    def test_with_servers(self) -> None:
        d = AdapterDns(adapter_name="Eth", dns_servers=["8.8.8.8", "8.8.4.4"], is_dhcp=False)
        assert len(d.dns_servers) == 2
        assert d.is_dhcp is False


class TestDnsOperationResult:
    """Tests for the DnsOperationResult dataclass."""

    def test_success(self) -> None:
        r = DnsOperationResult(success=True, message="OK", adapter_name="Wi-Fi")
        assert r.success is True
        assert r.adapter_name == "Wi-Fi"

    def test_failure(self) -> None:
        r = DnsOperationResult(success=False, message="Failed")
        assert r.success is False
        assert r.adapter_name == ""


# --------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------- #

class TestDnsPresets:
    """Tests for the DNS_PRESETS list."""

    def test_preset_count(self) -> None:
        assert len(DNS_PRESETS) == 7

    def test_automatic_first(self) -> None:
        assert DNS_PRESETS[0].name == "Automatic"
        assert DNS_PRESETS[0].primary == ""

    def test_all_have_names(self) -> None:
        for p in DNS_PRESETS:
            assert p.name, f"Preset missing name: {p}"

    def test_non_automatic_have_ips(self) -> None:
        for p in DNS_PRESETS[1:]:
            assert "." in p.primary, f"{p.name} has invalid primary IP: {p.primary}"

    def test_known_providers(self) -> None:
        names = {p.name for p in DNS_PRESETS}
        assert "Cloudflare" in names
        assert "Google" in names
        assert "Quad9" in names
        assert "OpenDNS" in names
        assert "Shecan" in names
        assert "Electro" in names


# --------------------------------------------------------------------- #
# Validation logic (no PS calls needed)
# --------------------------------------------------------------------- #

class TestSetDnsValidation:
    """Tests for set_dns_servers input validation (no PS calls)."""

    def test_empty_adapter_name(self) -> None:
        result = set_dns_servers("", "8.8.8.8")
        assert result.success is False
        assert "No adapter" in result.message

    def test_dash_adapter_name(self) -> None:
        result = set_dns_servers("—", "8.8.8.8")
        assert result.success is False

    def test_empty_primary(self) -> None:
        result = set_dns_servers("Wi-Fi", "")
        assert result.success is False
        assert "required" in result.message

    def test_invalid_primary_ip(self) -> None:
        result = set_dns_servers("Wi-Fi", "not-an-ip")
        assert result.success is False
        assert "Invalid" in result.message

    def test_invalid_secondary_ip(self) -> None:
        result = set_dns_servers("Wi-Fi", "8.8.8.8", secondary="bad")
        assert result.success is False
        assert "Invalid" in result.message

    def test_valid_ips_reach_ps(self) -> None:
        """Valid IPs should attempt the PS call (which may fail on CI)."""
        result = set_dns_servers("Wi-Fi", "8.8.8.8", "8.8.4.4")
        # On CI this will fail because the adapter doesn't exist,
        # but it should NOT fail on validation.
        assert "Invalid" not in result.message
        assert "No adapter" not in result.message


class TestResetDnsValidation:
    """Tests for reset_dns_automatic input validation."""

    def test_empty_adapter_name(self) -> None:
        result = reset_dns_automatic("")
        assert result.success is False
        assert "No adapter" in result.message

    def test_dash_adapter_name(self) -> None:
        result = reset_dns_automatic("—")
        assert result.success is False
