"""
Network Repair screen.

A full-screen modal that runs the network repair sequence with live
step-by-step progress.  Each step shows a pending/running/success/failed
indicator, duration, and output.

Accessed via the **U** key binding or the *Repair* button in the actions bar.
"""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.repair import (
    RepairResult,
    RepairStep,
    StepStatus,
    is_admin,
    run_repair,
)


class RepairScreen(ModalScreen[None]):
    """Full-screen network repair overlay with step-by-step progress.

    Displays 7 repair steps with live status updates. Shows a restart
    warning if any Winsock/TCP/IP reset succeeded.
    """

    DEFAULT_CSS = """
    RepairScreen {
        background: #0b1016ee;
        align: center middle;
    }
    RepairScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0f1923;
        border: thick #f59e0b;
        padding: 1 2;
    }
    RepairScreen #title {
        height: 2;
        text-align: center;
        color: #f59e0b;
        text-style: bold;
        padding-bottom: 1;
    }
    RepairScreen #admin-banner {
        height: auto;
        text-align: center;
        padding: 0 0 1 0;
    }
    RepairScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    RepairScreen #steps {
        height: auto;
        margin: 0 0 1 0;
    }
    RepairScreen .step-row {
        height: auto;
        border: round #223042;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    RepairScreen .step-header {
        height: 1;
    }
    RepairScreen .step-detail {
        height: 1;
        color: #64748b;
    }
    RepairScreen .step-output {
        height: 1;
        color: #94a3b8;
    }
    RepairScreen .step-pending   { color: #64748b; }
    RepairScreen .step-running   { color: #facc15; }
    RepairScreen .step-success   { color: #4ade80; }
    RepairScreen .step-failed    { color: #f87171; }
    RepairScreen .step-skipped   { color: #64748b; }
    RepairScreen #summary {
        height: auto;
        border: round #223042;
        padding: 1 2;
        margin: 0 0 1 0;
        text-align: center;
    }
    RepairScreen #restart-warning {
        height: auto;
        text-align: center;
        color: #f59e0b;
        padding: 1 0;
    }
    RepairScreen #btn-row {
        height: auto;
        padding: 1 0 0 0;
    }
    RepairScreen #btn-row Button {
        margin-right: 1;
    }
    RepairScreen #start-btn {
        background: #214d86;
    }
    RepairScreen #close-btn {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cancel_event = threading.Event()
        self._repair_thread: threading.Thread | None = None
        self._steps: list[RepairStep] = []
        self._step_widgets: dict[str, tuple[Static, Static, Static]] = {}

        # Widgets
        self._title: Static
        self._admin_banner: Static
        self._status: Static
        self._summary: Static
        self._restart_warning: Static
        self._start_btn: Button
        self._close_btn: Button

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Network Repair", id="title")
            yield self._title

            self._admin_banner = Static("", id="admin-banner")
            yield self._admin_banner

            self._status = Static("Click Start to begin network repair", id="status")
            yield self._status

            with VerticalScroll(id="steps"):
                from network.repair import REPAIR_STEPS
                for step_def in REPAIR_STEPS:
                    header = Static(
                        f"○ {step_def.label}", classes="step-header step-pending",
                    )
                    detail = Static(
                        step_def.description, classes="step-detail",
                    )
                    output = Static("", classes="step-output")
                    with Horizontal(classes="step-row"):
                        yield header
                    with Horizontal(classes="step-row"):
                        yield detail
                    with Horizontal(classes="step-row"):
                        yield output
                    self._step_widgets[step_def.id] = (header, detail, output)
                    self._steps.append(step_def)

            self._summary = Static("Ready", id="summary")
            yield self._summary

            self._restart_warning = Static("", id="restart-warning")
            yield self._restart_warning

            with Horizontal(id="btn-row"):
                self._start_btn = Button("Start Repair", id="start-btn", variant="warning")
                yield self._start_btn
                self._close_btn = Button("Close  [Esc]", id="close-btn")
                yield self._close_btn

    def on_mount(self) -> None:
        """Show admin status banner."""
        if is_admin():
            self._admin_banner.update(
                "[green]Running as Administrator — full repair available[/]"
            )
        else:
            self._admin_banner.update(
                "[yellow]Standard user — some steps may require elevation[/]"
            )

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self._start_repair()
        elif event.button.id == "close-btn":
            self._cancel_and_close()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self._cancel_and_close()

    # ------------------------------------------------------------------ #
    # Repair control
    # ------------------------------------------------------------------ #
    def _start_repair(self) -> None:
        """Begin the repair sequence in a background thread."""
        self._cancel_event.clear()
        self._start_btn.disabled = True
        self._start_btn.label = "Running…"
        self._restart_warning.update("")

        # Reset all step widgets
        from network.repair import REPAIR_STEPS
        for step_def in REPAIR_STEPS:
            widgets = self._step_widgets.get(step_def.id)
            if widgets:
                header, detail, output = widgets
                header.update(f"○ {step_def.label}")
                header.remove_class("step-success", "step-failed", "step-running", "step-skipped")
                header.add_class("step-pending")
                detail.update(step_def.description)
                output.update("")

        self._summary.update("Running repair sequence…")
        self._status.update("Executing repair steps…")

        self._repair_thread = threading.Thread(
            target=self._run_repair, daemon=True,
        )
        self._repair_thread.start()

    def _run_repair(self) -> None:
        """Execute repair (runs on background thread)."""
        try:
            result = run_repair(
                cancel_event=self._cancel_event,
                progress=self._on_step_progress,
            )
            self.call_from_thread(self._show_results, result)
        except Exception as exc:
            self.call_from_thread(self._show_error, str(exc))

    def _cancel_and_close(self) -> None:
        """Cancel running repair and dismiss."""
        self._cancel_event.set()
        if self._repair_thread and self._repair_thread.is_alive():
            self._repair_thread.join(timeout=5)
        self.dismiss()

    # ------------------------------------------------------------------ #
    # Progress callback
    # ------------------------------------------------------------------ #
    def _on_step_progress(
        self, step_index: int, total_steps: int, step: RepairStep,
    ) -> None:
        """Update the UI for a step completing."""
        def _update() -> None:
            widgets = self._step_widgets.get(step.id)
            if not widgets:
                return

            header, detail, output = widgets

            if step.status == StepStatus.RUNNING:
                header.update(f"▶ {step.label}")
                header.remove_class("step-pending", "step-success", "step-failed", "step-skipped")
                header.add_class("step-running")
                self._status.update(
                    f"Step {step_index + 1}/{total_steps}: {step.label}…"
                )

            elif step.status == StepStatus.SUCCESS:
                header.update(f"✔ {step.label}  ({step.duration_s:.1f}s)")
                header.remove_class("step-pending", "step-running", "step-failed", "step-skipped")
                header.add_class("step-success")
                if step.output:
                    # Show first line of output
                    first_line = step.output.split("\n")[0][:80]
                    output.update(f"  {first_line}")

            elif step.status == StepStatus.FAILED:
                header.update(f"✘ {step.label}  ({step.duration_s:.1f}s)")
                header.remove_class("step-pending", "step-running", "step-success", "step-skipped")
                header.add_class("step-failed")
                error_text = step.error or step.output or "Unknown error"
                output.update(f"  [red]{error_text[:80]}[/]")

            elif step.status == StepStatus.SKIPPED:
                header.update(f"— {step.label}  (skipped)")
                header.remove_class("step-pending", "step-running", "step-success", "step-failed")
                header.add_class("step-skipped")

        self.call_from_thread(_update)

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #
    def _show_results(self, result: RepairResult) -> None:
        """Render the final repair summary."""
        self._start_btn.disabled = False
        self._start_btn.label = "Run Again"
        self._status.update("Repair complete")

        if result.cancelled:
            self._summary.update("[yellow]Repair cancelled by user[/]")
            return

        parts = []
        if result.success_count > 0:
            parts.append(f"[green]{result.success_count} passed[/]")
        if result.failed_count > 0:
            parts.append(f"[red]{result.failed_count} failed[/]")
        if result.skipped_count > 0:
            parts.append(f"[dim]{result.skipped_count} skipped[/]")

        summary = "  ·  ".join(parts)
        duration = f"  ({result.total_duration_s:.1f}s)"
        self._summary.update(f"{summary}{duration}")

        if result.restart_required:
            self._restart_warning.update(
                "[yellow]⚠  A system restart is recommended to complete "
                "the network reset.[/]"
            )

        # Final status
        if result.failed_count == 0:
            self._status.update("[green]All repair steps completed successfully[/]")
        else:
            self._status.update(
                f"[yellow]Repair finished — {result.failed_count} step(s) failed[/]"
            )

    def _show_error(self, message: str) -> None:
        """Display an unexpected error."""
        self._status.update(f"[red]Error: {message}[/]")
        self._start_btn.disabled = False
        self._start_btn.label = "Retry"
