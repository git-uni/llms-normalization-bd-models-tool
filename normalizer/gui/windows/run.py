"""Pantalla 2 — Ejecución y progreso.

Lanza el `GuiController` y muestra el progreso en tiempo real: barra por
fases del pipeline (con Descubrimiento prepended en modo URL), tabla viva
de iteraciones del agente, panel de log con auto-scroll y botón Cancelar.
Al terminar (OK, cancelado o error), transiciona automáticamente a la
pantalla de resultado.
"""

import re

import customtkinter as ctk

from normalizer.gui.controller import (
    CancelledEvent,
    ControllerEvent,
    DoneEvent,
    ErrorEvent,
    GuiController,
    LogLineEvent,
)
from normalizer.gui.state import GuiState

_ITER_RE = re.compile(r"\[iter (\d+)\] -> (.+)$")
_PHASE_STARTS: dict[str, str] = {
    "Pipeline: ANÁLISIS ...": "Análisis",
    "Pipeline: DISEÑO ...": "Diseño",
    "Pipeline: DDL ...": "DDL",
}
_PHASE_ENDS: dict[str, str] = {
    "Pipeline: ANÁLISIS ok": "Análisis",
    "Pipeline: DISEÑO ok": "Diseño",
    "Pipeline: DDL ok": "DDL",
}

STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_DONE = "done"

_PHASE_COLORS = {
    STATUS_PENDING: ("#d0d0d0", "#3a3a3a"),  # light, dark
    STATUS_ACTIVE: ("#1f6aa5", "#1f6aa5"),
    STATUS_DONE: ("#2e7d32", "#2e7d32"),
}


class RunScreen(ctk.CTkFrame):
    def __init__(self, app: ctk.CTk) -> None:
        super().__init__(app)
        self.app = app
        self.gui_state: GuiState = app.gui_state
        self.gui_state.reset_run()

        self.phases: list[str] = (
            ["Descubrimiento", "Análisis", "Diseño", "DDL"]
            if self.gui_state.is_url
            else ["Análisis", "Diseño", "DDL"]
        )
        self.phase_status: dict[str, str] = {p: STATUS_PENDING for p in self.phases}
        self.phase_widgets: dict[str, ctk.CTkLabel] = {}

        self._build()
        self.controller = GuiController()
        self.controller.start(self.gui_state)
        self.after(100, self._poll)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            header, text="Ejecución", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left")
        self.cancel_btn = ctk.CTkButton(
            header,
            text="Cancelar",
            command=self._on_cancel,
            fg_color=("#b04040", "#9a3030"),
            hover_color=("#7a2020", "#7a2020"),
            width=110,
        )
        self.cancel_btn.pack(side="right")

        # Barra de progreso por fases
        ph_frame = ctk.CTkFrame(self)
        ph_frame.pack(fill="x", pady=(0, 12))
        ph_inner = ctk.CTkFrame(ph_frame, fg_color="transparent")
        ph_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            ph_inner,
            text="Progreso del pipeline",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(ph_inner, fg_color="transparent")
        row.pack(fill="x")
        for phase in self.phases:
            chip = ctk.CTkLabel(
                row,
                text=f"  {phase}  ",
                corner_radius=14,
                fg_color=_PHASE_COLORS[STATUS_PENDING],
                text_color=("#202020", "#f0f0f0"),
                height=28,
            )
            chip.pack(side="left", padx=4)
            self.phase_widgets[phase] = chip

        # Panel del agente (solo URL)
        if self.gui_state.is_url:
            agent_block = ctk.CTkFrame(self)
            agent_block.pack(fill="x", pady=(0, 12))
            agent_inner = ctk.CTkFrame(agent_block, fg_color="transparent")
            agent_inner.pack(fill="x", padx=14, pady=12)
            ctk.CTkLabel(
                agent_inner,
                text="Iteraciones del agente",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 6))
            self.agent_scroll = ctk.CTkScrollableFrame(agent_inner, height=160)
            self.agent_scroll.pack(fill="x")
            head = ctk.CTkFrame(self.agent_scroll, fg_color="transparent")
            head.pack(fill="x")
            ctk.CTkLabel(
                head, text="Iter", width=60, anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                head, text="Tool calls", anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", fill="x", expand=True)
        else:
            self.agent_scroll = None

        # Panel de log
        log_block = ctk.CTkFrame(self)
        log_block.pack(fill="both", expand=True)
        log_inner = ctk.CTkFrame(log_block, fg_color="transparent")
        log_inner.pack(fill="both", expand=True, padx=14, pady=12)
        ctk.CTkLabel(
            log_inner,
            text="Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        self.log_box = ctk.CTkTextbox(
            log_inner, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # Poll y eventos
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        events: list[ControllerEvent] = self.controller.drain()
        for ev in events:
            self._handle_event(ev)

        if self.controller.is_alive():
            self.after(100, self._poll)
        else:
            # El hilo terminó; drenar lo que queda y transicionar.
            for ev in self.controller.drain():
                self._handle_event(ev)
            self.after(600, self._finish_transition)

    def _handle_event(self, ev: ControllerEvent) -> None:
        if isinstance(ev, LogLineEvent):
            self._on_log(ev.line)
        elif isinstance(ev, DoneEvent):
            self.gui_state.finished_ok = True
            self._mark_remaining_done()
        elif isinstance(ev, CancelledEvent):
            self.gui_state.cancelled = True
            self._mark_active_as(STATUS_PENDING)
        elif isinstance(ev, ErrorEvent):
            self.gui_state.error_message = ev.message
            self.gui_state.error_phase = ev.phase

    def _on_log(self, line: str) -> None:
        self.gui_state.log_lines.append(line)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

        msg = line.split("] ", 1)[-1] if "] " in line else line
        if msg.startswith("Descubriendo evidencia"):
            self._mark_phase("Descubrimiento", STATUS_ACTIVE)
        elif msg.startswith("Evidencia en ") or msg.startswith("Agente done"):
            self._mark_phase("Descubrimiento", STATUS_DONE)
        elif msg.startswith("Agente cancelado"):
            self._mark_phase("Descubrimiento", STATUS_PENDING)
        else:
            for needle, phase in _PHASE_STARTS.items():
                if msg.startswith(needle):
                    self._mark_phase(phase, STATUS_ACTIVE)
                    break
            for needle, phase in _PHASE_ENDS.items():
                if msg.startswith(needle):
                    self._mark_phase(phase, STATUS_DONE)
                    break

        m = _ITER_RE.search(line)
        if m and self.agent_scroll is not None:
            self._append_agent_row(int(m.group(1)), m.group(2))

    def _append_agent_row(self, iter_n: int, calls: str) -> None:
        # Truncar si es muy largo para no romper la columna.
        if len(calls) > 200:
            calls = calls[:197] + "…"
        self.gui_state.agent_turns.append((iter_n, calls))
        row = ctk.CTkFrame(self.agent_scroll, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(row, text=str(iter_n), width=60, anchor="w").pack(side="left")
        ctk.CTkLabel(
            row, text=calls, anchor="w", wraplength=900, justify="left"
        ).pack(side="left", fill="x", expand=True)

    def _mark_phase(self, phase: str, status: str) -> None:
        if phase not in self.phase_widgets:
            return
        self.phase_status[phase] = status
        self.phase_widgets[phase].configure(fg_color=_PHASE_COLORS[status])

    def _mark_active_as(self, target: str) -> None:
        for phase, status in self.phase_status.items():
            if status == STATUS_ACTIVE:
                self._mark_phase(phase, target)

    def _mark_remaining_done(self) -> None:
        for phase in self.phases:
            if self.phase_status[phase] != STATUS_DONE:
                self._mark_phase(phase, STATUS_DONE)

    def _on_cancel(self) -> None:
        self.cancel_btn.configure(state="disabled", text="Cancelando...")
        self.controller.cancel()

    def _finish_transition(self) -> None:
        self.app.show_result()
