"""
Small, dependency-free helper functions used across NetMedic.

Each helper is pure (no I/O, no globals) so they are trivially testable
and easy to reason about. Anything that grows beyond a few lines or
acquires state belongs in a dedicated module instead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Sequence, TypeVar

T = TypeVar("T")


def safe_str(value: Any, *, default: str = "—") -> str:
    """Return a clean string representation of ``value``.

    ``None``, empty strings, and whitespace-only strings collapse to
    ``default`` so the UI never renders stray ``"None"`` text.

    Examples
    --------
    >>> safe_str(None)
    '—'
    >>> safe_str("  ")
    '—'
    >>> safe_str(42)
    '42'
    """
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def truncate(text: Any, max_length: int, *, ellipsis: str = "…") -> str:
    """Truncate ``text`` to ``max_length`` code points.

    A trailing ``ellipsis`` is appended when truncation occurs. Values
    already shorter than ``max_length`` are returned unchanged (after
    :func:`str` conversion). ``max_length`` values below the length of
    the ellipsis are clamped to that length so we never produce an
    empty/garbled suffix.
    """
    if max_length < 1:
        raise ValueError("max_length must be >= 1")
    text = safe_str(text, default="")
    if len(text) <= max_length:
        return text
    cutoff = max(1, max_length - len(ellipsis))
    return text[:cutoff] + ellipsis


def format_speed(value: Any) -> str:
    """Format a link speed expressed in bits-per-second (``bps``).

    Accepts raw integers, numeric strings (e.g. ``"1000000000"``), the
    sentinel text ``"1 Gbps"`` returned by some PowerShell providers,
    or ``None``. Returns a compact human-readable string such as
    ``"1 Gbps"``, ``"100 Mbps"`` or ``"—"``.
    """
    if value is None:
        return "—"
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "na", "unknown", "-"}:
        return "—"
    # Already-formatted strings are honored verbatim.
    lowered = text.lower()
    for unit in ("gbps", "mbps", "kbps", "bps"):
        if unit in lowered:
            return text
    try:
        bps = int(float(text))
    except (TypeError, ValueError):
        return text
    if bps <= 0:
        return "—"
    units: Sequence[tuple[str, int]] = (
        ("Gbps", 1_000_000_000),
        ("Mbps", 1_000_000),
        ("Kbps", 1_000),
    )
    for label, factor in units:
        if bps >= factor:
            return f"{bps / factor:.0f} {label}"
    return f"{bps} bps"


def format_mac(value: Any, *, separator: str = ":") -> str:
    """Normalize a MAC address to ``XX:XX:XX:XX:XX:XX``.

    Handles the common NetMedic inputs -- already-colon-separated,
    dash-separated, dot-separated (Cisco), bare hex, or ``None``.
    Non-matching input is returned unchanged (best-effort).
    """
    if value is None:
        return "—"
    text = str(value).strip()
    if not text:
        return "—"
    cleaned = (
        text.replace(":", "").replace("-", "").replace(".", "").replace(" ", "")
    )
    if len(cleaned) == 12 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
        pairs = [cleaned[i : i + 2].upper() for i in range(0, 12, 2)]
        return separator.join(pairs)
    return text


def coalesce(*values: Optional[T], default: Optional[T] = None) -> Optional[T]:
    """Return the first non-``None`` value, else ``default``.

    Equivalent in spirit to SQL ``COALESCE`` and useful when pulling
    data from several PowerShell sources with overlapping fields.
    """
    for value in values:
        if value is not None:
            return value
    return default


def first_non_blank(items: Iterable[Any], default: str = "") -> str:
    """Return the first truthy, stripped string in ``items``.

    Used when several PowerShell properties may hold the same data but
    only one is reliably populated for a given driver family.
    """
    for item in items:
        text = "" if item is None else str(item).strip()
        if text:
            return text
    return default


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
