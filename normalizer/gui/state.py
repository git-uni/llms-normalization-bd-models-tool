"""Estado mutable de la sesión de GUI.

Una instancia única vive en `NormalizerApp.gui_state` y se pasa entre
pantallas. Solo contiene tipos elementales (cadenas, rutas, enumeraciones)
y referencias a artefactos en disco, la capa de presentación no manipula
objetos del subsistema de proveedor ni del agente (decisión arquitectónica
§5.2.7 de la memoria).
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from normalizer.discovery import MAX_FILES, MAX_ITERS, MAX_TREE_ENTRIES

InputMode = Literal["file", "dir", "url"]
PhaseStatus = Literal["pending", "active", "done", "error", "cancelling"]


@dataclass
class PhaseInfo:
    """Estado de una fase del pipeline con timestamps para medir duración."""

    name: str
    status: PhaseStatus = "pending"
    started_at: float | None = None  # time.monotonic() al pasar a active
    ended_at: float | None = None    # time.monotonic() al pasar a done/error

    @property
    def duration_s(self) -> float:
        """Segundos transcurridos (en curso o totales si ya terminó)."""
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else time.monotonic()
        return max(0.0, end - self.started_at)


@dataclass
class GuiState:
    # Bloque rellenado en la pantalla de configuración.
    input_mode: InputMode = "file"
    input_value: str = ""
    provider: str = "google"
    model: str = ""  # cadena vacía → usar default del proveedor
    agent_model: str = ""
    out_dir: Path | None = None  # None → autogenerar `out-gui-<ts>/`
    # Presupuesto del agente (solo aplica en modo URL). Defaults = constantes
    # del núcleo, así una única fuente de verdad gobierna CLI y GUI.
    max_iters: int = MAX_ITERS
    max_files: int = MAX_FILES
    max_tree_entries: int = MAX_TREE_ENTRIES

    # Bloque rellenado durante la ejecución.
    error_message: str = ""
    error_phase: str = ""
    cancelled: bool = False
    finished_ok: bool = False
    log_lines: list[str] = field(default_factory=list)
    agent_turns: list[tuple[int, str]] = field(default_factory=list)
    phases: list[PhaseInfo] = field(default_factory=list)
    run_started_at: float | None = None  # wall clock de la corrida actual

    @property
    def is_url(self) -> bool:
        return self.input_mode == "url"

    def reset_run(self) -> None:
        self.error_message = ""
        self.error_phase = ""
        self.cancelled = False
        self.finished_ok = False
        self.log_lines = []
        self.agent_turns = []
        # phases las inicializa RunScreen según el modo (URL incluye
        # Descubrimiento; archivo/directorio no).
        self.phases = []
        self.run_started_at = time.monotonic()
