<div align="center">

<!-- Logo placeholder -->
<!-- <img src="docs/images/logo.png" alt="NetMedic Logo" width="120" /> -->

# NetMedic

**Modern Windows Network Diagnostics & Repair Toolkit built with Python and Textual.**

[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg?style=for-the-badge)](https://github.com/mmdMadi/NetMedic/releases/latest)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-00d275.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4.svg?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/)
[![Tests](https://img.shields.io/badge/tests-289%20passing-brightgreen.svg?style=for-the-badge)](https://github.com/mmdMadi/NetMedic/actions)
[![GitHub Stars](https://img.shields.io/github/stars/mmdMadi/NetMedic?style=for-the-badge&logo=github)](https://github.com/mmdMadi/NetMedic/stargazers)
[![Downloads](https://img.shields.io/github/downloads/mmdMadi/NetMedic/total?style=for-the-badge&logo=github)](https://github.com/mmdMadi/NetMedic/releases)
[![Last Commit](https://img.shields.io/github/last-commit/mmdMadi/NetMedic?style=for-the-badge&logo=github)](https://github.com/mmdMadi/NetMedic/commits/main)
[![Issues](https://img.shields.io/github/issues/mmdMadi/NetMedic?style=for-the-badge&logo=github)](https://github.com/mmdMadi/NetMedic/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/mmdMadi/NetMedic?style=for-the-badge&logo=github)](https://github.com/mmdMadi/NetMedic/pulls)
[![Code Size](https://img.shields.io/github/languages/code-size/mmdMadi/NetMedic?style=for-the-badge)](https://github.com/mmdMadi/NetMedic)

---

NetMedic inspects every network adapter on your Windows machine, detects inactive / virtual / VPN / ghost adapters, provides safe maintenance tools, and displays a live dashboard with internet health scoring — **without ever removing hardware automatically**.

**Safe · Readable · Modular · Robust · Portable**

</div>

---

## Why NetMedic?

Windows networking tools are scattered across **CMD**, **PowerShell**, **Control Panel**, and **Settings** — each with its own interface, syntax, and learning curve. Diagnosing a network issue often means jumping between five different tools just to gather basic information.

**NetMedic solves this** by unifying everything into a single, keyboard-driven terminal interface. One application to scan adapters, diagnose connectivity, test speed, manage DNS, repair network stacks, and generate reports — all without leaving the terminal.

### Built for

| Audience | Use Case |
|----------|----------|
| **System Administrators** | Fleet diagnostics, adapter management, automated repair |
| **IT Support** | Quick triage, one-click repair, report generation |
| **Developers** | Network debugging, DNS switching, connectivity testing |
| **Power Users** | Health monitoring, adapter cleanup, performance testing |
| **Help Desk Engineers** | Guided diagnostics, exportable reports for escalation |

---

## Screenshots

<!-- Replace placeholders with actual screenshots -->

| Dashboard | Adapter Scanner | Internet Diagnostics |
|-----------|----------------|---------------------|
| ![Dashboard](docs/images/dashboard.png) | ![Adapter Scanner](docs/images/adapter_scanner.png) | ![Internet Diagnostics](docs/images/diagnostics.png) |

| Speed Test | DNS Tools | Network Repair |
|-----------|-----------|---------------|
| ![Speed Test](docs/images/speed_test.png) | ![DNS Tools](docs/images/dns_tools.png) | ![Network Repair](docs/images/repair.png) |

| Adapter Manager | Health Score | Public Info | Report |
|----------------|-------------|-------------|--------|
| ![Adapter Manager](docs/images/adapter_manager.png) | ![Health Score](docs/images/health_score.png) | ![Public Info](docs/images/public_info.png) | ![Report](docs/images/report.png) |

---

## Demo

<!-- Replace with actual GIF -->

![NetMedic Demo](docs/images/demo.gif)

*Demonstrates: launch → scan adapters → run diagnostics → repair network → export report*

---

## Feature Highlights

```
✅ Network Adapter Scanner          ✅ Internet Diagnostics
✅ Internet Speed Test              ✅ DNS Tools (7 presets)
✅ One-Click Network Repair         ✅ Public IP Detection
✅ Internet Health Score (0-100)    ✅ Diagnostic Report Generator
✅ Adapter Manager (Enable/Disable) ✅ Log Viewer
✅ CSV / JSON / TXT Export          ✅ Portable Executable
✅ 289 Tests                        ✅ CI/CD Pipeline
```

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
├── __init__.py             # Package version (1.4.0)
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
├── network/                # Network domain logic — UI-free (18 modules)
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
├── tests/                  # Test suite (289 tests)
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

## Roadmap

### Completed

- [x] Dashboard with live status cards
- [x] Network Adapter Scanner with categorization
- [x] Internet Diagnostics (ping, traceroute, MTU, DNS, gateway)
- [x] Internet Speed Test (download, upload, ping, jitter)
- [x] DNS Tools with 7 provider presets
- [x] One-click Network Repair (7-step sequence)
- [x] Adapter Manager (enable/disable/restart)
- [x] Public Network Information
- [x] Diagnostic Report Generator (TXT, HTML, Clipboard)
- [x] Internet Health Score (0-100)
- [x] Log Viewer with automatic cleanup
- [x] CSV / JSON / TXT Export
- [x] PyInstaller portable executable
- [x] CI/CD with GitHub Actions
- [x] 289 tests across 14 test files

### Planned

- [ ] Bandwidth Monitor (real-time throughput graph)
- [ ] WiFi Signal Analyzer
- [ ] Firewall Rule Manager
- [ ] Plugin System for custom diagnostics
- [ ] Linux / macOS Support
- [ ] Scheduled Diagnostics (cron-like)
- [ ] Multi-language Support (i18n)
- [ ] Dark / Light Theme Toggle

---

## Performance

| Metric | Value |
|--------|-------|
| **Average Scan Time** | < 3 seconds |
| **Memory Usage** | ~30 MB idle |
| **Executable Size** | ~15 MB |
| **PowerShell Calls** | 5 bulk queries (optimized from N+1) |
| **Startup Time** | < 2 seconds |
| **Test Suite** | < 10 seconds |

---

## Security

NetMedic is designed with security as a first-class concern:

| Principle | Implementation |
|-----------|---------------|
| **No telemetry** | Zero network calls to analytics or tracking services |
| **No automatic hardware removal** | Actions limited to disable — never uninstall or delete |
| **No background services** | Runs only while the terminal is open |
| **No registry modifications** | Unless explicitly requested by the user |
| **Explicit confirmation** | Every destructive action gated behind a modal dialog |
| **Admin-only maintenance** | Disable/Restart refuse to run without elevation |
| **Input validation** | All PowerShell-interpolated values are sanitized |
| **No credential storage** | No passwords, tokens, or API keys are stored |

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

## Testing

```powershell
# Run all tests
python -m pytest tests/ -v

# Run only non-network tests (fast, no PowerShell)
python -m pytest tests/ -m "not network"

# Run with coverage report
python -m pytest tests/ --cov=network --cov=utils --cov=config --cov-report=term-missing
```

**289 tests** across 14 test files covering:

| Module | Tests | Coverage |
|--------|-------|----------|
| `network/adapter.py` | 17 | Construction, properties, serialization |
| `network/categorizer.py` | 18 | VPN, virtual, ghost, priority rules |
| `network/scanner.py` | 9 | ScanStats, ScanResult, ScanError |
| `network/diagnostics.py` | 10 | String normalization, enrich with mocks |
| `network/diagnostics_internet.py` | 13 | Ping, traceroute, MTU, DNS, gateway |
| `network/dns_tools.py` | 20 | Dataclasses, presets, validation |
| `network/repair.py` | 12 | Steps, repair execution with mocks |
| `network/export.py` | 12 | CSV, JSON, TXT export |
| `network/health.py` | 17 | Scoring, grading, thresholds |
| `network/health_service.py` | 4 | HealthReport dataclass |
| `network/internet.py` | 12 | Status enum, check results |
| `network/local_info.py` | 9 | Dataclasses, DNS provider matching |
| `network/powershell.py` | 11 | PSResult, runner, JSON parsing |
| `network/adapter_manager.py` | 10 | Dataclasses, validation |
| `network/report_generator.py` | 8 | HTML escaping, text rendering |
| `utils/helpers.py` | 25 | Formatting, string, color helpers |
| `utils/admin.py` | 7 | ElevationInfo, is_admin |
| `utils/storage.py` | 10 | Paths, JSON read/write |
| `config.py` | 16 | Defaults, coercion, persistence |

---

## FAQ

<details>
<summary><strong>Does NetMedic require administrator privileges?</strong></summary>

No. Most features work without elevation. Only **Disable**, **Restart**, and **Network Repair** (Winsock/TCP/IP reset) require administrator privileges. The app detects elevation status and shows a clear banner.
</details>

<details>
<summary><strong>Can NetMedic remove hardware?</strong></summary>

No. NetMedic will **never** automatically remove, uninstall, or delete network hardware. The most destructive action available is *disable*, which can be reversed by re-enabling the adapter.
</details>

<details>
<summary><strong>Can it work offline?</strong></summary>

Partially. Adapter scanning, DNS management, network repair, and local diagnostics work fully offline. Internet-dependent features (public IP lookup, speed test, some health checks) require an active connection.
</details>

<details>
<summary><strong>Does it support Windows 11?</strong></summary>

Yes. NetMedic supports Windows 10 and Windows 11. It uses PowerShell `Get-NetAdapter` which is available on both versions.
</details>

<details>
<summary><strong>Is internet access required?</strong></summary>

Not for core functionality. Adapter scanning, DNS tools, network repair, and adapter management work entirely offline. Internet access is only needed for public IP lookup, speed testing, and some health score checks.
</details>

<details>
<summary><strong>Can I build it from source?</strong></summary>

Yes. Clone the repository, install dependencies with `pip install -r requirements.txt`, and run `python app.py`. To build a portable executable, run `python build.py`.
</details>

<details>
<summary><strong>What terminal should I use?</strong></summary>

Windows Terminal is recommended for the best experience. CMD and PowerShell also work. The app uses a Textual TUI which renders properly in any modern Windows terminal.
</details>

<details>
<summary><strong>How do I update NetMedic?</strong></summary>

Pull the latest changes with `git pull` and restart the application. If using the portable executable, download the latest release from GitHub.
</details>

---

## Contributing

Contributions are welcome! Here's how to get started:

### Quick Start

1. **Fork** the repository
2. **Clone** your fork (`git clone https://github.com/YOUR-USERNAME/NetMedic.git`)
3. **Create** a feature branch (`git checkout -b feature/my-feature`)
4. **Make** your changes
5. **Test** your changes (`python -m pytest tests/ -v`)
6. **Commit** (`git commit -m "feat: add my feature"`)
7. **Push** (`git push origin feature/my-feature`)
8. **Open** a Pull Request

### Guidelines

- Follow the existing code style (PEP 8, type hints, docstrings)
- Add tests for new functionality
- Ensure all tests pass before submitting
- Update README if adding user-facing features
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages

### Areas for Contribution

- Bug fixes and error handling improvements
- New diagnostic tools or adapters
- UI/UX enhancements
- Documentation improvements
- Test coverage expansion
- Performance optimizations

---

## Support

### Report Bugs

Found a bug? Please [open an issue](https://github.com/mmdMadi/NetMedic/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Windows version and Python version

### Request Features

Have an idea? [Open a feature request](https://github.com/mmdMadi/NetMedic/issues/new?template=feature_request.md) describing:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

### Submit Pull Requests

Ready to contribute? See the [Contributing](#contributing) section above.

---

## Release History

| Version | Date | Highlights |
|---------|------|-----------|
| **v1.4.0** | 2026-07-13 | UI polish v3, documentation refresh, 289 tests |
| **v1.3.7** | 2026-07-13 | Final test coverage: admin, storage, diagnostics, config |
| **v1.3.6** | 2026-07-13 | Scanner, repair, local_info, health_service tests |
| **v1.3.5** | 2026-07-13 | Mock-based bulk fetch and DNS tools tests |
| **v1.3.4** | 2026-07-13 | Adapter manager and dns_tools test coverage |
| **v1.3.3** | 2026-07-13 | Bug fixes, security, performance, test expansion |
| **v1.3.0** | 2026-07-13 | Unit tests (82 tests across 5 modules) |
| **v1.2.0** | 2026-07-13 | Logging, UI polish, packaging |
| **v1.1.0** | 2026-07-13 | Diagnostics, speed test, DNS, repair, adapters, reports |
| **v1.0.0** | 2026-07-13 | Initial release: dashboard + adapter scanner |

---

## Acknowledgements

NetMedic is built on top of these amazing open-source projects:

| Project | Role |
|---------|------|
| [**Python**](https://www.python.org/) | Core language |
| [**Textual**](https://textual.textualize.io/) | TUI framework — makes beautiful terminal apps possible |
| [**PowerShell**](https://learn.microsoft.com/powershell/) | Windows network management and diagnostics |
| [**psutil**](https://github.com/giampaolo/psutil) | Cross-platform system and network utilities |
| [**requests**](https://requests.readthedocs.io/) | HTTP library for public API calls |
| [**PyInstaller**](https://pyinstaller.org/) | Python-to-executable packaging |

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

---

<div align="center">

**Built with ❤️ using Python and Textual**

[⬆ Back to Top](#netmedic)

</div>
