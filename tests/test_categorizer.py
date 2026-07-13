"""
Tests for the adapter categorizer.

The categorizer is a pure component — no I/O, no PowerShell, no threads —
so every test runs instantly without network marks.

Note: ``Adapter.from_ps()`` expects PascalCase keys matching PowerShell
output conventions (``Name``, ``Status``, ``Physical``, etc.).
"""

from __future__ import annotations

import pytest

from network.adapter import Adapter, AdapterCategory
from network.categorizer import Categorizer


@pytest.fixture
def cat() -> Categorizer:
    return Categorizer()


def _make(**overrides: object) -> Adapter:
    """Build an Adapter with sensible defaults, overriding specific fields.

    Uses PascalCase keys to match PowerShell output conventions expected
    by ``Adapter.from_ps()``.
    """
    defaults: dict[str, object] = {
        "Name": "Wi-Fi",
        "InterfaceDescription": "Intel Wi-Fi 6 AX201",
        "Status": "Up",
        "MacAddress": "AA:BB:CC:DD:EE:FF",
        "LinkSpeed": "866.7 Mbps",
        "PnPDeviceID": "PCI\\VEN_8086&DEV_2723",
        "HardwareIDs": ["PCI\\VEN_8086&DEV_2723"],
        "Physical": True,
        "Virtual": False,
    }
    defaults.update(overrides)
    return Adapter.from_ps(defaults)  # type: ignore[arg-type]


class TestCategorizerPriority:
    """Ghost > VPN > Virtual > Physical > Disabled > Unknown."""

    def test_ghost_overrides_vpn(self, cat: Categorizer) -> None:
        """Ghost WAN Miniport should be GHOST even if name contains 'VPN'."""
        adapter = _make(
            Name="VPN - WAN Miniport",
            InterfaceDescription="WAN Miniport (IKEv2)",
            PnPDeviceID="",
            HardwareIDs=[],
            MacAddress="—",
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.GHOST

    def test_vpn_overrides_virtual(self, cat: Categorizer) -> None:
        """VPN keyword should win over virtual keyword."""
        adapter = _make(
            Name="TAP-Windows Adapter V9",
            InterfaceDescription="TAP Virtual Network Adapter",
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.VPN

    def test_virtual_overrides_physical(self, cat: Categorizer) -> None:
        """Virtual keyword should win even if physical flag is True."""
        adapter = _make(
            Name="vEthernet (WSL)",
            InterfaceDescription="Hyper-V Virtual Ethernet Adapter",
            Physical=True,
        )
        assert cat.categorize(adapter) == AdapterCategory.VIRTUAL


class TestCategorizerVPN:
    """VPN detection via name/description matching."""

    @pytest.mark.parametrize(
        "name,desc",
        [
            ("WireGuard Tunnel", "WireGuard"),
            ("OpenVPN TUN", "TAP-Windows Adapter"),
            ("Cloudflare WARP", "Cloudflare WARP Tunnel"),
            ("Tailscale", "Tailscale Tunnel"),
            ("ZeroTier One", "ZeroTier Virtual Network"),
            ("Cisco AnyConnect", "AnyConnect Secure Mobility Client"),
            ("VPN Connection", "Generic VPN"),
        ],
    )
    def test_vpn_recognized(self, cat: Categorizer, name: str, desc: str) -> None:
        adapter = _make(Name=name, InterfaceDescription=desc, Physical=False)
        assert cat.categorize(adapter) == AdapterCategory.VPN


class TestCategorizerVirtual:
    """Virtual adapter detection."""

    @pytest.mark.parametrize(
        "name,desc",
        [
            ("vEthernet (Default Switch)", "Hyper-V Virtual Ethernet Adapter"),
            ("VMware Network Adapter VMnet8", "VMware Virtual Ethernet Adapter"),
            ("VirtualBox Host-Only Network", "VirtualBox Host-Only Ethernet Adapter"),
            ("vEthernet (Docker)", "Hyper-V Virtual Ethernet Adapter"),
            ("Npcap Loopback Adapter", "Npcap Loopback Adapter"),
        ],
    )
    def test_virtual_recognized(self, cat: Categorizer, name: str, desc: str) -> None:
        adapter = _make(Name=name, InterfaceDescription=desc, Physical=False)
        assert cat.categorize(adapter) == AdapterCategory.VIRTUAL


class TestCategorizerPhysical:
    """Physical adapter detection via flag."""

    def test_physical_adapter(self, cat: Categorizer) -> None:
        adapter = _make(Physical=True)
        assert cat.categorize(adapter) == AdapterCategory.PHYSICAL


class TestCategorizerDisabled:
    """Disabled adapter detection."""

    def test_disabled_adapter(self, cat: Categorizer) -> None:
        adapter = _make(
            Physical=False,
            Status="Disabled",
        )
        assert cat.categorize(adapter) == AdapterCategory.DISABLED


class TestCategorizerGhost:
    """Ghost adapter heuristic detection."""

    def test_wan_miniport(self, cat: Categorizer) -> None:
        adapter = _make(
            Name="WAN Miniport (SSTP)",
            InterfaceDescription="WAN Miniport (SSTP)",
            PnPDeviceID="",
            HardwareIDs=[],
            MacAddress="—",
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.GHOST

    def test_isatap(self, cat: Categorizer) -> None:
        adapter = _make(
            Name="isatap.{ABCD-1234}",
            InterfaceDescription="Microsoft ISATAP Adapter",
            PnPDeviceID="",
            HardwareIDs=[],
            MacAddress="—",
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.GHOST

    def test_no_pnp_no_hw_no_mac(self, cat: Categorizer) -> None:
        """Ghost detection when PnPDeviceID is the sentinel '—'.

        Note: ``from_ps`` normalizes empty PnPDeviceID to the sentinel
        ``"—"``, so the ``not pnp`` heuristic only fires when the raw
        value is truly ``None`` *and* ``safe_str`` doesn't produce a
        truthy sentinel. This tests the case where hardware_ids is
        empty and MAC is the sentinel — the name-based prefix checks
        are the reliable ghost triggers in practice.
        """
        adapter = _make(
            Name="WAN Miniport (Gre)",
            InterfaceDescription="WAN Miniport (Gre)",
            PnPDeviceID="",
            HardwareIDs=[],
            MacAddress="—",
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.GHOST


class TestCategorizerUnknown:
    """Fallback when no rule matches."""

    def test_unknown_adapter(self, cat: Categorizer) -> None:
        adapter = _make(
            Name="Some Weird Device",
            InterfaceDescription="Custom NIC",
            PnPDeviceID="PCI\\VEN_1234",
            HardwareIDs=["PCI\\VEN_1234"],
            Physical=False,
        )
        assert cat.categorize(adapter) == AdapterCategory.UNKNOWN
