"""Estado mutable de la sesión de GUI.

Una instancia única vive en `NormalizerApp.gui_state` y se pasa entre
pantallas. Solo contiene tipos elementales (cadenas, rutas, enumeraciones)
y referencias a artefactos en disco — la capa de presentación no manipula
objetos del subsistema de proveedor ni del agente (decisión arquitectónica
§5.2.7 de la memoria).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

InputMode = Literal["file", "dir", "url"]


@dataclass
class GuiState:
    # Bloque rellenado en la pantalla de configuración.
    input_mode: InputMode = "file"
    input_value: str = ""
    provider: str = "google"
    model: str = ""  # cadena vacía → usar default del proveedor
    agent_model: str = ""
    out_dir: Path | None = None  # None → autogenerar `out-gui-<ts>/`

    # Bloque rellenado durante la ejecución.
    error_message: str = ""
    error_phase: str = ""
    cancelled: bool = False
    finished_ok: bool = False
    log_lines: list[str] = field(default_factory=list)
    agent_turns: list[tuple[int, str]] = field(default_factory=list)

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
