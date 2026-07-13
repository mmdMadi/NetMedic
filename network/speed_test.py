"""
Internet speed test service.

Measures download speed, upload speed, ping latency, and jitter using
raw HTTP streaming.  No external dependencies beyond ``requests`` (already
a project dependency).

Every function is synchronous and designed to be called from a background
thread.  Cancellation is supported via a :class:`threading.Event`.

Design
------

**Download test**: Streams a fixed-size file from a reliable CDN endpoint,
reading chunks and measuring throughput in real time.

**Upload test**: POSTs random data to an HTTP echo endpoint, measuring
outbound throughput.

**Ping / Jitter**: ICMP-based, reusing :func:`network.diagnostics_internet.ping_host`.

Progress is reported via an optional callback so the UI can update a
progress bar and status label during the test.
"""

from __future__ import annotations

import random
import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import requests

from utils.logger import get_logger

_log = get_logger(__name__)


# --------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------- #

#: Default download test size in megabytes.
DEFAULT_DOWNLOAD_MB: int = 10
#: Default upload test size in megabytes.
DEFAULT_UPLOAD_MB: int = 10
#: Per-request timeout (seconds).
REQUEST_TIMEOUT: int = 30
#: Number of ICMP pings for latency measurement.
PING_COUNT: int = 10
#: ICMP ping timeout (seconds).
PING_TIMEOUT: int = 2

#: Download test endpoint — a 10 MB file served by Cloudflare.
#: Falls back to Tele2 if Cloudflare is unreachable.
DOWNLOAD_URLS: list[str] = [
    "http://speedtest.tele2.net/10MB.zip",
    "http://speedtest.tele2.net/1MB.zip",
]

#: Upload test endpoint — HTTPBin echo service (accepts any POST body).
UPLOAD_URL: str = "https://httpbin.org/post"

#: Progress callback signature: ``(phase, current_bytes, total_bytes) -> None``
ProgressCallback = Callable[[str, int, int], None]


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class SpeedTestResult:
    """Complete speed test result."""

    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    jitter_ms: float = 0.0
    download_bytes: int = 0
    download_duration_s: float = 0.0
    upload_bytes: int = 0
    upload_duration_s: float = 0.0
    server: str = ""
    error: str = ""
    cancelled: bool = False


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def _bytes_to_mbps(bytes_transferred: int, elapsed_seconds: float) -> float:
    """Convert bytes and seconds to megabits per second."""
    if elapsed_seconds <= 0:
        return 0.0
    bits = bytes_transferred * 8
    return bits / (elapsed_seconds * 1_000_000)


def _generate_payload(size_mb: int) -> bytes:
    """Generate random bytes for upload testing."""
    return bytes(random.getrandbits(8) for _ in range(size_mb * 1024 * 1024))


# --------------------------------------------------------------------- #
# Download test
# --------------------------------------------------------------------- #

def test_download(
    url: Optional[str] = None,
    size_mb: int = DEFAULT_DOWNLOAD_MB,
    timeout: int = REQUEST_TIMEOUT,
    cancel_event: Optional[threading.Event] = None,
    progress: Optional[ProgressCallback] = None,
) -> tuple[float, int, float, str]:
    """Stream a download and measure throughput.

    Parameters
    ----------
    url:
        URL to download.  If ``None``, tries :data:`DOWNLOAD_URLS` in order.
    size_mb:
        Expected download size in MB (used for progress reporting).
    timeout:
        Per-connection timeout in seconds.
    cancel_event:
        If set, the test aborts early.
    progress:
        Callback invoked with ``(phase, current_bytes, total_bytes)``.

    Returns
    -------
    tuple[float, int, float, str]
        ``(speed_mbps, bytes_downloaded, duration_seconds, server_url)``
    """
    urls = [url] if url else DOWNLOAD_URLS
    total_bytes = size_mb * 1024 * 1024

    for test_url in urls:
        if cancel_event and cancel_event.is_set():
            return (0.0, 0, 0.0, "")

        try:
            _log.info("Speed test: downloading from %s", test_url)
            start = time.perf_counter()
            downloaded = 0

            response = requests.get(
                test_url,
                timeout=timeout,
                stream=True,
                headers={"User-Agent": "NetMedic/1.0"},
            )
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=65536):
                if cancel_event and cancel_event.is_set():
                    response.close()
                    return (0.0, downloaded, time.perf_counter() - start, test_url)

                downloaded += len(chunk)
                if progress:
                    progress("download", downloaded, total_bytes)

            elapsed = time.perf_counter() - start
            speed = _bytes_to_mbps(downloaded, elapsed)

            _log.info(
                "Speed test: downloaded %d bytes in %.1fs = %.1f Mbps",
                downloaded, elapsed, speed,
            )
            return (speed, downloaded, elapsed, test_url)

        except requests.RequestException as exc:
            _log.warning("Download test failed for %s: %s", test_url, exc)
            continue
        except Exception as exc:
            _log.warning("Download test error for %s: %s", test_url, exc)
            continue

    return (0.0, 0, 0.0, "")


# --------------------------------------------------------------------- #
# Upload test
# --------------------------------------------------------------------- #

def test_upload(
    url: Optional[str] = None,
    size_mb: int = DEFAULT_UPLOAD_MB,
    timeout: int = REQUEST_TIMEOUT,
    cancel_event: Optional[threading.Event] = None,
    progress: Optional[ProgressCallback] = None,
) -> tuple[float, int, float]:
    """Upload random data and measure throughput.

    Parameters
    ----------
    url:
        Endpoint to POST to.  Defaults to :data:`UPLOAD_URL`.
    size_mb:
        Payload size in MB.
    timeout:
        Per-connection timeout in seconds.
    cancel_event:
        If set, the test aborts early.
    progress:
        Callback invoked with ``(phase, current_bytes, total_bytes)``.

    Returns
    -------
    tuple[float, int, float]
        ``(speed_mbps, bytes_uploaded, duration_seconds)``
    """
    upload_url = url or UPLOAD_URL
    total_bytes = size_mb * 1024 * 1024

    if cancel_event and cancel_event.is_set():
        return (0.0, 0, 0.0)

    try:
        _log.info("Speed test: uploading %d MB to %s", size_mb, upload_url)
        payload = _generate_payload(size_mb)

        if progress:
            progress("upload_prepare", 0, total_bytes)

        start = time.perf_counter()
        response = requests.post(
            upload_url,
            data=payload,
            timeout=timeout,
            headers={"User-Agent": "NetMedic/1.0"},
        )
        response.raise_for_status()
        elapsed = time.perf_counter() - start

        uploaded = len(payload)
        speed = _bytes_to_mbps(uploaded, elapsed)

        _log.info(
            "Speed test: uploaded %d bytes in %.1fs = %.1f Mbps",
            uploaded, elapsed, speed,
        )
        return (speed, uploaded, elapsed)

    except requests.RequestException as exc:
        _log.warning("Upload test failed: %s", exc)
        return (0.0, 0, 0.0)
    except Exception as exc:
        _log.warning("Upload test error: %s", exc)
        return (0.0, 0, 0.0)


# --------------------------------------------------------------------- #
# Ping / Jitter
# --------------------------------------------------------------------- #

def test_ping_jitter(
    host: str = "8.8.8.8",
    count: int = PING_COUNT,
    timeout: int = PING_TIMEOUT,
) -> tuple[float, float]:
    """Measure ping latency and jitter via ICMP.

    Returns
    -------
    tuple[float, float]
        ``(average_ms, jitter_ms)``
    """
    from network.diagnostics_internet import ping_host

    result = ping_host(host, count=count, timeout=timeout)
    return (result.avg_ms, result.jitter_ms)


# --------------------------------------------------------------------- #
# Full speed test
# --------------------------------------------------------------------- #

def run_speed_test(
    download_mb: int = DEFAULT_DOWNLOAD_MB,
    upload_mb: int = DEFAULT_UPLOAD_MB,
    cancel_event: Optional[threading.Event] = None,
    progress: Optional[ProgressCallback] = None,
) -> SpeedTestResult:
    """Run a complete speed test: ping, download, upload.

    Parameters
    ----------
    download_mb:
        Download test size in megabytes.
    upload_mb:
        Upload test size in megabytes.
    cancel_event:
        Set this to abort the test early.
    progress:
        Callback for progress updates.

    Returns
    -------
    SpeedTestResult
        Complete results with speeds, latency, jitter, and metadata.
    """
    _log.info(
        "Starting speed test (download=%d MB, upload=%d MB)",
        download_mb, upload_mb,
    )

    # --- Ping / Jitter ---
    if progress:
        progress("ping", 0, 0)
    ping_ms, jitter_ms = test_ping_jitter()

    if cancel_event and cancel_event.is_set():
        return SpeedTestResult(
            ping_ms=ping_ms, jitter_ms=jitter_ms, cancelled=True,
        )

    # --- Download ---
    if progress:
        progress("download", 0, download_mb * 1024 * 1024)
    dl_speed, dl_bytes, dl_duration, server = test_download(
        size_mb=download_mb,
        cancel_event=cancel_event,
        progress=progress,
    )

    if cancel_event and cancel_event.is_set():
        return SpeedTestResult(
            download_mbps=dl_speed,
            download_bytes=dl_bytes,
            download_duration_s=dl_duration,
            server=server,
            ping_ms=ping_ms,
            jitter_ms=jitter_ms,
            cancelled=True,
        )

    # --- Upload ---
    if progress:
        progress("upload", 0, upload_mb * 1024 * 1024)
    ul_speed, ul_bytes, ul_duration = test_upload(
        size_mb=upload_mb,
        cancel_event=cancel_event,
        progress=progress,
    )

    if cancel_event and cancel_event.is_set():
        return SpeedTestResult(
            download_mbps=dl_speed,
            download_bytes=dl_bytes,
            download_duration_s=dl_duration,
            upload_mbps=ul_speed,
            upload_bytes=ul_bytes,
            upload_duration_s=ul_duration,
            server=server,
            ping_ms=ping_ms,
            jitter_ms=jitter_ms,
            cancelled=True,
        )

    result = SpeedTestResult(
        download_mbps=round(dl_speed, 2),
        upload_mbps=round(ul_speed, 2),
        ping_ms=round(ping_ms, 1),
        jitter_ms=round(jitter_ms, 1),
        download_bytes=dl_bytes,
        download_duration_s=round(dl_duration, 2),
        upload_bytes=ul_bytes,
        upload_duration_s=round(ul_duration, 2),
        server=server,
    )

    _log.info(
        "Speed test complete: ↓%.1f Mbps  ↑%.1f Mbps  ping %.1f ms  jitter %.1f ms",
        result.download_mbps,
        result.upload_mbps,
        result.ping_ms,
        result.jitter_ms,
    )

    return result
