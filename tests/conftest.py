"""
Shared test fixtures for NetMedic.

Provides common fixtures used across test modules: temporary directories,
mock data, and configuration helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def tmp_logs_dir(tmp_path: Path) -> Path:
    """Return a temporary logs directory."""
    logs = tmp_path / "logs"
    logs.mkdir()
    return logs


@pytest.fixture
def sample_adapter_raw() -> dict:
    """Return a raw PowerShell-style adapter dictionary for testing."""
    return {
        "Name": "Wi-Fi",
        "InterfaceDescription": "Intel Wi-Fi 6 AX201",
        "ifIndex": 12,
        "InterfaceGuid": "{abc-123}",
        "Status": "Up",
        "MacAddress": "AA-BB-CC-DD-EE-FF",
        "LinkSpeed": "866.7 Mbps",
        "MediaConnectionState": "Connected",
        "DriverVersion": "22.120.0.3",
        "DriverDate": "2024-01-15",
        "DriverProvider": "Intel",
        "PnPDeviceID": "PCI\\VEN_8086&DEV_2723",
        "Hidden": False,
        "Physical": True,
        "PhysicalAdapter": True,
        "Virtual": False,
        "AdminStatus": 1,
        "HardwareIDs": ["PCI\\VEN_8086&DEV_2723"],
    }


@pytest.fixture
def sample_adapter_disabled() -> dict:
    """Return a raw PowerShell-style disabled adapter dictionary."""
    return {
        "Name": "Ethernet 2",
        "InterfaceDescription": "Realtek USB GbE",
        "ifIndex": 15,
        "InterfaceGuid": "{def-456}",
        "Status": "Disabled",
        "MacAddress": "11-22-33-44-55-66",
        "LinkSpeed": "0 bps",
        "MediaConnectionState": "Disconnected",
        "DriverVersion": "10.30.1007.0",
        "DriverDate": "2023-06-01",
        "DriverProvider": "Realtek",
        "PnPDeviceID": "USB\\VID_0BDA&PID_8153",
        "Hidden": False,
        "Physical": True,
        "PhysicalAdapter": True,
        "Virtual": False,
        "AdminStatus": 2,
        "HardwareIDs": ["USB\\VID_0BDA&PID_8153"],
    }


@pytest.fixture
def sample_adapter_virtual() -> dict:
    """Return a raw PowerShell-style virtual adapter dictionary."""
    return {
        "Name": "vEthernet (WSL)",
        "InterfaceDescription": "Hyper-V Virtual Ethernet Adapter",
        "ifIndex": 20,
        "InterfaceGuid": "{ghi-789}",
        "Status": "Up",
        "MacAddress": "",
        "LinkSpeed": "10 Gbps",
        "MediaConnectionState": "Connected",
        "DriverVersion": "10.0.26100.1",
        "DriverDate": "2024-01-01",
        "DriverProvider": "Microsoft",
        "PnPDeviceID": "ROOT\\*VMSMP",
        "Hidden": False,
        "Physical": False,
        "PhysicalAdapter": False,
        "Virtual": True,
        "AdminStatus": 1,
        "HardwareIDs": [],
    }
