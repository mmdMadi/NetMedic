"""
Tests for adapter_manager bulk fetch functions.

Uses ``unittest.mock`` to replace ``network.powershell.run_ps`` so the
JSON parsing logic is exercised without real PowerShell calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from network.adapter_manager import (
    _bulk_fetch_dns,
    _bulk_fetch_gateways,
    _bulk_fetch_ip_addresses,
    _bulk_fetch_mtu,
    list_adapters,
)
from network.powershell import PSResult


def _ps(stdout: str = "", exit_code: int = 0) -> PSResult:
    """Helper to build a fake PSResult."""
    return PSResult(stdout=stdout, stderr="", exit_code=exit_code)


# --------------------------------------------------------------------- #
# _bulk_fetch_ip_addresses
# --------------------------------------------------------------------- #

class TestBulkFetchIPAddresses:
    """Tests for the IP address bulk fetch function."""

    def test_empty_stdout(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert _bulk_fetch_ip_addresses() == {}

    def test_single_adapter_ipv4(self) -> None:
        data = [{"InterfaceAlias": "Wi-Fi", "IPAddress": "192.168.1.100", "AddressFamily": "2 (IPv4)"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_ip_addresses()
            assert "Wi-Fi" in result
            assert result["Wi-Fi"] == (["192.168.1.100"], [])

    def test_single_adapter_ipv6(self) -> None:
        data = [{"InterfaceAlias": "Eth", "IPAddress": "fe80::1", "AddressFamily": "23 (IPv6)"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_ip_addresses()
            assert result["Eth"] == ([], ["fe80::1"])

    def test_mixed_ipv4_and_ipv6(self) -> None:
        data = [
            {"InterfaceAlias": "Wi-Fi", "IPAddress": "192.168.1.100", "AddressFamily": "2 (IPv4)"},
            {"InterfaceAlias": "Wi-Fi", "IPAddress": "fe80::1", "AddressFamily": "23 (IPv6)"},
        ]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_ip_addresses()
            assert result["Wi-Fi"] == (["192.168.1.100"], ["fe80::1"])

    def test_multiple_adapters(self) -> None:
        data = [
            {"InterfaceAlias": "Wi-Fi", "IPAddress": "10.0.0.1", "AddressFamily": "2 (IPv4)"},
            {"InterfaceAlias": "Eth", "IPAddress": "192.168.1.1", "AddressFamily": "2 (IPv4)"},
        ]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_ip_addresses()
            assert len(result) == 2
            assert "Wi-Fi" in result
            assert "Eth" in result

    def test_single_dict_not_list(self) -> None:
        """PS may return a single dict instead of a list."""
        data = {"InterfaceAlias": "Wi-Fi", "IPAddress": "10.0.0.5", "AddressFamily": "2 (IPv4)"}
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_ip_addresses()
            assert result["Wi-Fi"] == (["10.0.0.5"], [])

    def test_empty_alias_skipped(self) -> None:
        data = [{"InterfaceAlias": "", "IPAddress": "10.0.0.1", "AddressFamily": "2 (IPv4)"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            assert _bulk_fetch_ip_addresses() == {}

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("PS failed")):
            assert _bulk_fetch_ip_addresses() == {}


# --------------------------------------------------------------------- #
# _bulk_fetch_gateways
# --------------------------------------------------------------------- #

class TestBulkFetchGateways:
    """Tests for the gateway bulk fetch function."""

    def test_empty_stdout(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert _bulk_fetch_gateways() == {}

    def test_single_gateway(self) -> None:
        data = [{"InterfaceAlias": "Wi-Fi", "NextHop": "192.168.1.1"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_gateways()
            assert result == {"Wi-Fi": ["192.168.1.1"]}

    def test_multiple_gateways_same_adapter(self) -> None:
        data = [
            {"InterfaceAlias": "Wi-Fi", "NextHop": "192.168.1.1"},
            {"InterfaceAlias": "Wi-Fi", "NextHop": "10.0.0.1"},
        ]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_gateways()
            assert result["Wi-Fi"] == ["192.168.1.1", "10.0.0.1"]

    def test_empty_hop_skipped(self) -> None:
        data = [{"InterfaceAlias": "Wi-Fi", "NextHop": ""}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            assert _bulk_fetch_gateways() == {}

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("fail")):
            assert _bulk_fetch_gateways() == {}


# --------------------------------------------------------------------- #
# _bulk_fetch_dns
# --------------------------------------------------------------------- #

class TestBulkFetchDns:
    """Tests for the DNS bulk fetch function."""

    def test_empty_stdout(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert _bulk_fetch_dns() == {}

    def test_single_adapter(self) -> None:
        data = [{"InterfaceAlias": "Wi-Fi", "ServerAddresses": ["8.8.8.8", "8.8.4.4"]}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_dns()
            assert result == {"Wi-Fi": ["8.8.8.8", "8.8.4.4"]}

    def test_string_servers_normalized(self) -> None:
        """PS sometimes returns a single string instead of a list."""
        data = [{"InterfaceAlias": "Eth", "ServerAddresses": "1.1.1.1"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_dns()
            assert result == {"Eth": ["1.1.1.1"]}

    def test_single_dict_not_list(self) -> None:
        data = {"InterfaceAlias": "Wi-Fi", "ServerAddresses": ["9.9.9.9"]}
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_dns()
            assert result == {"Wi-Fi": ["9.9.9.9"]}

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("fail")):
            assert _bulk_fetch_dns() == {}


# --------------------------------------------------------------------- #
# _bulk_fetch_mtu
# --------------------------------------------------------------------- #

class TestBulkFetchMtu:
    """Tests for the MTU bulk fetch function."""

    def test_empty_stdout(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert _bulk_fetch_mtu() == {}

    def test_single_adapter(self) -> None:
        data = [{"Name": "Wi-Fi", "Mtu": 1500}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_mtu()
            assert result == {"Wi-Fi": 1500}

    def test_string_mtu_coerced(self) -> None:
        data = [{"Name": "Eth", "Mtu": "1500"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_mtu()
            assert result == {"Eth": 1500}

    def test_invalid_mtu_skipped(self) -> None:
        data = [{"Name": "Bad", "Mtu": "not-a-number"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = _bulk_fetch_mtu()
            assert "Bad" not in result

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("fail")):
            assert _bulk_fetch_mtu() == {}


# --------------------------------------------------------------------- #
# list_adapters (integration of bulk fetches)
# --------------------------------------------------------------------- #

class TestListAdaptersMocked:
    """Integration test for list_adapters with all bulk fetches mocked."""

    def test_full_parse(self) -> None:
        adapter_data = [{
            "Name": "Wi-Fi",
            "InterfaceDescription": "Intel Wi-Fi 6",
            "Status": "Up",
            "MacAddress": "AA:BB:CC:DD:EE:FF",
            "LinkSpeed": "866.7 Mbps",
            "DriverVersion": "22.120.0.3",
            "DriverProvider": "Intel",
            "ifIndex": 12,
            "AdminStatus": 1,
            "PhysicalAdapter": True,
            "Virtual": False,
        }]

        ip_data = [{"InterfaceAlias": "Wi-Fi", "IPAddress": "192.168.1.100", "AddressFamily": "2 (IPv4)"}]
        gw_data = [{"InterfaceAlias": "Wi-Fi", "NextHop": "192.168.1.1"}]
        dns_data = [{"InterfaceAlias": "Wi-Fi", "ServerAddresses": ["8.8.8.8"]}]
        mtu_data = [{"Name": "Wi-Fi", "Mtu": 1500}]

        call_count = 0
        responses = [
            json.dumps(adapter_data),
            json.dumps(ip_data),
            json.dumps(gw_data),
            json.dumps(dns_data),
            json.dumps(mtu_data),
        ]

        def mock_ps(script: str, **kwargs: object) -> PSResult:
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            return _ps(resp)

        with patch("network.powershell.run_ps", side_effect=mock_ps):
            adapters = list_adapters()

        assert len(adapters) == 1
        a = adapters[0]
        assert a.name == "Wi-Fi"
        assert a.category == "Physical"
        assert a.enabled is True
        assert a.ipv4_addresses == ["192.168.1.100"]
        assert a.default_gateways == ["192.168.1.1"]
        assert a.dns_servers == ["8.8.8.8"]
        assert a.mtu == 1500

    def test_empty_adapters(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert list_adapters() == []

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("PS crashed")):
            assert list_adapters() == []
