"""
Internet Health Score screen.

A full-screen modal that displays a comprehensive health score from
0 to 100 with per-check breakdown, warning explanations, and network
summary. Data is collected on a background thread.

Accessed via the **H** key binding or the *Health* button in the actions bar.
"""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.health_service import HealthReport, compute_health_report


def _score_color(percentage: float) -> str:
    """Return a Textual color name based on score percentage."""
    if percentage >= 90:
        return "green"
    if percentage >= 70:
        return "yellow"
    if percentage >= 50:
        return "orange"
    return "red"


class HealthScoreScreen(ModalScreen[None]):
    """Full-screen health score overlay.

    Displays the overall score with grade, per-check breakdown with
    pass/fail icons, and warning explanations.
    """

    DEFAULT_CSS = """
    HealthScoreScreen {
        background: #0b1016ee;
        align: center middle;
    }
    HealthScoreScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    HealthScoreScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    HealthScoreScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    HealthScoreScreen #score-display {
        height: auto;
        text-align: center;
        border: round #223042;
        padding: 2 2;
        margin: 0 0 1 0;
    }
    HealthScoreScreen .score-big {
        text-align: center;
    }
    HealthScoreScreen .score-grade {
        text-align: center;
        height: 1;
    }
    HealthScoreScreen #checks {
        height: auto;
        margin: 0 0 1 0;
    }
    HealthScoreScreen .check-row {
        height: auto;
        border: round #223042;
        padding: 0 2;
        margin: 0 0 1 0;
    }
    HealthScoreScreen .check-pass {
        color: #4ade80;
    }
    HealthScoreScreen .check-fail {
        color: #f87171;
    }
    HealthScoreScreen .check-warn {
        color: #facc15;
    }
    HealthScoreScreen #warnings {
        height: auto;
        margin: 0 0 1 0;
    }
    HealthScoreScreen .warning-row {
        height: auto;
        border: round #78350f;
        padding: 0 2;
        margin: 0 0 1 0;
        color: #facc15;
    }
    HealthScoreScreen #network-summary {
        height: auto;
        border: round #223042;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    HealthScoreScreen .summary-line {
        height: 1;
    }
    HealthScoreScreen .summary-label {
        color: #64748b;
    }
    HealthScoreScreen #btn-row {
        height: auto;
        padding: 1 0 0 0;
    }
    HealthScoreScreen #btn-row Button {
        margin-right: 1;
    }
    HealthScoreScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._report: HealthReport | None = None

        # Widgets
        self._title: Static
        self._status: Static
        self._score_display: Static
        self._checks_container: Vertical
        self._warnings_container: Vertical
        self._network_summary: Vertical
        self._refresh_btn: Button

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Internet Health Score", id="title")
            yield self._title

            self._status = Static("Computing health score…", id="status")
            yield self._status

            self._score_display = Static("Calculating…", id="score-display")
            yield self._score_display

            self._checks_container = Vertical(id="checks")
            yield self._checks_container

            self._warnings_container = Vertical(id="warnings")
            yield self._warnings_container

            self._network_summary = Vertical(id="network-summary")
            yield self._network_summary

            with Horizontal(id="btn-row"):
                self._refresh_btn = Button("Refresh", id="refresh-btn", variant="primary")
                yield self._refresh_btn
                yield Button("Close  [Esc]", id="close-btn")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        """Compute health score on a background thread."""
        self._compute_health()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()
        elif event.button.id == "refresh-btn":
            self._compute_health()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Health computation
    # ------------------------------------------------------------------ #
    def _compute_health(self) -> None:
        """Compute health score in a background thread."""
        self._refresh_btn.disabled = True
        self._status.update("Computing health score…")

        def _worker() -> None:
            try:
                report = compute_health_report()
            except Exception as exc:
                from network.health import HealthScore
                report = HealthReport(
                    score=HealthScore(score=0, max_score=100),
                    warnings=[str(exc)],
                )
            self.call_from_thread(self._show_report, report)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_report(self, report: HealthReport) -> None:
        """Render the health report."""
        self._report = report
        self._refresh_btn.disabled = False

        score = report.score
        pct = score.percentage
        color = _score_color(pct)

        # Score display
        self._status.update(f"Health Score: {score.score}/{score.max_score} — {score.grade}")
        self._score_display.update(
            f"[b {color}]{score.status_symbol}  {score.score} / {score.max_score}[/]\n"
            f"[{color}]{score.grade}[/]"
        )

        # Per-check breakdown
        self._checks_container.remove_children()
        for check in score.checks:
            if check.passed:
                icon = "✔"
                cls = "check-pass"
                detail = check.detail if check.detail else f"+{check.weight} pts"
            else:
                icon = "✘"
                cls = "check-fail"
                detail = check.detail if check.detail else "Failed"

            line = Static(
                f"  [{cls}]{icon}[/] {check.label:<25} {detail}",
                classes=f"check-row {cls}",
            )
            self._checks_container.mount(line)

        # Warnings section
        self._warnings_container.remove_children()
        if report.warnings:
            header = Static("WARNINGS", classes="check-warn")
            self._warnings_container.mount(header)
            for w in report.warnings:
                line = Static(f"  ⚠  {w}", classes="warning-row")
                self._warnings_container.mount(line)

        # Network summary
        self._network_summary.remove_children()
        summary_header = Static("NETWORK SUMMARY", classes="summary-line")
        self._network_summary.mount(summary_header)
        lines = [
            ("Internet", report.internet_status),
            ("Local IP", report.local_ip),
            ("Public IP", report.public_ip),
            ("DNS Server", report.dns_server),
            ("Gateway", report.default_gateway),
            ("Adapter", report.connected_adapter),
            ("Packet Loss", f"{report.packet_loss_pct:.1f}%"),
            ("MTU", str(report.mtu) if report.mtu else "—"),
            ("Ping", f"{report.ping_avg_ms:.1f} ms"),
            ("DNS Speed", f"{report.dns_avg_ms:.1f} ms"),
        ]
        for label, value in lines:
            line = Static(
                f"  [dim]{label}:[/]  {value}",
                classes="summary-line",
            )
            self._network_summary.mount(line)
