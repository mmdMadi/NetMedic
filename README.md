# NetMedic

> A professional **Windows Network Diagnostics & Repair Toolkit** built as a Textual
> TUI. NetMedic inspects every network adapter on the machine, detects
> inactive / virtual / VPN / ghost adapters, provides safe
> maintenance tools, and displays a live dashboard with internet health
> scoring — **without ever removing hardware automatically**.

NetMedic is built to be:

- **Safe** — every destructive operation requires explicit confirmation.
- **Readable** — dark, layered UI with dashboard, table, details, and status bar.
- **Modular** — clean separation between `network/`, `ui/`, and `utils/`.
- **Robust** — every PowerShell call is wrapped, errors are surfaced
  as friendly dialogs, and the app never crashes on a partial failure.

---

## ✨ Features

### Dashboard
A live, at-a-glance summary of the host:

- **Internet Status** — real-time connectivity check (Connected / No Internet / No DNS)
- **Local IP** — primary local IPv4 address
- **Public IP** — public-facing IPv4 address
- **Windows Version** — detected OS version
- **Connected Adapter** — name of the active network adapter
- **DNS Server** — primary DNS server address
- **Health Score** — 0–100 score based on internet, DNS, gateway, adapter, packet loss, and MTU
- Administrator / elevation detection banner
- Total adapters, physical, virtual, VPN, ghost, and disabled counts

### Adapter Scanner
Reads **all** network adapters via PowerShell `Get-NetAdapter -IncludeHidden`
and collects, per adapter:

| Group | Fields |
|-------|--------|
| Identity | Name, Interface Description, ifIndex, Interface GUID, Status |
| Link layer | MAC Address, Link Speed, Media Connection State |
| Driver | Driver Version, Driver Date, Driver Provider |
| Hardware | PNP Device ID, Hardware IDs, Class GUID |
| Flags | Hidden, Physical, Virtual, Enabled, Disabled |

Adapters are categorized automatically into **Physical / Virtual / VPN /
Ghost / Disabled / Unknown**.

**VPN adapters** are recognized by name/description keywords:
WireGuard, Wintun, TAP, OpenVPN, Cloudflare WARP, ZeroTier, Tailscale,
SoftEther, Cisco AnyConnect, Fortinet, OpenConnect.

**Virtual adapters** are recognized by keywords:
Hyper-V, VMware, VirtualBox, Docker, WSL, Npcap Loopback, Microsoft KM-TEST.

**Ghost adapters** are detected heuristically (e.g. WAN Miniport, ISATAP,
adapters with no PnP device ID / hardware IDs / MAC).

### Detail View
Press **Enter** on any row to open the details panel, showing everything
NetMedic knows about the adapter — including IP addresses, gateways, DNS,
IPv4/IPv6, hardware IDs, registry class GUID, and driver information.

### Filters
Quickly narrow the table by category:

`All · Physical · VPN · Virtual · Ghost · Disabled · Connected · Disconnected`

### Export
Export the current result set to **CSV**, **JSON**, or **TXT** (written to
`exports/` next to the executable).

### Logging
Every operation is logged to `logs/netmedic-YYYY-MM-DD.log`.

### Configuration
`config.json` controls: `theme`, `scan_timeout`, `logging`,
`ignored_adapters`.

---

## 📸 Screenshots

> Place screenshots here.

```
docs/
└── screenshots/
    ├── dashboard.png
    ├── table.png
    └── details.png
```

---

## ✅ Requirements

- **OS**: Windows 10 / 11 (PowerShell `Get-NetAdapter` is required).
- **Python**: 3.12 or newer.
- **Terminal**: Windows Terminal, CMD, or PowerShell.
- **Dependencies**:
  - [`textual`](https://textual.textualize.io/) — TUI framework
  - [`psutil`](https://github.com/giampaolo/psutil) — system/network info
  - [`requests`](https://requests.readthedocs.io/) — HTTP for public IP lookup
- **Optional**: Administrator privileges — required only for the
  *Disable* maintenance action. Detection, scanning, and export work
  without elevation.

---

## 📦 Installation

```powershell
# 1. Clone or copy the NetMedic folder somewhere convenient.
cd D:\project\NetMedic

# 2. (Recommended) create and activate a virtual environment.
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install the single runtime dependency.
pip install -r requirements.txt
```

---

## 🚀 Usage

```powershell
# From the project root:
python app.py

# Print the version and exit:
python app.py --version
```

The app launches, performs an initial scan, and shows the dashboard.
Use the keyboard shortcuts below to drive it.

> Tip: run NetMedic **as Administrator** if you want to use the *Disable*
> maintenance action. Everything else works as a standard user.

---

## ⌨️ Keyboard Shortcuts

| Key     | Action |
|---------|--------|
| `R`     | Scan adapters |
| `F`     | Open the filter dialog |
| `Space` | Select / deselect the focused row |
| `Ctrl+A`| Select all visible adapters |
| `Ctrl+D`| Deselect all |
| `Enter` | Open the details panel for the focused adapter |
| `E`     | Export results (CSV / JSON / TXT) |
| `I`     | Ignore the selected adapter(s) |
| `D`     | Disable the selected adapter (admin only) |
| `X`     | Remove the selected adapter (admin only, double-confirm) |
| `?`     | Show keyboard shortcuts |
| `Q`     | Quit |

---

## 🗂️ Project Structure

```
NetMedic/
├── app.py                  # Textual App entry point + keyboard actions
├── config.py               # Config dataclass + JSON load/save
├── requirements.txt        # textual, psutil, requests
├── README.md               # this file
├── theme.tcss              # NetMedic dark theme (TCSS)
├── config.json             # user-editable runtime configuration
├── ui/                     # Textual widgets and modal dialogs
│   ├── __init__.py
│   ├── dashboard.py        # System summary + info cards + health score
│   ├── adapter_table.py    # Searchable/filterable/selectable table
│   ├── details.py          # Per-adapter details panel
│   ├── status.py           # Status bar + spinner
│   ├── actions_bar.py      # Quick-action toolbar
│   └── dialogs.py          # Confirm / Filter / Export / Error dialogs
├── network/                # Network domain logic (UI-free)
│   ├── __init__.py
│   ├── powershell.py       # Wrapped, UTF-8, timeout-safe PowerShell runner
│   ├── adapter.py          # Adapter dataclass + AdapterCategory enum
│   ├── categorizer.py      # Pure categorization rules
│   ├── scanner.py          # AdapterScanner + ScanResult/ScanStats
│   ├── diagnostics.py      # IP / DNS / gateway enrichment
│   ├── export.py           # CSV / JSON / TXT exporter
│   ├── internet.py         # Internet connectivity check
│   ├── local_info.py       # Local IP, adapters, DNS (psutil-based)
│   ├── public_info.py      # Public IP, ISP, geo lookup
│   └── health.py           # Health score computation (0–100)
├── utils/                  # Cross-cutting helpers
│   ├── __init__.py
│   ├── admin.py            # Administrator / elevation detection
│   ├── logger.py           # Daily file logging + stderr mirror
│   ├── helpers.py          # Pure formatting helpers
│   └── storage.py          # Paths + atomic JSON persistence
└── logs/                   # Daily log files (auto-created)
```

### Layering rules

- `utils/` depends on nothing inside NetMedic.
- `network/` depends only on `utils/` and `config`.
- `ui/` depends on `network/` and `utils/`, never the other way around.
- `app.py` wires all three layers together.

This makes the domain logic (`network/`) independently testable and the
UI swappable without touching PowerShell code.

---

## ⚙️ Configuration (`config.json`)

```json
{
  "theme": "netmedic-dark",
  "scan_timeout": 60,
  "logging": true,
  "ignored_adapters": []
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme` | string | `netmedic-dark` | Theme name (must match a TCSS theme). |
| `scan_timeout` | int | `60` | Per-PowerShell-call timeout in seconds (clamped 5–600). |
| `logging` | bool | `true` | When `false`, no log files are written. |
| `ignored_adapters` | string[] | `[]` | Adapter names hidden from scans. Editable from the UI (press `I`). |

Invalid values are replaced with their defaults and logged; the app
never fails to start because of a malformed `config.json`.

---

## 🔒 Safety & Design Principles

1. **Never remove hardware automatically.** NetMedic's maintenance
   actions are limited to *disable* — never uninstall or delete.
2. **Explicit confirmation for every destructive action.** Each is
   gated behind a modal dialog with a distinct "Confirm" step.
3. **Admin-only maintenance.** The *Disable* action refuses to run
   without elevation and shows a friendly explanation.
4. **Failures are surfaced, never fatal.** Every PowerShell call is
   wrapped; errors become a dialog plus a log line, not a crash.

---

## 🧪 Code Quality

- Type hints throughout; mypy-friendly.
- Dataclasses for all DTOs; enums for categories/states/formats.
- No module-level mutable globals; no magic numbers (named constants).
- PEP 8 layout; comprehensive docstrings.
- Each module is small and single-purpose.

---

## 📄 License

Released under the **MIT License**.

```
MIT License

Copyright (c) 2026 NetMedic Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```
