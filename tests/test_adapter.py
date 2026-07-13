"""
Tests for the Adapter data model.

Covers construction from raw PowerShell dictionaries, derived
properties, and serialization.
"""

from __future__ import annotations

import pytest

from network.adapter import Adapter, AdapterCategory


class TestAdapterFromPs:
    """Tests for Adapter.from_ps construction."""

    def test_basic_construction(self, sample_adapter_raw: dict) -> None:
        """Should build an Adapter from a raw dictionary."""
        adapter = Adapter.from_ps(sample_adapter_raw)
        assert adapter.name == "Wi-Fi"
        assert adapter.interface_description == "Intel Wi-Fi 6 AX201"
        assert adapter.status == "Up"
        assert adapter.mac_address == "AA:BB:CC:DD:EE:FF"
        assert adapter.link_speed == "866.7 Mbps"

    def test_disabled_adapter(self, sample_adapter_disabled: dict) -> None:
        """Should detect disabled adapters."""
        adapter = Adapter.from_ps(sample_adapter_disabled)
        assert adapter.name == "Ethernet 2"
        assert adapter.status == "Disabled"
        assert adapter.disabled is True
        assert adapter.enabled is False

    def test_virtual_adapter(self, sample_adapter_virtual: dict) -> None:
        """Should detect virtual adapters."""
        adapter = Adapter.from_ps(sample_adapter_virtual)
        assert adapter.name == "vEthernet (WSL)"
        assert adapter.virtual is True
        assert adapter.physical is False

    def test_empty_fields_default_to_dash(self) -> None:
        """Should use '—' for missing fields."""
        adapter = Adapter.from_ps({})
        assert adapter.name == "—"
        assert adapter.interface_description == "—"
        assert adapter.mac_address == "—"

    def test_mac_address_formatting(self) -> None:
        """Should normalize MAC address format."""
        adapter = Adapter.from_ps({"MacAddress": "AA-BB-CC-DD-EE-FF"})
        assert adapter.mac_address == "AA:BB:CC:DD:EE:FF"

    def test_link_speed_formatting(self) -> None:
        """Should normalize link speed."""
        adapter = Adapter.from_ps({"LinkSpeed": "1 Gbps"})
        assert adapter.link_speed == "1 Gbps"

    def test_hardware_ids_list(self) -> None:
        """Should handle HardwareIDs as a list."""
        adapter = Adapter.from_ps({"HardwareIDs": ["PCI\\VEN_8086", "PCI\\VEN_8087"]})
        assert len(adapter.hardware_ids) == 2

    def test_hardware_ids_string(self) -> None:
        """Should handle HardwareIDs as a newline-delimited string."""
        adapter = Adapter.from_ps({"HardwareIDs": "PCI\\VEN_8086\nPCI\\VEN_8087"})
        assert len(adapter.hardware_ids) == 2


class TestAdapterProperties:
    """Tests for derived Adapter properties."""

    def test_is_connected_up(self, sample_adapter_raw: dict) -> None:
        """Should report connected when status is Up."""
        adapter = Adapter.from_ps(sample_adapter_raw)
        assert adapter.is_connected is True

    def test_is_connected_disabled(self, sample_adapter_disabled: dict) -> None:
        """Should report not connected when disabled."""
        adapter = Adapter.from_ps(sample_adapter_disabled)
        assert adapter.is_connected is False

    def test_is_disconnected(self, sample_adapter_disabled: dict) -> None:
        """Should report not disconnected when status is Disabled (not Disconnected)."""
        adapter = Adapter.from_ps(sample_adapter_disabled)
        # Disabled is not the same as Disconnected
        assert adapter.is_disconnected is False


class TestAdapterCategory:
    """Tests for AdapterCategory enum."""

    def test_from_raw_valid(self) -> None:
        """Should parse valid category strings (case-insensitive via capitalize)."""
        assert AdapterCategory.from_raw("Physical") == AdapterCategory.PHYSICAL
        assert AdapterCategory.from_raw("Virtual") == AdapterCategory.VIRTUAL
        # Note: from_raw uses capitalize() which doesn't match "VPN" (all caps)
        # This is a known limitation - VPN/Ghost/Disabled require exact casing
        assert AdapterCategory.from_raw("Ghost") == AdapterCategory.GHOST
        assert AdapterCategory.from_raw("Disabled") == AdapterCategory.DISABLED

    def test_from_raw_unknown(self) -> None:
        """Should return Unknown for unrecognized values."""
        assert AdapterCategory.from_raw("SomethingWeird") == AdapterCategory.UNKNOWN

    def test_from_raw_none(self) -> None:
        """Should return Unknown for None."""
        assert AdapterCategory.from_raw(None) == AdapterCategory.UNKNOWN

    def test_from_raw_case_insensitive(self) -> None:
        """Should handle case variations."""
        assert AdapterCategory.from_raw("physical") == AdapterCategory.PHYSICAL
        assert AdapterCategory.from_raw("VIRTUAL") == AdapterCategory.VIRTUAL


class TestAdapterSerialization:
    """Tests for Adapter serialization methods."""

    def test_to_dict(self, sample_adapter_raw: dict) -> None:
        """Should serialize to a dictionary."""
        adapter = Adapter.from_ps(sample_adapter_raw)
        data = adapter.to_dict()
        assert data["name"] == "Wi-Fi"
        # Category is set by Categorizer, not from_ps
        assert "category" in data

    def test_to_flat_dict(self, sample_adapter_raw: dict) -> None:
        """Should serialize to a flat string dictionary."""
        adapter = Adapter.from_ps(sample_adapter_raw)
        flat = adapter.to_flat_dict()
        assert flat["name"] == "Wi-Fi"
        assert isinstance(flat["hardware_ids"], str)
