"""
Mocked tests for dns_tools functions.

Uses ``unittest.mock`` to replace ``network.powershell.run_ps`` so the
JSON parsing and error-handling logic is exercised without real PS calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from network.dns_tools import (
    get_active_adapter_dns,
    get_current_dns_servers,
    reset_dns_automatic,
    set_dns_servers,
)
from network.powershell import PSResult


def _ps(stdout: str = "", exit_code: int = 0) -> PSResult:
    return PSResult(stdout=stdout, stderr="", exit_code=exit_code)


# --------------------------------------------------------------------- #
# get_current_dns_servers
# --------------------------------------------------------------------- #

class TestGetCurrentDnsServers:
    def test_empty_stdout(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            assert get_current_dns_servers() == []

    def test_single_adapter(self) -> None:
        data = [{"InterfaceAlias": "Wi-Fi", "ServerAddresses": ["8.8.8.8", "8.8.4.4"]}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = get_current_dns_servers()
            assert len(result) == 1
            assert result[0].adapter_name == "Wi-Fi"
            assert result[0].dns_servers == ["8.8.8.8", "8.8.4.4"]

    def test_string_servers_normalized(self) -> None:
        data = [{"InterfaceAlias": "Eth", "ServerAddresses": "1.1.1.1"}]
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = get_current_dns_servers()
            assert result[0].dns_servers == ["1.1.1.1"]

    def test_single_dict_not_list(self) -> None:
        data = {"InterfaceAlias": "Wi-Fi", "ServerAddresses": ["9.9.9.9"]}
        with patch("network.powershell.run_ps", return_value=_ps(json.dumps(data))):
            result = get_current_dns_servers()
            assert len(result) == 1

    def test_ps_exception_returns_empty(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("PS failed")):
            assert get_current_dns_servers() == []


# --------------------------------------------------------------------- #
# get_active_adapter_dns
# --------------------------------------------------------------------- #

class TestGetActiveAdapterDns:
    def test_gateway_found(self) -> None:
        gw_ps = _ps("Wi-Fi")
        dns_ps = _ps(json.dumps(["8.8.8.8", "8.8.4.4"]))
        calls = [gw_ps, dns_ps]
        call_idx = 0

        def mock_ps(script: str, **kwargs: object) -> PSResult:
            nonlocal call_idx
            resp = calls[call_idx]
            call_idx += 1
            return resp

        with patch("network.powershell.run_ps", side_effect=mock_ps):
            result = get_active_adapter_dns()
            assert result.adapter_name == "Wi-Fi"
            assert result.dns_servers == ["8.8.8.8", "8.8.4.4"]
            assert result.is_dhcp is False

    def test_no_gateway_fallback(self) -> None:
        """When no gateway is found, falls back to first adapter with DNS."""
        gw_ps = _ps("")
        all_dns_ps = _ps(json.dumps([{"InterfaceAlias": "Eth", "ServerAddresses": ["1.1.1.1"]}]))
        calls = [gw_ps, all_dns_ps]
        call_idx = 0

        def mock_ps(script: str, **kwargs: object) -> PSResult:
            nonlocal call_idx
            resp = calls[call_idx]
            call_idx += 1
            return resp

        with patch("network.powershell.run_ps", side_effect=mock_ps):
            result = get_active_adapter_dns()
            assert result.adapter_name == "Eth"

    def test_ps_exception_returns_dash(self) -> None:
        with patch("network.powershell.run_ps", side_effect=Exception("fail")):
            result = get_active_adapter_dns()
            assert result.adapter_name == "—"


# --------------------------------------------------------------------- #
# set_dns_servers (PS path)
# --------------------------------------------------------------------- #

class TestSetDnsServersPS:
    def test_success(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            result = set_dns_servers("Wi-Fi", "8.8.8.8", "8.8.4.4")
            assert result.success is True
            assert "8.8.8.8" in result.message

    def test_ps_failure(self) -> None:
        from network.powershell import PowerShellError
        with patch("network.powershell.run_ps", side_effect=PowerShellError("PS error")):
            result = set_dns_servers("Wi-Fi", "8.8.8.8")
            assert result.success is False
            assert "Failed" in result.message


# --------------------------------------------------------------------- #
# reset_dns_automatic (PS path)
# --------------------------------------------------------------------- #

class TestResetDnsAutomaticPS:
    def test_success(self) -> None:
        with patch("network.powershell.run_ps", return_value=_ps("")):
            result = reset_dns_automatic("Wi-Fi")
            assert result.success is True

    def test_ps_failure(self) -> None:
        from network.powershell import PowerShellError
        with patch("network.powershell.run_ps", side_effect=PowerShellError("PS error")):
            result = reset_dns_automatic("Wi-Fi")
            assert result.success is False
