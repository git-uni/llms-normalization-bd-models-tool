"""Pantalla 2 — Ejecución y progreso (v2).

Reescritura del layout que da protagonismo al pipeline. De arriba a abajo:

- **Header**: título, botón Cancelar, metadatos de la corrida (proveedor,
  modelos, directorio de salida) y wall clock que avanza cada segundo.
- **Bloque pipeline** (~45%): una fila por fase con icono de estado, nombre
  y duración en curso/total. La fase activa se destaca y su contador
  refresca en vivo.
- **Bloque agente** (~25%, solo URL): tabla de iteraciones como en la v1.
- **Bloque log** (~15%, altura fija): textbox pequeño con auto-scroll.

Al pulsar Cancelar, la fase activa pasa al estado "cancelling" con icono
`⏸` y color ámbar, y un texto auxiliar explica que la cancelación espera a
que termine la llamada al LLM en curso.
"""

import re
import time

import customtkinter as ctk

from normalizer.gui.controller import (
    CancelledEvent,
    ControllerEvent,
    DoneEvent,
    ErrorEvent,
    GuiController,
    LogLineEvent,
)
from normalizer.gui.state import GuiState, PhaseInfo

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

# Iconos por estado. Símbolos unicode neutros que se ven igual en tema
# claro y oscuro; el color lo aporta el text_color del label.
_ICONS: dict[str, str] = {
    "pending": "○",
    "active": "●",
    "done": "✓",
    "error": "✗",
    "cancelling": "⏸",
}

_ICON_COLORS: dict[str, tuple[str, str]] = {
    "pending": ("#888888", "#888888"),
    "active": ("#1f6aa5", "#3a8fd6"),
    "done": ("#2e7d32", "#4caf50"),
    "error": ("#b30000", "#ff7a7a"),
    "cancelling": ("#b07a00", "#e0a040"),
}

# Colores de fondo por estado. "transparent" se pasa como string (no tupla)
# porque CustomTkinter no acepta transparencia dentro de una tupla light/dark.
_PHASE_ROW_BG: dict[str, str | tuple[str, str]] = {
    "pending": "transparent",
    "active": ("#e8f0fe", "#1f2a3a"),
    "done": "transparent",
    "error": ("#fde2e2", "#3a1f1f"),
    "cancelling": ("#fff4d6", "#3a2f1a"),
}


def _format_mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    mm, ss = divmod(s, 60)
    return f"{mm:02d}:{ss:02d}"


class RunScreen(ctk.CTkFrame):
    def __init__(self, app: ctk.CTk) -> None:
        super().__init__(app)
        self.app = app
        self.gui_state: GuiState = app.gui_state
        self.gui_state.reset_run()

        # Lista de nombres de fase para esta corrida (URL incluye Descubrimiento).
        phase_names = (
            ["Descubrimiento", "Análisis", "Diseño", "DDL"]
            if self.gui_state.is_url
            else ["Análisis", "Diseño", "DDL"]
        )
        self.gui_state.phases = [PhaseInfo(name=n) for n in phase_names]

        # Widgets por fase, indexados por nombre. Cada entrada tiene los
        # CTkLabel que se refrescan dinámicamente: icono, status_text y el
        # frame contenedor (para cambiar fg_color cuando se activa).
        self._phase_widgets: dict[str, dict] = {}
        self._cancelling = False  # flag para evitar updates concurrentes raros

        self._build()
        self.controller = GuiController()
        self.controller.start(self.gui_state)
        self.after(100, self._poll)
        self.after(1000, self._tick)

    # ------------------------------------------------------------------
    # Construcción del layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        s = self.gui_state
        mode_label = {"file": "archivo único", "dir": "directorio", "url": "URL"}[s.input_mode]

        # Tokens M3-inspired aplicados consistentemente:
        # - Spacing: 4 / 8 / 12 / 16 / 20 / 24
        # - Border radius: 12 en todas las cards
        # - Type scale: Title Large 22 / Title Small 16 / Body Medium 13 / Body Small 11

        # --- Header (surface container highest) ----------------------
        header = ctk.CTkFrame(
            self, fg_color=("#eef2fa", "#1a2230"), corner_radius=12,
        )
        header.pack(fill="x", pady=(0, 12))
        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=18)

        # Fila 1: título grande + chip de modo + botón cancelar
        top = ctk.CTkFrame(header_inner, fg_color="transparent")
        top.pack(fill="x")
        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box, text="Ejecución",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            title_box, text=f"  {mode_label}  ",
            corner_radius=10,
            fg_color=("#dde4f0", "#2a3548"),
            text_color=("#3a4a6a", "#b8c4dc"),
            font=ctk.CTkFont(size=11, weight="bold"),
            height=24,
        ).pack(side="left", padx=(12, 0))

        self.cancel_btn = ctk.CTkButton(
            top, text="Cancelar", command=self._on_cancel,
            fg_color=("#b04040", "#9a3030"),
            hover_color=("#7a2020", "#7a2020"),
            width=110, corner_radius=8,
        )
        self.cancel_btn.pack(side="right")

        # Fila 2: metadatos con iconos
        meta_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        meta_row.pack(fill="x", pady=(16, 0))

        def _meta(icon: str, text: str) -> None:
            ctk.CTkLabel(
                meta_row, text=icon, font=ctk.CTkFont(size=14),
                text_color=("#5566a0", "#7a8cc6"),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                meta_row, text=text, font=ctk.CTkFont(size=13),
                text_color=("#202838", "#d8e0ec"),
            ).pack(side="left", padx=(0, 24))

        _meta("◆", s.provider)
        _meta("▸", s.model or "(default)")
        if s.is_url and s.agent_model:
            _meta("▸", f"agente: {s.agent_model}")
        if s.out_dir is not None:
            _meta("▸", f"{s.out_dir.name}/")

        # --- Bloque pipeline (surface container, protagonista) ----------
        pipeline_block = ctk.CTkFrame(self, corner_radius=12)
        pipeline_block.pack(fill="both", expand=True, pady=(0, 12))
        pipeline_inner = ctk.CTkFrame(pipeline_block, fg_color="transparent")
        pipeline_inner.pack(fill="both", expand=True, padx=20, pady=18)

        title_row = ctk.CTkFrame(pipeline_inner, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            title_row, text="▣",
            font=ctk.CTkFont(size=16),
            text_color=("#1f6aa5", "#3a8fd6"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            title_row, text="Progreso del pipeline",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
        ).pack(side="left")

        for phase in self.gui_state.phases:
            self._build_phase_row(pipeline_inner, phase)

        self.pipeline_footer = ctk.CTkLabel(
            pipeline_inner, text="", text_color="gray", anchor="w",
        )
        self.pipeline_footer.pack(fill="x", pady=(16, 0))

        # Texto auxiliar de cancelación, aparece solo cuando hace falta.
        self.cancel_help_label = ctk.CTkLabel(
            pipeline_inner, text="", text_color=("#7a5a1a", "#e0c080"),
            anchor="w", wraplength=900,
        )
        self.cancel_help_label.pack(fill="x", pady=(4, 0))

        # --- Bloque iteraciones del agente (solo URL) ----------------
        self.agent_scroll = None
        if self.gui_state.is_url:
            agent_block = ctk.CTkFrame(self, corner_radius=12)
            agent_block.pack(fill="x", pady=(0, 12))
            agent_inner = ctk.CTkFrame(agent_block, fg_color="transparent")
            agent_inner.pack(fill="x", padx=20, pady=16)

            agent_title_row = ctk.CTkFrame(agent_inner, fg_color="transparent")
            agent_title_row.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(
                agent_title_row, text="◇",
                font=ctk.CTkFont(size=16),
                text_color=("#1f6aa5", "#3a8fd6"),
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                agent_title_row, text="Iteraciones del agente",
                font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
            ).pack(side="left")

            self.agent_scroll = ctk.CTkScrollableFrame(agent_inner, height=170)
            self.agent_scroll.pack(fill="x")
            head = ctk.CTkFrame(self.agent_scroll, fg_color="transparent")
            head.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(
                head, text="Iter", width=60, anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray",
            ).pack(side="left")
            ctk.CTkLabel(
                head, text="Tool calls", anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="gray",
            ).pack(side="left", fill="x", expand=True)

        # --- Bloque log (altura fija, sin protagonismo) ---------------
        log_block = ctk.CTkFrame(self, corner_radius=12)
        log_block.pack(fill="x")
        log_inner = ctk.CTkFrame(log_block, fg_color="transparent")
        log_inner.pack(fill="x", padx=20, pady=16)

        log_title_row = ctk.CTkFrame(log_inner, fg_color="transparent")
        log_title_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            log_title_row, text="▤",
            font=ctk.CTkFont(size=16),
            text_color=("#1f6aa5", "#3a8fd6"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            log_title_row, text="Log",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
        ).pack(side="left")

        self.log_box = ctk.CTkTextbox(
            log_inner, font=ctk.CTkFont(family="Consolas", size=11),
            height=140, wrap="none",
        )
        self.log_box.pack(fill="x")
        self.log_box.configure(state="disabled")

    def _build_phase_row(self, parent: ctk.CTkFrame, phase: PhaseInfo) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=8)
        row.pack(fill="x", pady=3)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        icon = ctk.CTkLabel(
            inner, text=_ICONS["pending"], width=32,
            text_color=_ICON_COLORS["pending"],
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        icon.pack(side="left")
        name = ctk.CTkLabel(
            inner, text=phase.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        name.pack(side="left", padx=(10, 0))
        status = ctk.CTkLabel(
            inner, text="pendiente",
            font=ctk.CTkFont(size=13),
            text_color="gray", anchor="e",
        )
        status.pack(side="right")
        self._phase_widgets[phase.name] = {
            "row": row,
            "icon": icon,
            "name": name,
            "status": status,
        }

    # ------------------------------------------------------------------
    # Poll de eventos
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        for ev in self.controller.drain():
            self._handle_event(ev)
        if self.controller.is_alive():
            self.after(100, self._poll)
        else:
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
            self._mark_active_as_cancelled()
        elif isinstance(ev, ErrorEvent):
            self.gui_state.error_message = ev.message
            self.gui_state.error_phase = ev.phase
            self._mark_active_as_error()

    def _on_log(self, line: str) -> None:
        self.gui_state.log_lines.append(line)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

        msg = line.split("] ", 1)[-1] if "] " in line else line
        if msg.startswith("Descubriendo evidencia"):
            self._mark_phase("Descubrimiento", "active")
        elif msg.startswith("Evidencia en ") or msg.startswith("Agente done"):
            self._mark_phase("Descubrimiento", "done")
        elif msg.startswith("Agente cancelado"):
            self._mark_phase("Descubrimiento", "cancelling")
        else:
            for needle, phase in _PHASE_STARTS.items():
                if msg.startswith(needle):
                    self._mark_phase(phase, "active")
                    break
            for needle, phase in _PHASE_ENDS.items():
                if msg.startswith(needle):
                    self._mark_phase(phase, "done")
                    break

        m = _ITER_RE.search(line)
        if m and self.agent_scroll is not None:
            self._append_agent_row(int(m.group(1)), m.group(2))

    def _append_agent_row(self, iter_n: int, calls: str) -> None:
        if len(calls) > 200:
            calls = calls[:197] + "…"
        self.gui_state.agent_turns.append((iter_n, calls))
        row = ctk.CTkFrame(self.agent_scroll, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(row, text=str(iter_n), width=60, anchor="w").pack(side="left")
        ctk.CTkLabel(
            row, text=calls, anchor="w", wraplength=900, justify="left"
        ).pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------------
    # Manipulación del estado de fases
    # ------------------------------------------------------------------

    def _phase_by_name(self, name: str) -> PhaseInfo | None:
        for p in self.gui_state.phases:
            if p.name == name:
                return p
        return None

    def _mark_phase(self, name: str, status: str) -> None:
        phase = self._phase_by_name(name)
        if phase is None:
            return
        # Si ya estamos cancelando, no permitimos volver a "active": el
        # backend puede emitir un "ok" tardío de la fase justo antes del
        # abort, pero visualmente queremos preservar el estado "cancelling".
        if self._cancelling and status == "active":
            return
        now = time.monotonic()
        if status == "active" and phase.started_at is None:
            phase.started_at = now
        if status in ("done", "error") and phase.ended_at is None:
            phase.ended_at = now
        phase.status = status  # type: ignore[assignment]
        self._render_phase(phase)
        self._update_pipeline_footer()

    def _mark_active_as_cancelled(self) -> None:
        for p in self.gui_state.phases:
            if p.status in ("active", "cancelling"):
                if p.ended_at is None:
                    p.ended_at = time.monotonic()
                p.status = "cancelling"
                self._render_phase(p)
        self._update_pipeline_footer()

    def _mark_active_as_error(self) -> None:
        for p in self.gui_state.phases:
            if p.status == "active":
                if p.ended_at is None:
                    p.ended_at = time.monotonic()
                p.status = "error"
                self._render_phase(p)
        self._update_pipeline_footer()

    def _mark_remaining_done(self) -> None:
        for p in self.gui_state.phases:
            if p.status != "done":
                if p.started_at is None:
                    p.started_at = time.monotonic()
                if p.ended_at is None:
                    p.ended_at = time.monotonic()
                p.status = "done"
                self._render_phase(p)
        self._update_pipeline_footer()

    def _render_phase(self, phase: PhaseInfo) -> None:
        w = self._phase_widgets.get(phase.name)
        if w is None:
            return
        status = phase.status
        w["icon"].configure(
            text=_ICONS[status], text_color=_ICON_COLORS[status]
        )
        w["row"].configure(fg_color=_PHASE_ROW_BG[status])

        text = {
            "pending": "pendiente",
            "active": f"en curso · {_format_mmss(phase.duration_s)}",
            "cancelling": f"cancelando · {_format_mmss(phase.duration_s)}",
            "done": f"completada · {_format_mmss(phase.duration_s)}",
            "error": f"error · {_format_mmss(phase.duration_s)}",
        }[status]
        w["status"].configure(text=text)

    def _update_pipeline_footer(self) -> None:
        total = len(self.gui_state.phases)
        active_idx = next(
            (i for i, p in enumerate(self.gui_state.phases) if p.status == "active"),
            None,
        )
        done_count = sum(1 for p in self.gui_state.phases if p.status == "done")
        wall = (
            time.monotonic() - self.gui_state.run_started_at
            if self.gui_state.run_started_at is not None else 0
        )
        if active_idx is not None:
            text = f"Fase {active_idx + 1} de {total} · {_format_mmss(wall)} transcurridos"
        elif done_count == total:
            text = f"Pipeline completado · {_format_mmss(wall)} total"
        else:
            text = f"{done_count}/{total} fases completadas · {_format_mmss(wall)} transcurridos"
        self.pipeline_footer.configure(text=text)

    # ------------------------------------------------------------------
    # Ticker (wall clock + duración de la fase activa)
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        # El reloj global vive en el footer del bloque pipeline (`X
        # transcurridos`), no en el header — evita tener varios contadores
        # idénticos compitiendo por la atención.
        for p in self.gui_state.phases:
            if p.status in ("active", "cancelling"):
                self._render_phase(p)
        self._update_pipeline_footer()
        if self.controller.is_alive():
            self.after(1000, self._tick)

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def _on_cancel(self) -> None:
        self._cancelling = True
        self.cancel_btn.configure(state="disabled", text="Cancelando...")
        self.cancel_help_label.configure(
            text=(
                "Esperando a que termine la llamada actual al LLM "
                "(puede tardar hasta ~1 min). Los artefactos ya escritos "
                "se conservan en el directorio de salida."
            )
        )
        for p in self.gui_state.phases:
            if p.status == "active":
                p.status = "cancelling"
                self._render_phase(p)
        self.controller.cancel()

    def _finish_transition(self) -> None:
        self.app.show_result()
