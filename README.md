# NetMedic

> A professional **Windows Network Diagnostics & Repair Toolkit** built as a Textual
> TUI. NetMedic inspects every network adapter on the machine, detects
> inactive / virtual / VPN / ghost adapters, provides safe
> maintenance tools, and displays a live dashboard with internet health
> scoring — **without ever removing hardware automatically**.

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/mmdMadi/NetMedic)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg)](https://www.microsoft.com/)

NetMedic is built to be:

- **Safe** — every destructive operation requires explicit confirmation.
- **Readable** — dark, layered UI with dashboard, table, details, and status bar.
- **Modular** — clean separation between `network/`, `ui/`, and `utils/`.
- **Robust** — every PowerShell call is wrapped, errors are surfaced
  as friendly dialogs, and the app never crashes on a partial failure.
- **Portable** — single executable, no installation required.

---

## Features

### Dashboard

A live, at-a-glance summary of the host:

- **Internet Status** — real-time connectivity check (Connected / No Internet / No DNS)
- **Local IP** — primary local IPv4 address
- **Public IP** — public-facing IPv4 address
- **Windows Version** — detected OS version
- **Connected Adapter** — name of the active network adapter
- **DNS Server** — primary DNS server address with provider name
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

- **VPN adapters** recognized: WireGuard, Wintun, TAP, OpenVPN, Cloudflare WARP, ZeroTier, Tailscale, SoftEther, Cisco AnyConnect, Fortinet, OpenConnect.
- **Virtual adapters** recognized: Hyper-V, VMware, VirtualBox, Docker, WSL, Npcap Loopback, Microsoft KM-TEST.
- **Ghost adapters** detected heuristically (WAN Miniport, ISATAP, adapters with no PnP device ID / hardware IDs / MAC).

### Internet Diagnostics (`T`)

Run comprehensive network diagnostics with live results:

- **Ping** — single-host ICMP ping with min/avg/max/jitter
- **Multi-Host Ping** — concurrent ping to 4 DNS servers (8.8.8.8, 1.1.1.1, 9.9.9.9, 208.67.222.222)
- **Packet Loss Test** — 20-packet test with quality assessment (Good/Degraded/Poor)
- **Traceroute** — hop-by-hop route with latency table
- **MTU Detection** — binary search path-MTU discovery
- **DNS Resolution** — parallel resolution across 4 public resolvers
- **Gateway Detection** — default gateway with reachability probe

### Internet Speed Test (`S`)

Measure network performance with progress tracking:

- **Download Speed** — streaming HTTP from CDN (10 MB)
- **Upload Speed** — POST to echo endpoint (10 MB)
- **Ping & Jitter** — 10 ICMP probes
- Real-time progress bar with phase indicators
- Cancellation support
- Color-coded results (green > 100 Mbps, yellow > 10, red < 10)

### DNS Tools (`N`)

Manage DNS configuration with one click:

- **Current DNS** — display active adapter's DNS servers and mode (DHCP/Static)
- **7 Presets** — Automatic, Cloudflare, Google, Quad9, OpenDNS, Shecan, Electro
- **Flush DNS** — `ipconfig /flushdns`
- **Register DNS** — `ipconfig /registerdns`
- **Reset Network Stack** — `netsh int ip reset`

### Network Repair (`U`)

One-click sequential repair with live progress:

1. Flush DNS cache (`ipconfig /flushdns`)
2. Release DHCP lease (`ipconfig /release`)
3. Renew DHCP lease (`ipconfig /renew`)
4. Reset Winsock catalog (`netsh winsock reset`)
5. Reset TCP/IP stack (`netsh int ip reset`)
6. Reset IPv4 interface (`netsh int ipv4 reset`)
7. Reset IPv6 interface (`netsh int ipv6 reset`)

- Step-by-step progress with pass/fail indicators
- Admin detection for elevated steps
- Restart warning when Winsock/TCP/IP resets succeed

### Adapter Manager (`A`)

View and manage all network adapters:

- **Adapter List** — all adapters with status icons (● up, ○ down)
- **Detail Panel** — IPv4, IPv6, Gateway, MAC, Speed, MTU, Driver, Provider
- **Enable** — enable a disabled adapter
- **Disable** — disable an enabled adapter
- **Restart** — disable then enable cycle

### Public Network Information (`P`)

Display public-facing network identity:

- **Public IPv4** — from ipify.org
- **Public IPv6** — from api64.ipify.org
- **ISP / ASN** — from ipapi.co
- **Country, Region, City** — geolocation data
- **Timezone** — from ipapi.co

### Diagnostic Report (`G`)

Generate comprehensive diagnostic reports:

- **System Info** — hostname, username, Windows, Python, CPU, RAM
- **Network Status** — internet, IPs, DNS, gateway, adapter
- **Adapter Summary** — total, physical, virtual, VPN, ghost, disabled
- **Diagnostics** — ping, packet loss, MTU, DNS resolution
- **Warnings** — auto-detected issues
- **Export** — Copy to Clipboard, Save TXT, Save HTML

### Internet Health Score (`H`)

Comprehensive health assessment from 0 to 100:

| Check | Weight | Threshold |
|-------|--------|-----------|
| Internet Reachable | 30 pts | TCP + HTTP probe |
| DNS Working | 20 pts | DNS resolution via HTTP |
| Gateway OK | 15 pts | Default gateway present |
| Adapter Connected | 15 pts | Primary adapter Up |
| Low Packet Loss | 10 pts | ≤ 2% threshold |
| MTU OK | 10 pts | ≥ 1280 (IPv6 minimum) |

- Grade: Excellent (≥90) / Good (≥70) / Fair (≥50) / Poor (≥30) / Critical (<30)
- Warning explanations for failed checks
- Network summary with all signals

### Log Viewer (`L`)

Browse application logs:

- **File List** — all log files with size and date
- **Content Viewer** — scrollable, color-coded log entries
- **Color Levels** — ERROR (red), WARNING (yellow), INFO (dim)
- **Automatic Cleanup** — logs older than 30 days are deleted on startup

### Export

Export adapter data to:

- **CSV** — comma-separated values
- **JSON** — structured data
- **TXT** — human-readable table

Written to `exports/` folder.

---

## Requirements

- **OS**: Windows 10 / 11 (PowerShell `Get-NetAdapter` is required).
- **Python**: 3.12 or newer.
- **Terminal**: Windows Terminal, CMD, or PowerShell.
- **Dependencies**:
  - [`textual`](https://textual.textualize.io/) — TUI framework
  - [`psutil`](https://github.com/giampaolo/psutil) — system/network info
  - [`requests`](https://requests.readthedocs.io/) — HTTP for public IP lookup
- **Optional**: Administrator privileges — required for Disable, Restart,
  and Network Repair actions. All other features work without elevation.

---

## Installation

### From Source

```powershell
# 1. Clone the repository
git clone https://github.com/mmdMadi/NetMedic.git
cd NetMedic

# 2. (Recommended) create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### Portable Executable

Download the latest release from [Releases](https://github.com/mmdMadi/NetMedic/releases)
or build it yourself:

```powershell
# Build the executable
python build.py

# The executable is at: dist/NetMedic.exe
```

---

## Usage

```powershell
# Run from source
python app.py

# Print version
python app.py --version

# Build portable executable
python build.py

# Build with cleanup and verification
python build.py --clean --verify
```

---

## Keyboard Shortcuts

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `R` | Scan adapters | `A` | Adapter Manager |
| `T` | Internet Diagnostics | `P` | Public Network Info |
| `S` | Internet Speed Test | `G` | Diagnostic Report |
| `N` | DNS Tools | `H` | Internet Health Score |
| `U` | Network Repair | `L` | Log Viewer |
| `F` | Filter adapters | `E` | Export results |
| `I` | Ignore adapter(s) | `D` | Disable adapter |
| `X` | Remove adapter | `?` | Show shortcuts |
| `Space` | Select/deselect row | `Q` | Quit |
| `Ctrl+A` | Select all | `Ctrl+D` | Deselect all |
| `Enter` | Open details | | |

---

## Project Structure

```
NetMedic/
├── app.py                  # Textual App entry point + keyboard actions
├── config.py               # Config dataclass + JSON load/save
├── config.json             # User-editable runtime configuration
├── requirements.txt        # Runtime dependencies
├── theme.tcss              # NetMedic dark theme (TCSS)
├── netmedic.spec           # PyInstaller spec for building
├── build.py                # Build script for packaging
├── __init__.py             # Package version (1.2.0)
│
├── ui/                     # Textual widgets and modal dialogs (13 screens)
│   ├── dashboard.py        # System summary + info cards + health score
│   ├── adapter_table.py    # Searchable/filterable/selectable table
│   ├── details.py          # Per-adapter details panel
│   ├── status.py           # Status bar + spinner
│   ├── actions_bar.py      # Quick-action toolbar
│   ├── dialogs.py          # Confirm / Filter / Export / Error dialogs
│   ├── diagnostics.py      # Internet Diagnostics screen
│   ├── speed_test.py       # Speed Test screen
│   ├── dns_tools.py        # DNS Tools screen
│   ├── repair.py           # Network Repair screen
│   ├── adapter_manager.py  # Adapter Manager screen
│   ├── public_info.py      # Public Network Info screen
│   ├── report_generator.py # Diagnostic Report screen
│   ├── health_score.py     # Health Score screen
│   └── log_viewer.py       # Log Viewer screen
│
├── network/                # Network domain logic — UI-free (16 modules)
│   ├── powershell.py       # Wrapped, UTF-8, timeout-safe PowerShell runner
│   ├── adapter.py          # Adapter dataclass + AdapterCategory enum
│   ├── categorizer.py      # Pure categorization rules
│   ├── scanner.py          # AdapterScanner + ScanResult/ScanStats
│   ├── diagnostics.py      # IP / DNS / gateway enrichment
│   ├── export.py           # CSV / JSON / TXT exporter
│   ├── internet.py         # Internet connectivity check
│   ├── local_info.py       # Local IP, adapters, DNS (psutil-based)
│   ├── public_info.py      # Public IP, ISP, geo lookup
│   ├── health.py           # Health score computation (0–100)
│   ├── diagnostics_internet.py # Ping, traceroute, MTU, DNS tests
│   ├── speed_test.py       # Download/upload speed test
│   ├── dns_tools.py        # DNS management (change, flush, register)
│   ├── repair.py           # Network repair sequence
│   ├── adapter_manager.py  # Adapter enable/disable/restart
│   ├── report_generator.py # Diagnostic report generation
│   └── health_service.py   # Health score service
│
├── utils/                  # Cross-cutting helpers
│   ├── admin.py            # Administrator / elevation detection
│   ├── logger.py           # Daily file logging + auto-cleanup
│   ├── helpers.py          # Pure formatting helpers
│   └── storage.py          # Paths + atomic JSON persistence
│
├── logs/                   # Daily log files (auto-created)
└── exports/                # Exported reports (auto-created)
```

### Architecture

```
utils/  ←  network/  ←  ui/  ←  app.py
(deps)    (utils+cfg)   (net+ui)  (wires all)
```

- `utils/` depends on nothing inside NetMedic.
- `network/` depends only on `utils/` and `config`.
- `ui/` depends on `network/` and `utils/`, never the other way around.
- `app.py` wires all three layers together.

This makes the domain logic (`network/`) independently testable and the
UI swappable without touching PowerShell code.

---

## Configuration

`config.json` controls:

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
| `ignored_adapters` | string[] | `[]` | Adapter names hidden from scans. |

Invalid values are replaced with their defaults and logged; the app
never fails to start because of a malformed `config.json`.

---

## Building

```powershell
# Standard build
python build.py

# Clean build (removes previous artifacts)
python build.py --clean

# Build and verify (launches the executable)
python build.py --verify
```

The build produces a single portable executable at `dist/NetMedic.exe`.
No installation required — just copy and run.

---

## Safety & Design Principles

1. **Never remove hardware automatically.** NetMedic's maintenance
   actions are limited to *disable* — never uninstall or delete.
2. **Explicit confirmation for every destructive action.** Each is
   gated behind a modal dialog with a distinct "Confirm" step.
3. **Admin-only maintenance.** The *Disable* and *Restart* actions
   refuse to run without elevation and show a friendly explanation.
4. **Failures are surfaced, never fatal.** Every PowerShell call is
   wrapped; errors become a dialog plus a log line, not a crash.
5. **Thread safety.** All I/O runs on background threads. The UI
   never freezes during network operations.
6. **Graceful degradation.** Partial results are shown when some
   APIs or commands fail — the app continues working.

---

## Code Quality

- Type hints throughout; mypy-friendly.
- Dataclasses for all DTOs; enums for categories/states/formats.
- No module-level mutable globals; no magic numbers (named constants).
- PEP 8 layout; comprehensive docstrings.
- Each module is small and single-purpose.
- Frozen dataclasses for thread-safe result passing.
- `threading.Lock` for shared mutable state in concurrent code.
- Input validation on all PowerShell-interpolated values.

---

## License

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
