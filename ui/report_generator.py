"""
Report Generator screen.

A full-screen modal that generates a complete diagnostic report and
allows the user to preview, copy to clipboard, or export as TXT/HTML.

Accessed via the **G** key binding or the *Report* button in the actions bar.
"""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.report_generator import (
    DiagnosticReport,
    generate_report,
    render_text,
    save_report,
)


class ReportGeneratorScreen(ModalScreen[None]):
    """Full-screen report generator overlay.

    Generates a diagnostic report on a background thread, displays a
    preview, and provides buttons to copy, save as TXT, or save as HTML.
    """

    DEFAULT_CSS = """
    ReportGeneratorScreen {
        background: #0b1016ee;
        align: center middle;
    }
    ReportGeneratorScreen > Vertical {
        width: 100;
        height: 92%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    ReportGeneratorScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    ReportGeneratorScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    ReportGeneratorScreen #preview {
        height: 1fr;
        border: round #223042;
        padding: 1 2;
        overflow-y: auto;
        color: #d6dde6;
    }
    ReportGeneratorScreen #btn-row {
        height: auto;
        padding: 1 0 0 0;
    }
    ReportGeneratorScreen #btn-row Button {
        margin-right: 1;
    }
    ReportGeneratorScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    ReportGeneratorScreen .report-line {
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._report: DiagnosticReport | None = None
        self._report_text: str = ""

        # Widgets
        self._title: Static
        self._status: Static
        self._preview: VerticalScroll
        self._copy_btn: Button
        self._save_txt_btn: Button
        self._save_html_btn: Button
        self._close_btn: Button

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Diagnostic Report", id="title")
            yield self._title

            self._status = Static("Generating report…", id="status")
            yield self._status

            self._preview = VerticalScroll(id="preview")
            yield self._preview

            with Horizontal(id="btn-row"):
                self._copy_btn = Button("Copy to Clipboard", id="copy-btn", variant="primary")
                yield self._copy_btn
                self._save_txt_btn = Button("Save TXT", id="save-txt-btn")
                yield self._save_txt_btn
                self._save_html_btn = Button("Save HTML", id="save-html-btn")
                yield self._save_html_btn

            self._close_btn = Button("Close  [Esc]", id="close-btn")
            yield self._close_btn

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        """Generate the report on a background thread."""
        self._generate_report()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "close-btn":
            self.dismiss()
        elif btn_id == "copy-btn":
            self._copy_to_clipboard()
        elif btn_id == "save-txt-btn":
            self._save_as("txt")
        elif btn_id == "save-html-btn":
            self._save_as("html")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Report generation
    # ------------------------------------------------------------------ #
    def _generate_report(self) -> None:
        """Generate report in a background thread."""
        def _worker() -> None:
            try:
                report = generate_report()
                text = render_text(report)
            except Exception as exc:
                report = DiagnosticReport(errors=[str(exc)])
                text = f"Report generation failed: {exc}"
            self.call_from_thread(self._show_report, report, text)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_report(self, report: DiagnosticReport, text: str) -> None:
        """Display the generated report."""
        self._report = report
        self._report_text = text

        self._status.update(
            f"Report generated — {len(report.warnings)} warnings, "
            f"{len(report.errors)} errors"
        )

        # Render preview
        self._preview.remove_children()
        for line in text.split("\n"):
            widget = Static(line, classes="report-line")
            self._preview.mount(widget)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _copy_to_clipboard(self) -> None:
        """Copy the report text to the clipboard."""
        if not self._report_text:
            return

        try:
            import subprocess
            import sys

            # Use PowerShell to set clipboard content
            ps_script = f"Set-Clipboard -Value @'\n{self._report_text}\n'@"
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=creationflags,
            )

            self._status.update("[green]✔ Report copied to clipboard[/]")

        except Exception as exc:
            self._status.update(f"[red]✘ Copy failed: {exc}[/]")

    def _save_as(self, fmt: str) -> None:
        """Save the report to a file."""
        if not self._report:
            return

        from pathlib import Path
        from utils.storage import Storage

        storage = Storage()
        exports_dir = storage.base_dir / "exports"
        exports_dir.mkdir(exist_ok=True)

        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"netmedic-report-{timestamp}.{fmt}"
        path = str(exports_dir / filename)

        def _worker() -> None:
            success = save_report(self._report, path, fmt=fmt)
            if success:
                self.call_from_thread(
                    self._status.update,
                    f"[green]✔ Saved to {filename}[/]",
                )
            else:
                self.call_from_thread(
                    self._status.update,
                    f"[red]✘ Failed to save {filename}[/]",
                )

        self._status.update(f"Saving {fmt.upper()}…")
        threading.Thread(target=_worker, daemon=True).start()
