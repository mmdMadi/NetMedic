"""
Tests for the diagnostic report generator.

Covers HTML escaping, text rendering, and data collection.
"""

from __future__ import annotations

from network.report_generator import (
    DiagnosticReport,
    NetworkStatus,
    SystemInfo,
    render_html,
    render_text,
)


def _minimal_report(**overrides: object) -> DiagnosticReport:
    """Build a minimal report for testing."""
    defaults = {
        "generated_at": "2026-01-01 00:00:00",
        "system": SystemInfo(
            hostname="TEST-PC",
            username="testuser",
            windows_version="Windows 11",
            python_version="3.12.0",
            cpu_count=8,
            cpu_freq_mhz=3200.0,
            ram_total_gb=16.0,
            ram_available_gb=8.0,
        ),
        "network": NetworkStatus(
            internet_status="Connected",
            local_ip="192.168.1.100",
            public_ip="203.0.113.1",
            dns_server="8.8.8.8",
            default_gateway="192.168.1.1",
            connected_adapter="Wi-Fi",
        ),
    }
    defaults.update(overrides)
    return DiagnosticReport(**defaults)  # type: ignore[arg-type]


class TestHtmlEscaping:
    """Verify that user-data is HTML-escaped in render_html()."""

    def test_hostname_escaped(self) -> None:
        report = _minimal_report(
            system=SystemInfo(
                hostname="<script>alert('xss')</script>",
                username="testuser",
                windows_version="Windows 11",
                python_version="3.12.0",
                cpu_count=1,
                cpu_freq_mhz=1000.0,
                ram_total_gb=4.0,
                ram_available_gb=2.0,
            )
        )
        html = render_html(report)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_username_escaped(self) -> None:
        report = _minimal_report(
            system=SystemInfo(
                hostname="PC",
                username='user"><img src=x onerror=alert(1)>',
                windows_version="Windows 11",
                python_version="3.12.0",
                cpu_count=1,
                cpu_freq_mhz=1000.0,
                ram_total_gb=4.0,
                ram_available_gb=2.0,
            )
        )
        html = render_html(report)
        assert "<img" not in html
        assert "&lt;img" in html or "&quot;&gt;" in html

    def test_network_status_escaped(self) -> None:
        report = _minimal_report(
            network=NetworkStatus(
                internet_status="No<strong>Internet</strong>",
                local_ip="127.0.0.1",
                public_ip="1.2.3.4",
                dns_server="8.8.8.8",
                default_gateway="192.168.1.1",
                connected_adapter="Wi-Fi",
            )
        )
        html = render_html(report)
        assert "<strong>" not in html
        assert "&lt;strong&gt;" in html

    def test_warnings_escaped(self) -> None:
        report = _minimal_report(warnings=["<b>Warning</b> & 'test'"])
        html = render_html(report)
        assert "<b>" not in html
        assert "&lt;b&gt;" in html
        assert "&amp;" in html

    def test_errors_escaped(self) -> None:
        report = _minimal_report(errors=['<script>alert("xss")</script>'])
        html = render_html(report)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_normal_values_not_corrupted(self) -> None:
        """Normal values should pass through without extra escaping."""
        report = _minimal_report()
        html = render_html(report)
        assert "TEST-PC" in html
        assert "testuser" in html
        assert "192.168.1.100" in html


class TestTextRendering:
    """Verify plain text rendering."""

    def test_text_contains_sections(self) -> None:
        report = _minimal_report()
        text = render_text(report)
        assert "NetMedic Diagnostic Report" in text
        assert "SYSTEM INFORMATION" in text
        assert "NETWORK STATUS" in text
        assert "TEST-PC" in text

    def test_text_with_warnings(self) -> None:
        report = _minimal_report(warnings=["Test warning"])
        text = render_text(report)
        assert "WARNINGS" in text
        assert "Test warning" in text
