"""
Adapter categorization rules.

The categorizer is a *pure* component: it consumes a populated
:class:`Adapter` and assigns exactly one :class:`AdapterCategory`. It
performs no I/O of its own and may be unit-tested in isolation.

Priority order matters and is documented in :meth:`Categorizer.categorize`.
"""

from __future__ import annotations

from typing import Iterable

from .adapter import Adapter, AdapterCategory
from utils.helpers import safe_str

# --------------------------------------------------------------------- #
# Detection vocabularies.
#
# Each tuple is matched **case-insensitively** against both the adapter
# name and its interface description. Adding a new product is a one-line
# change here -- no other code path needs to know about it.
# --------------------------------------------------------------------- #

#: Product / keyword signatures that indicate a VPN tunnel adapter.
VPN_KEYWORDS: tuple[str, ...] = (
    "wireguard",
    "wintun",
    "tap",            # OpenVPN TAP/TAP-Windows
    "openvpn",
    "cloudflare warp",
    "warp",
    "zerotier",
    "tailscale",
    "softether",
    "cisco anyconnect",
    "anyconnect",
    "fortinet",
    "forticlient",
    "openconnect",
    "vpn",
)

#: Signatures for hypervisor / container / loopback virtual NICs.
VIRTUAL_KEYWORDS: tuple[str, ...] = (
    "hyper-v",
    "virtual switch",
    "vmware",
    "vmnet",
    "virtualbox",
    "host-only",
    "docker",
    "vethernet",
    "wsl",
    "hyper-v virtual ethernet",
    "npcap loopback",
    "npcap",
    "microsoft km-test",
    "km-test",
    "loopback",
    "virtual",
)


class Categorizer:
    """Assigns a single :class:`AdapterCategory` to each adapter.

    The class is stateless; an instance exists only so callers can
    subclass/monkey-patch individual rules for testing.
    """

    def __init__(
        self,
        *,
        vpn_keywords: Iterable[str] = VPN_KEYWORDS,
        virtual_keywords: Iterable[str] = VIRTUAL_KEYWORDS,
    ) -> None:
        self._vpn_keywords = tuple(k.lower() for k in vpn_keywords)
        self._virtual_keywords = tuple(k.lower() for k in virtual_keywords)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def categorize(self, adapter: Adapter) -> AdapterCategory:
        """Return the best category for ``adapter``.

        Priority (first match wins):

        1. **Ghost**  -- adapter present with no hardware backing, or
           flagged ghost by the scanner.
        2. **VPN**    -- name/description matches a VPN product.
        3. **Virtual**-- name/description matches a virtual NIC family.
        4. **Physical** -- adapter reports itself as a real NIC.
        5. **Disabled** -- administratively down.
        6. **Unknown** -- none of the above.
        """
        # (1) Ghost takes precedence: a ghost adapter is the most
        # actionable signal and should not be masked by a name match.
        if self._is_ghost(adapter):
            return AdapterCategory.GHOST

        haystack = self._haystack(adapter)

        # (2) VPN
        if self._matches(haystack, self._vpn_keywords):
            return AdapterCategory.VPN

        # (3) Virtual
        if self._matches(haystack, self._virtual_keywords):
            return AdapterCategory.VIRTUAL

        # (4) Physical -- trust the driver flag when available.
        if adapter.physical:
            return AdapterCategory.PHYSICAL

        # (5) Disabled is informational, not a hardware classification.
        if adapter.disabled:
            return AdapterCategory.DISABLED

        # (6) Nothing recognizable.
        return AdapterCategory.UNKNOWN

    # ------------------------------------------------------------------ #
    # Rule helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _haystack(adapter: Adapter) -> str:
        """Lower-cased concatenation of name + description for matching."""
        name = safe_str(adapter.name, default="").lower()
        desc = safe_str(adapter.interface_description, default="").lower()
        return f"{name} {desc}"

    @staticmethod
    def _matches(haystack: str, keywords: tuple[str, ...]) -> bool:
        """Return ``True`` when any keyword is a substring of ``haystack``."""
        return any(kw in haystack for kw in keywords)

    @staticmethod
    def _is_ghost(adapter: Adapter) -> bool:
        """Heuristic: present-but-empty adapters are treated as ghosts.

        A ghost adapter typically reports an interface description that
        begins with "WAN Miniport" or has no PnP device id / no hardware
        ids despite being enumerated. We also treat adapters whose status
        is empty *and* whose MAC is unknown as ghosts.
        """
        desc = safe_str(adapter.interface_description, default="").lower()
        name = safe_str(adapter.name, default="").lower()
        pnp = safe_str(adapter.pnp_device_id, default="").strip()
        hw_ids = adapter.hardware_ids
        mac_unknown = adapter.mac_address in {"—", "", None}

        if desc.startswith("wan miniport"):
            return True
        if name.startswith("isatap") or name.startswith("teredo"):
            return True
        if not pnp and not hw_ids and mac_unknown:
            return True
        return False
