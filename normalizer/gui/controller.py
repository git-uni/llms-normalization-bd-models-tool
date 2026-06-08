"""Capa de aplicación de la GUI.

`GuiController` orquesta los puntos de entrada del núcleo (`discover_from_url`,
`run_pipeline`) en un hilo trabajador, manteniendo el hilo de UI libre. La
comunicación de vuelta se hace a través de una `queue.Queue` que el hilo de UI
consume con `app.after(100, ...)` (patrón estándar para Tkinter, que no es
*thread-safe*).

El controlador no conoce nada de *widgets*. Solo consume el estado validado
por la pantalla de configuración (`GuiState`) y emite eventos planos.

Además, el módulo expone los *helpers* que la pantalla de configuración
necesita: `ENV_KEY_BY_PROVIDER` (mapeo proveedor → variable de entorno),
`resolve_default_out_dir()` y `persist_api_key()`.
"""

import os
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue

from dotenv import set_key

from normalizer._log import register_callback, unregister_callback
from normalizer.discovery import discover_from_url
from normalizer.gui.state import GuiState
from normalizer.pipeline import PipelineCancelled, run_pipeline
from normalizer.providers import build_provider

# Mapeo proveedor → variable de entorno con su API key. La GUI lo usa para
# detectar credenciales ya configuradas y para persistir nuevas vía dotenv.
ENV_KEY_BY_PROVIDER: dict[str, str] = {
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}


def resolve_default_out_dir(prefix: str = "out-gui") -> Path:
    """Devuelve `<prefix>-YYYYMMDD-HHMMSS/` en el directorio de trabajo."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / f"{prefix}-{ts}"


def persist_api_key(env_key: str, value: str) -> None:
    """Inyecta en `os.environ` y persiste en `.env` (creándolo si no existe).

    Usa `dotenv.set_key`, que añade o reemplaza la línea correspondiente sin
    tocar el resto del fichero.
    """
    value = value.strip()
    if not value:
        return
    os.environ[env_key] = value
    env_path = Path.cwd() / ".env"
    env_path.touch(exist_ok=True)
    set_key(str(env_path), env_key, value, quote_mode="never")


@dataclass(frozen=True)
class LogLineEvent:
    line: str


@dataclass(frozen=True)
class DoneEvent:
    out_dir: Path


@dataclass(frozen=True)
class CancelledEvent:
    out_dir: Path


@dataclass(frozen=True)
class ErrorEvent:
    phase: str
    message: str
    out_dir: Path


ControllerEvent = LogLineEvent | DoneEvent | CancelledEvent | ErrorEvent


class GuiController:
    """Orquesta el núcleo en un hilo trabajador y publica eventos a UI."""

    def __init__(self) -> None:
        self._queue: Queue[ControllerEvent] = Queue()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_phase = ""

    def start(self, state: GuiState) -> None:
        """Lanza el núcleo en un hilo trabajador. No bloquea."""
        if self.is_alive():
            return
        self._cancel.clear()
        self._last_phase = ""
        register_callback(self._on_log_line)
        self._thread = threading.Thread(
            target=self._run, args=(state,), daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        """Señaliza la cancelación. El núcleo aborta entre fases/iteraciones."""
        self._cancel.set()

    def is_alive(self) -> bool:
        """`True` mientras el hilo trabajador está vivo."""
        return self._thread is not None and self._thread.is_alive()

    def drain(self) -> list[ControllerEvent]:
        """Vacía la cola y devuelve los eventos pendientes (no bloqueante)."""
        events: list[ControllerEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events

    def _on_log_line(self, line: str) -> None:
        # Se llama desde el hilo trabajador (el de _log.log). Solo encolamos;
        # ningún widget se toca aquí (Tkinter no es thread-safe).
        self._update_phase_from_line(line)
        self._queue.put(LogLineEvent(line))

    def _update_phase_from_line(self, line: str) -> None:
        # Inferencia de la fase en curso a partir de las marcas que ya emite
        # el núcleo. Si el LLM falla, sabemos en qué fase estaba el proceso
        # y la GUI lo muestra en el banner de error.
        msg = line.split("] ", 1)[-1] if "] " in line else line
        if msg.startswith("Descubriendo evidencia"):
            self._last_phase = "Descubrimiento"
        elif msg.startswith("Pipeline: ANÁLISIS") and not msg.endswith("ok"):
            self._last_phase = "Análisis"
        elif msg.startswith("Pipeline: DISEÑO") and not msg.endswith("ok"):
            self._last_phase = "Diseño"
        elif msg.startswith("Pipeline: DDL") and not msg.endswith("ok"):
            self._last_phase = "DDL"

    def _run(self, state: GuiState) -> None:
        assert state.out_dir is not None, "out_dir debe estar resuelto"
        out_dir = state.out_dir
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            pipeline_provider = build_provider(
                name=state.provider,
                model=state.model or None,
            )
            if state.is_url:
                agent_provider = build_provider(
                    name=state.provider,
                    model=state.agent_model or None,
                    for_agent=True,
                )
                pipeline_input = discover_from_url(
                    url=state.input_value,
                    agent_provider=agent_provider,
                    out_dir=out_dir,
                    cancel_event=self._cancel,
                )
            else:
                pipeline_input = Path(state.input_value)

            run_pipeline(
                input_path=pipeline_input,
                provider=pipeline_provider,
                out_dir=out_dir,
                cancel_event=self._cancel,
            )
            self._queue.put(DoneEvent(out_dir=out_dir))
        except PipelineCancelled:
            self._queue.put(CancelledEvent(out_dir=out_dir))
        except Exception as e:
            # Traceback completo a stderr para depuración (queda en el log
            # del usuario); a la UI solo el resumen + la fase.
            traceback.print_exc()
            self._queue.put(
                ErrorEvent(
                    phase=self._last_phase or "Inicialización",
                    message=str(e) or e.__class__.__name__,
                    out_dir=out_dir,
                )
            )
        finally:
            unregister_callback(self._on_log_line)
