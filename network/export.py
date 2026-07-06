"""
Export scanned adapter data to CSV, JSON, or TXT.

The exporter is deliberately decoupled from both the scanner and the
UI: it consumes a ``list[Adapter]`` plus a :class:`ScanStats`-like
object and writes a file. The format is selected by :class:`ExportFormat`.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional

from .adapter import Adapter
from .scanner import ScanStats
from utils.helpers import now_iso
from utils.logger import get_logger

_log = get_logger(__name__)


class ExportFormat(str, Enum):
    """Supported export destinations.

    Subclassing :class:`str` keeps the enum directly serializable and
    usable as a dictionary key.
    """

    CSV = "csv"
    JSON = "json"
    TXT = "txt"

    @classmethod
    def from_value(cls, value: Any) -> "ExportFormat":
        """Coerce arbitrary input into an :class:`ExportFormat`.

        Unknown values raise :class:`ValueError` since they almost always
        indicate a programming error in the caller.
        """
        if isinstance(value, cls):
            return value
        text = str(value).strip().lower()
        for member in cls:
            if member.value == text:
                return member
        raise ValueError(f"Unknown export format: {value!r}")


#: Columns rendered in CSV / TXT exports, in display order.
EXPORT_COLUMNS: tuple[str, ...] = (
    "name",
    "interface_description",
    "category",
    "status",
    "mac_address",
    "link_speed",
    "driver_version",
    "driver_provider",
    "interface_guid",
    "pnp_device_id",
    "class_guid",
    "ipv4_addresses",
    "ipv6_addresses",
    "default_gateways",
    "dns_servers",
    "subnet_prefixes",
    "hardware_ids",
    "physical",
    "virtual",
    "hidden",
    "enabled",
    "disabled",
)


class Exporter:
    """Write adapter data to disk in one of the supported formats.

    A single instance is stateless beyond its injected
    :class:`ExportFormat`; multiple calls reuse the same writer logic.
    """

    def __init__(
        self,
        fmt: ExportFormat | str = ExportFormat.CSV,
        *,
        columns: Iterable[str] = EXPORT_COLUMNS,
    ) -> None:
        self.format = ExportFormat.from_value(fmt)
        self.columns = tuple(columns)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def export(
        self,
        adapters: list[Adapter],
        path: Path | str,
        *,
        stats: Optional[ScanStats] = None,
    ) -> Path:
        """Serialize ``adapters`` to ``path`` and return the resolved path.

        Parameters
        ----------
        adapters:
            Adapters to export. Pass an empty list to get a header-only
            CSV / empty JSON array.
        path:
            Destination file. Parent directories are created.
        stats:
            Optional :class:`ScanStats` to embed in the JSON/TXT header
            for context.
        """
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        if self.format is ExportFormat.JSON:
            payload = self._build_json(adapters, stats)
            target.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        elif self.format is ExportFormat.CSV:
            target.write_text(
                self._build_csv(adapters), encoding="utf-8", newline=""
            )
        else:  # TXT
            target.write_text(
                self._build_txt(adapters, stats), encoding="utf-8"
            )

        _log.info("Exported %d adapters to %s (%s).", len(adapters), target, self.format.value)
        return target

    # ------------------------------------------------------------------ #
    # Builders
    # ------------------------------------------------------------------ #
    def _build_csv(self, adapters: list[Adapter]) -> str:
        """Return CSV text with one row per adapter."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(self.columns)
        for adapter in adapters:
            flat = adapter.to_flat_dict()
            writer.writerow([flat.get(col, "") for col in self.columns])
        return buffer.getvalue()

    def _build_json(
        self,
        adapters: list[Adapter],
        stats: Optional[ScanStats],
    ) -> dict[str, Any]:
        """Return a JSON-serializable dictionary with metadata + rows."""
        return {
            "generated_at": now_iso(),
            "stats": asdict(stats) if stats else None,
            "count": len(adapters),
            "adapters": [adapter.to_dict() for adapter in adapters],
        }

    def _build_txt(
        self,
        adapters: list[Adapter],
        stats: Optional[ScanStats],
    ) -> str:
        """Return a human-readable plain-text report."""
        lines: list[str] = []
        lines.append("NetMedic Adapter Report")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total adapters: {len(adapters)}")
        if stats:
            lines.append(
                "Breakdown: "
                f"physical={stats.physical} virtual={stats.virtual} "
                f"vpn={stats.vpn} ghost={stats.ghost} "
                f"disabled={stats.disabled} unknown={stats.unknown}"
            )
        lines.append("")
        for adapter in adapters:
            lines.append("-" * 60)
            flat = adapter.to_flat_dict()
            for col in self.columns:
                label = col.replace("_", " ").capitalize()
                lines.append(f"{label:<22}: {flat.get(col, '')}")
            lines.append("")
        return "\n".join(lines) + "\n"
