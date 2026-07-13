"""
Internet Diagnostics screen.

A full-screen modal that runs network diagnostics (ping, traceroute,
MTU, DNS, gateway) in background workers and renders results in
seven bordered sections.  All network I/O happens off the UI thread;
the screen is a pure *view* that receives data via ``call_from_thread``.

Accessed via the **T** key binding or the *Diagnostics* button in
the actions bar.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.diagnostics_internet import (
    DnsTestResult,
    GatewayResult,
    MtuResult,
    MultiPingResult,
    PingResult,
    TracerouteResult,
    detect_gateway,
    detect_mtu,
    measure_packet_loss,
    ping_multi_host,
    test_dns_resolution,
    trace_route,
)
from utils.helpers import safe_str


class DiagnosticsScreen(ModalScreen[None]):
    """Full-screen diagnostics overlay with per-section live results.

    The screen is pushed by :meth:`NetMedicApp.action_diagnostics` and
    dismissed with **Escape** or the *Close* button.
    """

    DEFAULT_CSS = """
    DiagnosticsScreen {
        background: #0b1016ee;
        align: center middle;
    }
    DiagnosticsScreen > Vertical {
        width: 100;
        height: 92%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    DiagnosticsScreen #title {
        height: 2;
        padding: 0 0 1 0;
        color: #8ab4ff;
        text-style: bold;
    }
    DiagnosticsScreen VerticalScroll {
        height: 1fr;
    }
    DiagnosticsScreen #close-btn {
        dock: bottom;
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    DiagnosticsScreen .diag-section {
        border: round #223042;
        margin: 0 0 1 0;
        padding: 1 2;
        height: auto;
        min-height: 4;
    }
    DiagnosticsScreen .diag-section Static {
        height: auto;
    }
    DiagnosticsScreen .running {
        color: #facc15;
    }
    DiagnosticsScreen .done {
        color: #4ade80;
    }
    DiagnosticsScreen .error {
        color: #f87171;
    }
    """

    # Default multi-ping targets — common public DNS / CDN endpoints.
    DEFAULT_PING_HOSTS: list[str] = [
        "8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._title: Static
        self._ping_content: Static
        self._multi_content: Static
        self._loss_content: Static
        self._trace_content: Static
        self._mtu_content: Static
        self._dns_content: Static
        self._gw_content: Static

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("", id="title")
            yield self._title

            with VerticalScroll():
                self._ping_content = Static("Running ping test…", classes="diag-section running")
                yield self._ping_content

                self._multi_content = Static("Running multi-host ping…", classes="diag-section running")
                yield self._multi_content

                self._loss_content = Static("Running packet loss test…", classes="diag-section running")
                yield self._loss_content

                self._trace_content = Static("Running traceroute…", classes="diag-section running")
                yield self._trace_content

                self._mtu_content = Static("Detecting MTU…", classes="diag-section running")
                yield self._mtu_content

                self._dns_content = Static("Testing DNS resolution…", classes="diag-section running")
                yield self._dns_content

                self._gw_content = Static("Detecting gateway…", classes="diag-section running")
                yield self._gw_content

            yield Button("Close  [Esc]", id="close-btn", variant="default")

    def on_mount(self) -> None:
        """Push the title and kick off all diagnostic workers."""
        self._title.update(
            "[b]Internet Diagnostics[/]\n"
            "[dim]Running network diagnostics — results appear as they complete…[/]"
        )
        self._run_all()

    # ------------------------------------------------------------------ #
    # Button / key handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Diagnostic workers — each runs on a Textual worker thread
    # ------------------------------------------------------------------ #
    def _run_all(self) -> None:
        self._run_ping()
        self._run_multi_ping()
        self._run_packet_loss()
        self._run_traceroute()
        self._run_mtu()
        self._run_dns()
        self._run_gateway()

    def _run_ping(self) -> None:
        """Ping 8.8.8.8 with 4 packets."""
        try:
            result = ping_host("8.8.8.8", count=4, timeout=2)
        except Exception as exc:
            result = PingResult(host="8.8.8.8", reachable=False, error=str(exc))
        self.call_from_thread(self._render_ping, result)

    def _run_multi_ping(self) -> None:
        """Ping multiple public DNS servers concurrently."""
        try:
            result = ping_multi_host(self.DEFAULT_PING_HOSTS, count=4, timeout=2)
        except Exception as exc:
            result = MultiPingResult(results=[], error=str(exc))
        self.call_from_thread(self._render_multi_ping, result)

    def _run_packet_loss(self) -> None:
        """20-packet loss test to 8.8.8.8."""
        try:
            result = measure_packet_loss("8.8.8.8", count=20, timeout=2)
        except Exception as exc:
            result = PingResult(host="8.8.8.8", reachable=False, error=str(exc))
        self.call_from_thread(self._render_packet_loss, result)

    def _run_traceroute(self) -> None:
        """Traceroute to 8.8.8.8."""
        try:
            result = trace_route("8.8.8.8", max_hops=20, timeout=3000)
        except Exception as exc:
            result = TracerouteResult(host="8.8.8.8", hops=[], error=str(exc))
        self.call_from_thread(self._render_traceroute, result)

    def _run_mtu(self) -> None:
        """Binary-search MTU detection via 8.8.8.8."""
        try:
            result = detect_mtu("8.8.8.8")
        except Exception as exc:
            result = MtuResult(mtu=0, method="Failed", error=str(exc))
        self.call_from_thread(self._render_mtu, result)

    def _run_dns(self) -> None:
        """Parallel DNS resolution test across 4 public servers."""
        try:
            result = test_dns_resolution()
        except Exception as exc:
            result = DnsTestResult(results=[], error=str(exc))
        self.call_from_thread(self._render_dns, result)

    def _run_gateway(self) -> None:
        """Default gateway detection + latency probe."""
        try:
            result = detect_gateway()
        except Exception as exc:
            result = GatewayResult(gateway="—", interface="—", error=str(exc))
        self.call_from_thread(self._render_gateway, result)

    # ------------------------------------------------------------------ #
    # Renderers — run on the UI thread via call_from_thread
    # ------------------------------------------------------------------ #
    def _render_ping(self, r: PingResult) -> None:
        """Paint the single-host ping section."""
        lines = ["Ping: 8.8.8.8 (ICMP, 4 packets)", ""]

        if r.error:
            lines.append(f"  [error]Error: {r.error}[/]")
        else:
            status = "[done]Reachable[/]" if r.reachable else "[error]Unreachable[/]"
            lines.append(f"  Status: {status}")
            lines.append(f"  Sent: {r.packets_sent}  Received: {r.packets_received}  Loss: {r.loss_pct:.1f}%")
            if r.reachable:
                lines.append(f"  Min: {r.min_ms:.1f} ms")
                lines.append(f"  Avg: {r.avg_ms:.1f} ms")
                lines.append(f"  Max: {r.max_ms:.1f} ms")
                lines.append(f"  Jitter: {r.jitter_ms:.1f} ms")

        self._ping_content.update("\n".join(lines), markup=False)
        self._ping_content.remove_class("running")
        self._ping_content.add_class("done" if r.reachable else "error")

    def _render_multi_ping(self, r: MultiPingResult) -> None:
        """Paint the multi-host ping section."""
        lines = [
            f"Multi-Host Ping  ({r.reachable_hosts}/{r.total_hosts} reachable)",
            "",
        ]

        for pr in r.results:
            if pr.reachable:
                lines.append(
                    f"  [done]✔[/] {pr.host:<20} "
                    f"avg {pr.avg_ms:6.1f} ms   "
                    f"min {pr.min_ms:6.1f} ms   "
                    f"max {pr.max_ms:6.1f} ms   "
                    f"jitter {pr.jitter_ms:5.1f} ms   "
                    f"loss {pr.loss_pct:.0f}%"
                )
            elif pr.error:
                lines.append(f"  [error]✘[/] {pr.host:<20} {pr.error}")
            else:
                lines.append(f"  [error]✘[/] {pr.host:<20} unreachable")

        if r.total_hosts > 0:
            lines.append("")
            lines.append(f"  Overall loss: {r.overall_loss_pct:.1f}%")
            if r.reachable_hosts > 0:
                lines.append(
                    f"  Latency range: {r.min_latency_ms:.1f} – {r.max_latency_ms:.1f} ms "
                    f"(avg {r.avg_latency_ms:.1f} ms, jitter {r.jitter_ms:.1f} ms)"
                )

        self._multi_content.update("\n".join(lines), markup=False)
        self._multi_content.remove_class("running")
        self._multi_content.add_class(
            "done" if r.reachable_hosts == r.total_hosts else
            "error" if r.reachable_hosts == 0 else ""
        )

    def _render_packet_loss(self, r: PingResult) -> None:
        """Paint the packet loss section."""
        lines = [
            f"Packet Loss Test  (20 packets to {r.host})",
            "",
        ]

        if r.error:
            lines.append(f"  [error]Error: {r.error}[/]")
        else:
            loss_color = "done" if r.loss_pct <= 2 else "error"
            lines.append(f"  Sent: {r.packets_sent}   Received: {r.packets_received}")
            lines.append(f"  Packet loss: [{loss_color}]{r.loss_pct:.1f}%[/]")
            if r.reachable:
                lines.append(f"  Latency — min: {r.min_ms:.1f} ms  avg: {r.avg_ms:.1f} ms  max: {r.max_ms:.1f} ms")
                lines.append(f"  Jitter: {r.jitter_ms:.1f} ms")
            lines.append("")
            if r.loss_pct <= 2:
                lines.append("  [done]✔ Connection quality: Good[/]")
            elif r.loss_pct <= 10:
                lines.append("  [warning]⚠ Connection quality: Degraded[/]")
            else:
                lines.append("  [error]✘ Connection quality: Poor[/]")

        self._loss_content.update("\n".join(lines), markup=False)
        self._loss_content.remove_class("running")
        self._loss_content.add_class(
            "done" if r.loss_pct <= 2 and r.reachable else "error"
        )

    def _render_traceroute(self, r: TracerouteResult) -> None:
        """Paint the traceroute section."""
        lines = [f"Traceroute: {r.host}", ""]

        if r.error:
            lines.append(f"  [error]Error: {r.error}[/]")
        elif not r.hops:
            lines.append("  [warning]No hops returned.[/]")
        else:
            lines.append(f"  {'Hop':>4}  {'IP':<20}  {'Avg Latency':>12}")
            lines.append(f"  {'─'*4}  {'─'*20}  {'─'*12}")
            for hop in r.hops:
                ip_str = hop.ip if hop.ip else "*"
                if hop.timeout:
                    lat_str = "timeout"
                elif hop.latency_ms is not None:
                    lat_str = f"{hop.latency_ms:.1f} ms"
                else:
                    lat_str = "—"
                lines.append(f"  {hop.hop:>4}  {ip_str:<20}  {lat_str:>12}")

        self._trace_content.update("\n".join(lines), markup=False)
        self._trace_content.remove_class("running")
        self._trace_content.add_class(
            "done" if r.hops and not r.error else "error"
        )

    def _render_mtu(self, r: MtuResult) -> None:
        """Paint the MTU detection section."""
        lines = ["Path MTU Detection", ""]

        if r.error:
            lines.append(f"  [error]Error: {r.error}[/]")
        elif r.mtu > 0:
            quality = "done" if r.mtu >= 1280 else "error"
            lines.append(f"  MTU: [{quality}]{r.mtu} bytes[/]")
            lines.append(f"  Method: {r.method}")
            lines.append("")
            if r.mtu >= 1500:
                lines.append("  [done]✔ Optimal MTU for Ethernet[/]")
            elif r.mtu >= 1280:
                lines.append("  [done]✔ Adequate (meets IPv6 minimum)[/]")
            else:
                lines.append("  [error]✘ Below IPv6 minimum — fragmentation likely[/]")
        else:
            lines.append("  [warning]Could not determine MTU[/]")

        self._mtu_content.update("\n".join(lines), markup=False)
        self._mtu_content.remove_class("running")
        self._mtu_content.add_class("done" if r.mtu >= 1280 else "error")

    def _render_dns(self, r: DnsTestResult) -> None:
        """Paint the DNS resolution section."""
        lines = [
            f"DNS Resolution Test  ({r.servers_ok}/{r.servers_tested} servers responded)",
            "",
        ]

        for res in r.results:
            if res.resolved:
                lines.append(
                    f"  [done]✔[/] {res.server:<20} {res.latency_ms:6.1f} ms"
                )
            else:
                lines.append(
                    f"  [error]✘[/] {res.server:<20} {res.error or 'failed'}"
                )

        if r.servers_ok > 0:
            lines.append("")
            lines.append(
                f"  Avg: {r.avg_ms:.1f} ms   "
                f"Min: {r.min_ms:.1f} ms   "
                f"Max: {r.max_ms:.1f} ms   "
                f"Jitter: {r.jitter_ms:.1f} ms"
            )

        self._dns_content.update("\n".join(lines), markup=False)
        self._dns_content.remove_class("running")
        self._dns_content.add_class(
            "done" if r.servers_ok == r.servers_tested else
            "error" if r.servers_ok == 0 else ""
        )

    def _render_gateway(self, r: GatewayResult) -> None:
        """Paint the gateway detection section."""
        lines = ["Default Gateway", ""]

        if r.error:
            lines.append(f"  [error]Error: {r.error}[/]")
        else:
            status = "[done]Reachable[/]" if r.reachable else "[error]Unreachable[/]"
            lines.append(f"  Gateway:   {r.gateway}")
            lines.append(f"  Interface: {r.interface}")
            lines.append(f"  Status:    {status}")
            if r.reachable:
                lines.append(f"  Latency:   {r.latency_ms:.1f} ms")

        self._gw_content.update("\n".join(lines), markup=False)
        self._gw_content.remove_class("running")
        self._gw_content.add_class(
            "done" if r.reachable else "error"
        )
