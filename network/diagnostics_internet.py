"""
Internet diagnostics service.

Provides low-level network diagnostic functions that run system commands
(ping, tracert, netsh, PowerShell) and return structured, frozen
dataclasses.  Every function is synchronous and designed to be called
from a background thread — never from the UI thread.

Functions
---------
- :func:`ping_host`          — ICMP ping a single host (stats + jitter)
- :func:`ping_multi_host`    — ping multiple hosts concurrently
- :func:`measure_packet_loss` — packet loss test over N packets
- :func:`trace_route`        — traceroute with hop-by-hop latency
- :func:`detect_mtu`         — binary-search path-MTU discovery
- :func:`test_dns_resolution` — parallel DNS resolution across servers
- :func:`detect_gateway`     — default gateway + interface
- :func:`measure_latency`    — repeated ICMP probe for min/avg/max/jitter

All data flows out through frozen dataclasses so the UI layer can render
results without worrying about mutation.
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Optional

from utils.logger import get_logger

_log = get_logger(__name__)

#: Ping executable — ``ping.exe`` ships with every Windows version.
_PING = "ping"


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run *cmd* and return the completed process.

    Encoding is set to ``utf-8`` with ``errors="replace"`` so non-ASCII
    output (e.g. Chinese locale ``tracert``) does not crash the parser.
    Windows-specific flags suppress the console window.
    """
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )


def _avg(values: list[float]) -> float:
    """Arithmetic mean, returns 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def _jitter(values: list[float]) -> float:
    """Mean absolute deviation from the mean — a simple jitter estimate."""
    if len(values) < 2:
        return 0.0
    mean = _avg(values)
    return _avg([abs(v - mean) for v in values])


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class PingResult:
    """Result of pinging a single host."""

    host: str
    reachable: bool
    packets_sent: int = 0
    packets_received: int = 0
    loss_pct: float = 0.0
    min_ms: float = 0.0
    avg_ms: float = 0.0
    max_ms: float = 0.0
    jitter_ms: float = 0.0
    error: str = ""


@dataclass(frozen=True)
class MultiPingResult:
    """Aggregated result from pinging multiple hosts."""

    results: list[PingResult]
    total_hosts: int = 0
    reachable_hosts: int = 0
    overall_loss_pct: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    jitter_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TracerouteHop:
    """Single hop in a traceroute path."""

    hop: int
    ip: str
    latency_ms: Optional[float]
    timeout: bool = False
    error: str = ""


@dataclass(frozen=True)
class TracerouteResult:
    """Full traceroute to a destination."""

    host: str
    hops: list[TracerouteHop]
    error: str = ""


@dataclass(frozen=True)
class MtuResult:
    """Path-MTU detection result."""

    mtu: int
    method: str
    error: str = ""


@dataclass(frozen=True)
class DnsResolution:
    """Single DNS server resolution measurement."""

    server: str
    resolved: bool
    latency_ms: float = 0.0
    ip_resolved: str = ""
    error: str = ""


@dataclass(frozen=True)
class DnsTestResult:
    """Aggregated DNS resolution test across multiple servers."""

    results: list[DnsResolution]
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    jitter_ms: float = 0.0
    servers_tested: int = 0
    servers_ok: int = 0


@dataclass(frozen=True)
class GatewayResult:
    """Default gateway detection result."""

    gateway: str
    interface: str
    reachable: bool = False
    latency_ms: float = 0.0
    error: str = ""


# --------------------------------------------------------------------- #
# Ping
# --------------------------------------------------------------------- #

def ping_host(
    host: str,
    count: int = 4,
    timeout: int = 3,
) -> PingResult:
    """Ping *host* and return statistics.

    Parameters
    ----------
    host:
        Target hostname or IP address.
    count:
        Number of ICMP echo requests to send.
    timeout:
        Per-packet timeout in seconds.

    Returns
    -------
    PingResult
        Contains reachability, packet counts, loss %, latency stats,
        and jitter.
    """
    try:
        proc = _run(
            [_PING, "-n", str(count), "-w", str(timeout * 1000), host],
            timeout=(timeout * count) + 5,
        )
        output = proc.stdout

        # Parse per-packet lines:  "Reply from 8.8.8.8: bytes=32 time=12ms TTL=117"
        times: list[float] = []
        for line in output.splitlines():
            m = re.search(r"time[=<](\d+)ms", line, re.IGNORECASE)
            if m:
                times.append(float(m.group(1)))

        # Parse summary:  "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)"
        sent = received = 0
        loss_pct = 100.0
        m = re.search(
            r"Sent\s*=\s*(\d+)\s*,\s*Received\s*=\s*(\d+)", output, re.IGNORECASE
        )
        if m:
            sent = int(m.group(1))
            received = int(m.group(2))
            loss_pct = ((sent - received) / sent * 100) if sent > 0 else 0.0

        reachable = received > 0
        return PingResult(
            host=host,
            reachable=reachable,
            packets_sent=sent,
            packets_received=received,
            loss_pct=round(loss_pct, 1),
            min_ms=min(times) if times else 0.0,
            avg_ms=_avg(times),
            max_ms=max(times) if times else 0.0,
            jitter_ms=_jitter(times),
        )
    except subprocess.TimeoutExpired:
        return PingResult(host=host, reachable=False, error="Timed out")
    except Exception as exc:
        _log.warning("Ping failed for %s: %s", host, exc)
        return PingResult(host=host, reachable=False, error=str(exc))


def ping_multi_host(
    hosts: list[str],
    count: int = 4,
    timeout: int = 3,
) -> MultiPingResult:
    """Ping multiple hosts concurrently and aggregate results.

    Parameters
    ----------
    hosts:
        List of hostnames or IPs.
    count:
        ICMP packets per host.
    timeout:
        Per-packet timeout in seconds.

    Returns
    -------
    MultiPingResult
        Per-host results plus overall summary statistics.
    """
    results: list[PingResult] = [PingResult(host=h, reachable=False) for h in hosts]
    errors: list[str] = []
    lock = threading.Lock()

    def _worker(idx: int, host: str) -> None:
        results[idx] = ping_host(host, count=count, timeout=timeout)
        if not results[idx].reachable:
            err = results[idx].error or "unreachable"
            with lock:
                errors.append(f"{host}: {err}")

    threads = [
        threading.Thread(target=_worker, args=(i, h), daemon=True)
        for i, h in enumerate(hosts)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=(timeout * count) + 10)

    reachable = [r for r in results if r.reachable]
    all_latencies = [r.avg_ms for r in reachable]

    return MultiPingResult(
        results=results,
        total_hosts=len(hosts),
        reachable_hosts=len(reachable),
        overall_loss_pct=round(
            sum(r.loss_pct for r in results) / len(results), 1
        ) if results else 0.0,
        avg_latency_ms=_avg(all_latencies),
        min_latency_ms=min(all_latencies) if all_latencies else 0.0,
        max_latency_ms=max(all_latencies) if all_latencies else 0.0,
        jitter_ms=_jitter(all_latencies),
        errors=errors,
    )


def measure_packet_loss(
    host: str = "8.8.8.8",
    count: int = 20,
    timeout: int = 2,
) -> PingResult:
    """Measure packet loss to *host* over *count* packets.

    Uses the same :func:`ping_host` primitive with a larger packet count
    for a statistically meaningful loss measurement.
    """
    return ping_host(host, count=count, timeout=timeout)


# --------------------------------------------------------------------- #
# Traceroute
# --------------------------------------------------------------------- #

def trace_route(host: str, max_hops: int = 30, timeout: int = 3000) -> TracerouteResult:
    """Run ``tracert -d`` and parse hop-by-hop latency.

    Parameters
    ----------
    host:
        Target hostname or IP.
    max_hops:
        Maximum hop count.
    timeout:
        Per-hop timeout in milliseconds (passed to ``tracert -w``).

    Returns
    -------
    TracerouteResult
        List of :class:`TracerouteHop` entries, one per hop.
    """
    try:
        proc = _run(
            ["tracert", "-d", "-w", str(timeout), "-h", str(max_hops), host],
            timeout=(timeout * max_hops / 1000) + 30,
        )
        output = proc.stdout
        hops: list[TracerouteHop] = []

        for line in output.splitlines():
            stripped = line.strip()
            # Skip header / blank lines
            if not stripped or stripped.lower().startswith("tracing route"):
                continue
            if stripped.lower().startswith("over a maximum"):
                continue
            if stripped.lower().startswith("determining"):
                continue

            # Hop lines:  "  1     1 ms     1 ms     1 ms  192.168.1.1"
            # Timeout:    "  5     *        *        *     Request timed out."
            hop_match = re.match(r"^\s*(\d+)\s+(.*)", stripped)
            if not hop_match:
                continue

            hop_num = int(hop_match.group(1))
            rest = hop_match.group(2).strip()

            if "*" in rest and "ms" not in rest.lower():
                hops.append(TracerouteHop(hop=hop_num, ip="", latency_ms=None, timeout=True))
                continue

            times = re.findall(r"(\d+)\s*ms", rest, re.IGNORECASE)
            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", rest)
            ip = ip_match.group(1) if ip_match else ""

            if times:
                avg = _avg([float(t) for t in times])
                hops.append(TracerouteHop(hop=hop_num, ip=ip, latency_ms=round(avg, 1)))
            else:
                hops.append(TracerouteHop(hop=hop_num, ip=ip, latency_ms=None, timeout=True))

        return TracerouteResult(host=host, hops=hops)
    except subprocess.TimeoutExpired:
        return TracerouteResult(host=host, hops=[], error="Traceroute timed out")
    except Exception as exc:
        _log.warning("Traceroute failed for %s: %s", host, exc)
        return TracerouteResult(host=host, hops=[], error=str(exc))


# --------------------------------------------------------------------- #
# MTU detection
# --------------------------------------------------------------------- #

def _ping_mtu_test(host: str, size: int, timeout: int = 2) -> bool:
    """Return ``True`` if a *size*-byte ICMP packet gets through without fragmentation."""
    try:
        proc = _run(
            [_PING, "-f", "-l", str(size), "-n", "1", "-w", str(timeout * 1000), host],
            timeout=timeout + 3,
        )
        return "Reply from" in proc.stdout and "Fragmentation needed" not in proc.stdout
    except Exception:
        return False


def detect_mtu(host: str = "8.8.8.8") -> MtuResult:
    """Discover path MTU via binary search with DF-flag pings.

    Searches the range [576, 1500] using binary search.  Returns the
    largest packet size that does not trigger a *Fragmentation needed*
    response.
    """
    # Binary search: find the largest size that works
    low, high = 576, 1500
    best = 0

    while low <= high:
        mid = (low + high) // 2
        if _ping_mtu_test(host, mid):
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    if best > 0:
        return MtuResult(mtu=best, method="ICMP DF-binary search")

    # Fallback: try known standard MTU values
    for size in [1500, 1492, 1472, 1400, 1280, 576]:
        if _ping_mtu_test(host, size):
            return MtuResult(mtu=size, method="ICMP DF-probe (fallback)")

    return MtuResult(mtu=0, method="Failed — all probes timed out")


# --------------------------------------------------------------------- #
# DNS resolution test
# --------------------------------------------------------------------- #

def test_dns_resolution(
    servers: Optional[list[str]] = None,
) -> DnsTestResult:
    """Test DNS resolution speed across multiple servers.

    Each server is tested by resolving ``google.com`` via a UDP socket
    query to the target DNS server.  Tests run in parallel threads.

    Parameters
    ----------
    servers:
        DNS server IPs to test.  Defaults to a curated list of major
        public resolvers.
    """
    if servers is None:
        servers = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222"]

    results: list[DnsResolution] = []
    lock = threading.Lock()

    def _worker(server: str) -> None:
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            start = __import__("time").perf_counter()
            # Simple DNS query for google.com (A record, IN class)
            query = b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            query += b"\x06google\x03com\x00\x00\x01\x00\x01"
            sock.sendto(query, (server, 53))
            sock.recvfrom(512)
            elapsed = (__import__("time").perf_counter() - start) * 1000
            sock.close()
            with lock:
                results.append(DnsResolution(
                    server=server, resolved=True, latency_ms=round(elapsed, 1),
                ))
        except socket.timeout:
            with lock:
                results.append(DnsResolution(
                    server=server, resolved=False, error="Timeout",
                ))
        except Exception as exc:
            with lock:
                results.append(DnsResolution(
                    server=server, resolved=False, error=str(exc),
                ))

    threads = [threading.Thread(target=_worker, args=(s,), daemon=True) for s in servers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    ok = [r for r in results if r.resolved]
    latencies = [r.latency_ms for r in ok]

    return DnsTestResult(
        results=results,
        avg_ms=round(_avg(latencies), 1),
        min_ms=round(min(latencies), 1) if latencies else 0.0,
        max_ms=round(max(latencies), 1) if latencies else 0.0,
        jitter_ms=round(_jitter(latencies), 1),
        servers_tested=len(servers),
        servers_ok=len(ok),
    )


# --------------------------------------------------------------------- #
# Gateway detection
# --------------------------------------------------------------------- #

def detect_gateway() -> GatewayResult:
    """Detect the default gateway, interface, and reachability.

    Attempts PowerShell first (Get-NetRoute), falls back to psutil.
    If a gateway IP is found, it is pinged once to measure latency.
    """
    gateway = ""
    interface = ""

    # --- Method 1: PowerShell Get-NetRoute ---
    try:
        from network.powershell import run_ps
        script = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
            "Select-Object -First 1 NextHop, InterfaceAlias | "
            "ConvertTo-Json"
        )
        result = run_ps(script, timeout=10)
        if result.stdout:
            import json
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                gateway = data.get("NextHop", "")
                interface = data.get("InterfaceAlias", "")
    except Exception as exc:
        _log.debug("Gateway detection via PowerShell failed: %s", exc)

    # --- Method 2: psutil fallback ---
    if not gateway:
        try:
            import psutil
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            for name, stat in stats.items():
                if stat.isup and name in addrs:
                    for addr in addrs[name]:
                        if addr.family.name == "AF_INET" and addr.address != "127.0.0.1":
                            gateway = addr.address
                            interface = name
                            break
                if gateway:
                    break
        except Exception as exc:
            _log.debug("Gateway detection via psutil failed: %s", exc)

    if not gateway:
        return GatewayResult(
            gateway="—", interface="—", error="No default gateway found",
        )

    # Probe gateway latency
    reachable = False
    latency = 0.0
    try:
        proc = _run([_PING, "-n", "1", "-w", "2000", gateway], timeout=5)
        if "Reply from" in proc.stdout:
            reachable = True
            m = re.search(r"time[=<](\d+)ms", proc.stdout, re.IGNORECASE)
            if m:
                latency = float(m.group(1))
    except Exception:
        pass

    return GatewayResult(
        gateway=gateway,
        interface=interface,
        reachable=reachable,
        latency_ms=latency,
    )


# --------------------------------------------------------------------- #
# Latency measurement
# --------------------------------------------------------------------- #

def measure_latency(host: str = "8.8.8.8", count: int = 10) -> PingResult:
    """Measure latency with multiple ICMP probes.

    Convenience wrapper over :func:`ping_host` with a higher packet
    count for more stable statistics.
    """
    return ping_host(host, count=count, timeout=2)
