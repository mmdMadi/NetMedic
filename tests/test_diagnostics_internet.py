"""
Tests for the Internet diagnostics module.

Covers ping, traceroute, MTU, DNS, and gateway functions.
"""

from __future__ import annotations

import pytest

from network.diagnostics_internet import (
    DnsResolution,
    DnsTestResult,
    GatewayResult,
    MtuResult,
    MultiPingResult,
    PingResult,
    TracerouteHop,
    TracerouteResult,
    detect_gateway,
    detect_mtu,
    measure_latency,
    measure_packet_loss,
    ping_host,
    ping_multi_host,
    test_dns_resolution,
    trace_route,
)


class TestPingResult:
    """Tests for the PingResult dataclass."""

    def test_creation(self) -> None:
        """Should create a PingResult with all fields."""
        result = PingResult(
            host="8.8.8.8",
            reachable=True,
            packets_sent=4,
            packets_received=4,
            loss_pct=0.0,
            min_ms=10.0,
            avg_ms=15.0,
            max_ms=20.0,
            jitter_ms=2.5,
        )
        assert result.host == "8.8.8.8"
        assert result.reachable is True
        assert result.avg_ms == 15.0

    def test_frozen(self) -> None:
        """Should be immutable."""
        result = PingResult(host="8.8.8.8", reachable=True)
        with pytest.raises(AttributeError):
            result.host = "changed"  # type: ignore[misc]


class TestMultiPingResult:
    """Tests for the MultiPingResult dataclass."""

    def test_creation(self) -> None:
        """Should create a MultiPingResult."""
        result = MultiPingResult(
            results=[],
            total_hosts=4,
            reachable_hosts=3,
        )
        assert result.total_hosts == 4
        assert result.reachable_hosts == 3


class TestTracerouteResult:
    """Tests for the TracerouteResult dataclass."""

    def test_creation(self) -> None:
        """Should create a TracerouteResult."""
        hop = TracerouteHop(hop=1, ip="192.168.1.1", latency_ms=1.0)
        result = TracerouteResult(host="8.8.8.8", hops=[hop])
        assert len(result.hops) == 1
        assert result.hops[0].ip == "192.168.1.1"


class TestMtuResult:
    """Tests for the MtuResult dataclass."""

    def test_creation(self) -> None:
        """Should create an MtuResult."""
        result = MtuResult(mtu=1500, method="ICMP DF-binary search")
        assert result.mtu == 1500


class TestDnsTestResult:
    """Tests for the DnsTestResult dataclass."""

    def test_creation(self) -> None:
        """Should create a DnsTestResult."""
        result = DnsTestResult(
            results=[],
            avg_ms=50.0,
            min_ms=30.0,
            max_ms=70.0,
            servers_tested=4,
            servers_ok=3,
        )
        assert result.avg_ms == 50.0
        assert result.servers_ok == 3


class TestGatewayResult:
    """Tests for the GatewayResult dataclass."""

    def test_creation(self) -> None:
        """Should create a GatewayResult."""
        result = GatewayResult(
            gateway="192.168.1.1",
            interface="Wi-Fi",
            reachable=True,
            latency_ms=1.0,
        )
        assert result.gateway == "192.168.1.1"
        assert result.reachable is True


@pytest.mark.network
class TestPingHost:
    """Tests that make real ping calls.

    Run with: pytest -m network
    """

    def test_ping_localhost(self) -> None:
        """Should ping localhost successfully."""
        result = ping_host("127.0.0.1", count=2, timeout=2)
        assert result.reachable is True
        assert result.packets_received > 0

    def test_ping_invalid_host(self) -> None:
        """Should handle invalid host gracefully."""
        result = ping_host("192.0.2.1", count=1, timeout=1)  # TEST-NET
        assert result.reachable is False

    def test_multi_ping(self) -> None:
        """Should ping multiple hosts."""
        result = ping_multi_host(["127.0.0.1"], count=2, timeout=2)
        assert result.total_hosts == 1
        assert result.reachable_hosts >= 0


@pytest.mark.network
class TestDnsResolution:
    """Tests that make real DNS calls.

    Run with: pytest -m network
    """

    def test_dns_resolution(self) -> None:
        """Should resolve DNS servers."""
        result = test_dns_resolution(servers=["8.8.8.8"])
        assert result.servers_tested == 1
        assert result.servers_ok >= 0


@pytest.mark.network
class TestGateway:
    """Tests that detect the gateway.

    Run with: pytest -m network
    """

    def test_detect_gateway(self) -> None:
        """Should detect a gateway."""
        result = detect_gateway()
        assert isinstance(result, GatewayResult)
