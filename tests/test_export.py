"""
Tests for the adapter exporter.

Covers ExportFormat enum, Exporter CSV/JSON/TXT output, and edge cases
(empty adapters, stats embedding).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from network.adapter import Adapter, AdapterCategory
from network.export import ExportFormat, Exporter
from network.scanner import ScanStats


# --------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------- #

def _make_adapter(**overrides: object) -> Adapter:
    """Build a minimal Adapter for testing.

    Uses PascalCase keys matching PowerShell conventions for ``Adapter.from_ps()``.
    """
    defaults: dict[str, object] = {
        "Name": "Wi-Fi",
        "InterfaceDescription": "Intel Wi-Fi 6 AX201",
        "Status": "Up",
        "MacAddress": "AA:BB:CC:DD:EE:FF",
        "LinkSpeed": "866.7 Mbps",
        "PnPDeviceID": "PCI\\VEN_8086&DEV_2723",
        "HardwareIDs": ["PCI\\VEN_8086&DEV_2723"],
        "Physical": True,
        "Virtual": False,
    }
    defaults.update(overrides)
    return Adapter.from_ps(defaults)  # type: ignore[arg-type]


@pytest.fixture
def sample_adapters() -> list[Adapter]:
    return [_make_adapter(), _make_adapter(Name="Ethernet", Physical=True)]


@pytest.fixture
def sample_stats() -> ScanStats:
    return ScanStats(
        total=2,
        physical=2,
        virtual=0,
        vpn=0,
        ghost=0,
        disabled=0,
        unknown=0,
    )


# --------------------------------------------------------------------- #
# ExportFormat
# --------------------------------------------------------------------- #

class TestExportFormat:
    def test_from_value_str(self) -> None:
        assert ExportFormat.from_value("csv") is ExportFormat.CSV
        assert ExportFormat.from_value("json") is ExportFormat.JSON
        assert ExportFormat.from_value("txt") is ExportFormat.TXT

    def test_from_value_member(self) -> None:
        assert ExportFormat.from_value(ExportFormat.CSV) is ExportFormat.CSV

    def test_from_value_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown export format"):
            ExportFormat.from_value("xml")

    def test_case_insensitive(self) -> None:
        assert ExportFormat.from_value("CSV") is ExportFormat.CSV
        assert ExportFormat.from_value("Json") is ExportFormat.JSON


# --------------------------------------------------------------------- #
# CSV export
# --------------------------------------------------------------------- #

class TestExportCSV:
    def test_csv_has_header(self, sample_adapters: list[Adapter], tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.CSV)
        result = exporter.export(sample_adapters, tmp_path / "out.csv")
        lines = result.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= 1
        header = lines[0]
        assert "name" in header
        assert "mac_address" in header

    def test_csv_row_count(
        self, sample_adapters: list[Adapter], tmp_path: Path
    ) -> None:
        exporter = Exporter(ExportFormat.CSV)
        result = exporter.export(sample_adapters, tmp_path / "out.csv")
        lines = result.read_text(encoding="utf-8").splitlines()
        # header + 2 adapter rows
        assert len(lines) == 3

    def test_csv_empty_adapters(self, tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.CSV)
        result = exporter.export([], tmp_path / "out.csv")
        lines = result.read_text(encoding="utf-8").splitlines()
        # header only
        assert len(lines) == 1


# --------------------------------------------------------------------- #
# JSON export
# --------------------------------------------------------------------- #

class TestExportJSON:
    def test_json_structure(
        self, sample_adapters: list[Adapter], sample_stats: ScanStats, tmp_path: Path
    ) -> None:
        exporter = Exporter(ExportFormat.JSON)
        result = exporter.export(sample_adapters, tmp_path / "out.json", stats=sample_stats)
        data = json.loads(result.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert data["count"] == 2
        assert len(data["adapters"]) == 2
        assert data["stats"]["total"] == 2

    def test_json_no_stats(self, sample_adapters: list[Adapter], tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.JSON)
        result = exporter.export(sample_adapters, tmp_path / "out.json")
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["stats"] is None

    def test_json_empty(self, tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.JSON)
        result = exporter.export([], tmp_path / "out.json")
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["count"] == 0
        assert data["adapters"] == []


# --------------------------------------------------------------------- #
# TXT export
# --------------------------------------------------------------------- #

class TestExportTXT:
    def test_txt_header(
        self, sample_adapters: list[Adapter], sample_stats: ScanStats, tmp_path: Path
    ) -> None:
        exporter = Exporter(ExportFormat.TXT)
        result = exporter.export(sample_adapters, tmp_path / "out.txt", stats=sample_stats)
        text = result.read_text(encoding="utf-8")
        assert "NetMedic Adapter Report" in text
        assert "Total adapters: 2" in text
        assert "physical=2" in text

    def test_txt_adapter_entry(self, sample_adapters: list[Adapter], tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.TXT)
        result = exporter.export(sample_adapters, tmp_path / "out.txt")
        text = result.read_text(encoding="utf-8")
        assert "Wi-Fi" in text
        assert "Ethernet" in text


# --------------------------------------------------------------------- #
# Custom columns
# --------------------------------------------------------------------- #

class TestCustomColumns:
    def test_subset_columns(self, sample_adapters: list[Adapter], tmp_path: Path) -> None:
        exporter = Exporter(ExportFormat.CSV, columns=("name", "status"))
        result = exporter.export(sample_adapters, tmp_path / "out.csv")
        lines = result.read_text(encoding="utf-8").splitlines()
        header = lines[0]
        assert "name" in header
        assert "status" in header
        assert "mac_address" not in header
