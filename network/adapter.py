"""
The adapter data model and category enumeration.

:class:`Adapter` is the single representation of a network adapter used
throughout NetMedic. It is constructed from raw PowerShell dictionaries
and is intentionally tolerant of missing fields so that a partial
NetAdapter row never crashes the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable, Mapping, Optional

from utils.helpers import safe_str, format_speed, format_mac, first_non_blank


class AdapterCategory(str, Enum):
    """Logical categories an adapter can be sorted into.

    The enum subclasses :class:`str` so values render naturally in the
    UI and serialize as plain strings to JSON/CSV.
    """

    PHYSICAL = "Physical"
    VIRTUAL = "Virtual"
    VPN = "VPN"
    GHOST = "Ghost"
    DISABLED = "Disabled"
    UNKNOWN = "Unknown"

    @classmethod
    def from_raw(cls, value: Any) -> "AdapterCategory":
        """Coerce arbitrary input into an :class:`AdapterCategory`.

        Unknown strings fall back to :attr:`UNKNOWN` rather than raising
        so the categorizer is robust to future PowerShell schema drift.
        """
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        text = str(value).strip().capitalize()
        for member in cls:
            if member.value == text:
                return member
        return cls.UNKNOWN


@dataclass
class Adapter:
    """A single Windows network adapter.

    The dataclass keeps every field a plain string (or list/bool) so
    that export to CSV/JSON is trivial. Missing values are stored as
    the sentinel ``"—"`` via :func:`safe_str` to keep the UI consistent.
    """

    # ---- Identity --------------------------------------------------- #
    name: str = "—"
    interface_description: str = "—"
    if_index: str = "—"
    interface_guid: str = "—"
    status: str = "—"

    # ---- Link-layer ------------------------------------------------- #
    mac_address: str = "—"
    link_speed: str = "—"
    media_connection_state: str = "—"

    # ---- Driver / hardware ----------------------------------------- #
    driver_version: str = "—"
    driver_date: str = "—"
    driver_provider: str = "—"
    pnp_device_id: str = "—"
    hardware_ids: list[str] = field(default_factory=list)
    class_guid: str = "—"

    # ---- Flags ------------------------------------------------------ #
    hidden: bool = False
    physical: bool = False
    virtual: bool = False
    enabled: bool = False
    disabled: bool = False

    # ---- IP configuration (populated lazily by Diagnostics) -------- #
    ipv4_addresses: list[str] = field(default_factory=list)
    ipv6_addresses: list[str] = field(default_factory=list)
    default_gateways: list[str] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)
    subnet_prefixes: list[str] = field(default_factory=list)

    # ---- Derived ---------------------------------------------------- #
    category: AdapterCategory = AdapterCategory.UNKNOWN

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_ps(cls, raw: Mapping[str, Any]) -> "Adapter":
        """Build an :class:`Adapter` from a raw PowerShell dictionary.

        The constructor is defensive: every access goes through
        :func:`safe_str` / :func:`format_mac` / :func:`format_speed` so
        that ``None`` / blank / oddly-formatted values degrade to clean
        placeholders rather than raising.
        """
        name = safe_str(raw.get("Name"))
        status = safe_str(raw.get("Status")).lower()
        admin_status = safe_str(raw.get("AdminStatus")).lower()
        enabled = status == "up" or admin_status == "up"
        disabled = status in {"disabled", "disconnected"} or admin_status in {
            "down",
            "disabled",
        }

        # Hardware IDs may arrive as a list, a newline-joined string, or
        # an object containing an "InstanceId" field. Normalize to list.
        hw_ids = _coerce_string_list(raw.get("HardwareIDs") or raw.get("HardwareID"))

        return cls(
            name=name,
            interface_description=safe_str(raw.get("InterfaceDescription")),
            if_index=safe_str(raw.get("ifIndex")),
            interface_guid=safe_str(raw.get("InterfaceGuid")),
            status=safe_str(raw.get("Status")),
            mac_address=format_mac(
                first_non_blank(
                    [raw.get("MacAddress"), raw.get("PermanentAddress")],
                    default="",
                )
            ),
            link_speed=format_speed(raw.get("LinkSpeed")),
            media_connection_state=safe_str(raw.get("MediaConnectionState")),
            driver_version=safe_str(raw.get("DriverVersion")),
            driver_date=safe_str(raw.get("DriverDate")),
            driver_provider=safe_str(raw.get("DriverProvider")),
            pnp_device_id=safe_str(raw.get("PnPDeviceID")),
            hardware_ids=hw_ids,
            class_guid=safe_str(raw.get("ClassGuid")),
            hidden=bool(raw.get("Hidden", False)),
            physical=bool(raw.get("Physical", raw.get("PhysicalAdapter", False))),
            virtual=bool(raw.get("Virtual", False)),
            enabled=enabled,
            disabled=disabled,
        )

    # ------------------------------------------------------------------ #
    # Derived predicates
    # ------------------------------------------------------------------ #
    @property
    def is_connected(self) -> bool:
        """``True`` when the adapter reports an operational Up state."""
        return self.status.lower() == "up"

    @property
    def is_disconnected(self) -> bool:
        """``True`` when the adapter is present but not connected."""
        return self.status.lower() in {"disconnected", "not connected"}

    @property
    def display_speed(self) -> str:
        """Alias for :attr:`link_speed` for export readability."""
        return self.link_speed

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly dictionary.

        Enum values are unwrapped to their string form so downstream
        consumers never need to know about :class:`AdapterCategory`.
        """
        data = asdict(self)
        data["category"] = self.category.value
        return data

    def to_flat_dict(self) -> dict[str, str]:
        """Return a flat ``str -> str`` view, list fields joined by ``, ``.

        Handy for CSV/TXT exports where multi-value cells must collapse
        to a single column.
        """
        data = self.to_dict()
        flat: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, list):
                flat[key] = ", ".join(str(v) for v in value) or "—"
            elif isinstance(value, bool):
                flat[key] = "Yes" if value else "No"
            else:
                flat[key] = str(value)
        return flat


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _coerce_string_list(value: Any) -> list[str]:
    """Normalize PowerShell's varied list encodings to ``list[str]``."""
    if value is None:
        return []
    if isinstance(value, str):
        # PowerShell sometimes joins values with newlines or semicolons.
        parts = value.replace(";", "\n").splitlines()
        return [p.strip() for p in parts if p.strip()]
    if isinstance(value, Iterable):
        out: list[str] = []
        for item in value:
            text = "" if item is None else str(item).strip()
            if text:
                out.append(text)
        return out
    return [str(value).strip()]
