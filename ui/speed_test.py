"""
Internet Speed Test screen.

A full-screen modal that measures download speed, upload speed, ping
latency, and jitter.  Tests run on a background thread with real-time
progress updates and cancellation support.

Accessed via the **S** key binding or the *Speed Test* button in
the actions bar.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, ProgressBar, Static
from textual import work

from network.speed_test import (
    SpeedTestResult,
    run_speed_test,
)


class SpeedTestScreen(ModalScreen[None]):
    """Full-screen speed test overlay with progress and results.

    The screen is pushed by :meth:`NetMedicApp.action_speed_test` and
    dismissed with **Escape** or the *Close* button.
    """

    DEFAULT_CSS = """
    SpeedTestScreen {
        background: #0b1016ee;
        align: center middle;
    }
    SpeedTestScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    SpeedTestScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    SpeedTestScreen #status {
        height: 1;
        text-align: center;
        color: #facc15;
        padding-bottom: 1;
    }
    SpeedTestScreen .progress-section {
        height: auto;
        padding: 0 0 1 0;
    }
    SpeedTestScreen .progress-label {
        height: 1;
        color: #94a3b8;
    }
    SpeedTestScreen ProgressBar {
        width: 100%;
        height: 1;
    }
    SpeedTestScreen .result-row {
        height: auto;
        padding: 1 0;
    }
    SpeedTestScreen .result-header {
        height: 1;
        color: #94a3b8;
        text-style: bold;
    }
    SpeedTestScreen .result-value {
        height: 2;
        color: #e2e8f0;
        text-style: bold;
    }
    SpeedTestScreen .result-detail {
        height: 1;
        color: #64748b;
    }
    SpeedTestScreen #results {
        height: auto;
        padding: 1 0;
    }
    SpeedTestScreen .speed-big {
        color: #4ade80;
        text-style: bold;
    }
    SpeedTestScreen .speed-unit {
        color: #94a3b8;
    }
    SpeedTestScreen #btn-row {
        height: auto;
        padding: 1 0 0 0;
    }
    SpeedTestScreen #btn-row Button {
        margin-right: 1;
    }
    SpeedTestScreen #start-btn {
        background: #214d86;
    }
    SpeedTestScreen #close-btn {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cancel_requested = False

        # Widgets (set in compose)
        self._title: Static
        self._status: Static
        self._progress_bar: ProgressBar
        self._progress_label: Static
        self._ping_value: Static
        self._jitter_value: Static
        self._download_value: Static
        self._download_detail: Static
        self._upload_value: Static
        self._upload_detail: Static
        self._start_btn: Button
        self._close_btn: Button

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Internet Speed Test", id="title")
            yield self._title

            self._status = Static("Click Start to begin the speed test", id="status")
            yield self._status

            # Progress section (hidden until test starts)
            with Vertical(classes="progress-section"):
                self._progress_label = Static("", classes="progress-label")
                yield self._progress_label
                self._progress_bar = ProgressBar(total=100, show_eta=False)
                yield self._progress_bar

            # Results
            with Vertical(id="results"):
                # Ping
                with Vertical(classes="result-row"):
                    yield Static("PING LATENCY", classes="result-header")
                    self._ping_value = Static("—", classes="result-value")
                    yield self._ping_value
                    self._jitter_value = Static("Jitter: —", classes="result-detail")
                    yield self._jitter_value

                # Download
                with Vertical(classes="result-row"):
                    yield Static("DOWNLOAD SPEED", classes="result-header")
                    self._download_value = Static("—", classes="result-value")
                    yield self._download_value
                    self._download_detail = Static("", classes="result-detail")
                    yield self._download_detail

                # Upload
                with Vertical(classes="result-row"):
                    yield Static("UPLOAD SPEED", classes="result-header")
                    self._upload_value = Static("—", classes="result-value")
                    yield self._upload_value
                    self._upload_detail = Static("", classes="result-detail")
                    yield self._upload_detail

            # Buttons
            with Horizontal(id="btn-row"):
                self._start_btn = Button("Start", id="start-btn", variant="primary")
                yield self._start_btn
                self._close_btn = Button("Close  [Esc]", id="close-btn")
                yield self._close_btn

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self._start_test()
        elif event.button.id == "close-btn":
            self._cancel_and_close()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self._cancel_and_close()

    # ------------------------------------------------------------------ #
    # Test control
    # ------------------------------------------------------------------ #
    def _start_test(self) -> None:
        """Begin the speed test in a background worker."""
        self._cancel_requested = False
        self._start_btn.disabled = True
        self._start_btn.label = "Running..."
        self._progress_bar.progress = 0
        self._progress_bar.visible = True
        self._progress_label.visible = True

        # Reset results
        self._ping_value.update("Measuring...")
        self._jitter_value.update("Jitter: --")
        self._download_value.update("--")
        self._download_detail.update("")
        self._upload_value.update("--")
        self._upload_detail.update("")

        self._run_speed_test()

    @work(thread=True, exclusive=True, group="speed_test")
    def _run_speed_test(self) -> None:
        """Execute the speed test (runs on background worker)."""
        try:
            result = run_speed_test(
                download_mb=10,
                upload_mb=10,
                progress=self._on_progress,
            )
            self._show_results(result)
        except Exception as exc:
            self._show_error(str(exc))

    def _cancel_and_close(self) -> None:
        """Cancel any running test and dismiss the screen."""
        self._cancel_requested = True
        self.dismiss()

    # ------------------------------------------------------------------ #
    # Progress callback (called from background thread)
    # ------------------------------------------------------------------ #
    def _on_progress(self, phase: str, current: int, total: int) -> None:
        """Update progress bar from the speed test worker thread."""
        if self._cancel_requested or not self.is_mounted:
            return
        try:
            if phase == "ping":
                self._status.update("Measuring ping latency...")
                self._progress_label.update("Ping: sending ICMP packets...")
                self._progress_bar.progress = 0
            elif phase == "download":
                self._status.update("Testing download speed...")
                self._progress_label.update(f"Download: {current // (1024*1024)} MB / {total // (1024*1024)} MB")
                if total > 0:
                    self._progress_bar.progress = min(100, int(current / total * 100))
            elif phase == "upload_prepare":
                self._status.update("Preparing upload data...")
                self._progress_label.update("Upload: generating payload...")
                self._progress_bar.progress = 0
            elif phase == "upload":
                self._status.update("Testing upload speed...")
                self._progress_label.update(f"Upload: {current // (1024*1024)} MB / {total // (1024*1024)} MB")
                if total > 0:
                    self._progress_bar.progress = min(100, int(current / total * 100))
        except Exception:
            pass  # Screen may have been dismissed

    # ------------------------------------------------------------------ #
    # Results display
    # ------------------------------------------------------------------ #
    def _show_results(self, result: SpeedTestResult) -> None:
        """Render the final speed test results."""
        if not self.is_mounted:
            return
        self._start_btn.disabled = False
        self._start_btn.label = "Start Again"
        self._progress_bar.progress = 100
        self._progress_label.update("Test complete")

        if result.cancelled:
            self._status.update("Test cancelled")
            self._ping_value.update("—")
            self._download_value.update("—")
            self._upload_value.update("—")
            return

        if result.error:
            self._status.update(f"Error: {result.error}")
            return

        self._status.update("Test complete")

        # Ping
        self._ping_value.update(f"{result.ping_ms:.1f} ms")
        self._jitter_value.update(f"Jitter: {result.jitter_ms:.1f} ms")

        # Download
        if result.download_mbps > 0:
            speed_str = self._format_speed(result.download_mbps)
            self._download_value.update(speed_str)
            size_mb = result.download_bytes / (1024 * 1024)
            self._download_detail.update(
                f"{size_mb:.1f} MB in {result.download_duration_s:.1f}s"
            )
        else:
            self._download_value.update("[red]Failed[/]")

        # Upload
        if result.upload_mbps > 0:
            speed_str = self._format_speed(result.upload_mbps)
            self._upload_value.update(speed_str)
            size_mb = result.upload_bytes / (1024 * 1024)
            self._upload_detail.update(
                f"{size_mb:.1f} MB in {result.upload_duration_s:.1f}s"
            )
        else:
            self._upload_value.update("[red]Failed[/]")

    def _show_error(self, message: str) -> None:
        """Display an error message."""
        if not self.is_mounted:
            return
        self._status.update(f"[red]Error: {message}[/]")
        self._start_btn.disabled = False
        self._start_btn.label = "Retry"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_speed(mbps: float) -> str:
        """Format speed as a human-readable string with color."""
        if mbps >= 100:
            return f"[#4ade80]{mbps:.1f}[/] Mbps"
        if mbps >= 10:
            return f"[#facc15]{mbps:.1f}[/] Mbps"
        return f"[#f87171]{mbps:.1f}[/] Mbps"
