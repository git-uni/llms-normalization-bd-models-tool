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

from normalizer._log import log, register_callback, reset_clock, unregister_callback
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
        self._abandoned = False
        # Identidad del hilo trabajador de esta corrida. `_on_log_line` la usa
        # para descartar líneas que emita un hilo abandonado de otra corrida
        # (tras Cancelar, ese hilo sigue vivo y sigue llamando a `log()`).
        self._worker_ident: int | None = None

    def start(self, state: GuiState) -> None:
        """Lanza el núcleo en un hilo trabajador. No bloquea."""
        if self.is_alive():
            return
        self._cancel.clear()
        self._abandoned = False
        self._last_phase = ""
        # Reinicia el reloj relativo del log: la primera línea de la corrida
        # debe marcar [00:00], no acumular el tiempo de configuración.
        reset_clock()
        register_callback(self._on_log_line)
        self._thread = threading.Thread(
            target=self._run, args=(state,), daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        """Señaliza la cancelación. El núcleo aborta entre fases/iteraciones."""
        self._cancel.set()

    def cancel_and_abandon(self) -> None:
        """Pulsa cancel y desvincula este controlador del hilo trabajador.

        La llamada HTTP al LLM en curso no se puede abortar (los SDKs son
        síncronos y bloqueantes), pero la UI no tiene por qué esperarla:
        marcamos el controlador como abandonado para que el hilo (cuando
        termine) no contamine la pantalla siguiente ni futuras corridas,
        y desregistramos el *callback* del log inmediatamente. El hilo
        sigue vivo como `daemon` y muere con el proceso o cuando la
        llamada HTTP termine; los artefactos ya escritos a disco se
        conservan.
        """
        self._cancel.set()
        self._abandoned = True
        unregister_callback(self._on_log_line)

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
        if self._abandoned:
            return
        # `log()` difunde a todos los callbacks registrados. Una corrida nueva
        # registra su callback mientras el hilo abandonado de la anterior sigue
        # vivo emitiendo líneas; las descartamos comparando identidades de hilo
        # para que no se cuelen en el log de la corrida nueva.
        if threading.get_ident() != self._worker_ident:
            return
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
        # Se fija aquí, en el propio hilo trabajador y antes de cualquier
        # `log()`, para que `_on_log_line` reconozca nuestras líneas.
        self._worker_ident = threading.get_ident()
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
                # Paridad con la CLI (cli.py): estas dos marcas hacen que
                # RunScreen marque la fase Descubrimiento como activa (fija
                # started_at) al empezar y como completada (fija ended_at) al
                # terminar. Sin ellas la fase nunca arranca su reloj y su
                # duración sale 00:00. La de "Evidencia en" tras el retorno
                # cubre también el caso de presupuesto agotado (sin "Agente done").
                log(f"Descubriendo evidencia desde {state.input_value}...")
                pipeline_input = discover_from_url(
                    url=state.input_value,
                    agent_provider=agent_provider,
                    out_dir=out_dir,
                    max_iters=state.max_iters,
                    max_files=state.max_files,
                    max_tree_entries=state.max_tree_entries,
                    cancel_event=self._cancel,
                )
                log(
                    f"Evidencia en {pipeline_input} "
                    f"(traza en {out_dir}/00_discovery/discovery.md)"
                )
            else:
                pipeline_input = Path(state.input_value)

            run_pipeline(
                input_path=pipeline_input,
                provider=pipeline_provider,
                out_dir=out_dir,
                cancel_event=self._cancel,
            )
            if not self._abandoned:
                self._queue.put(DoneEvent(out_dir=out_dir))
        except PipelineCancelled:
            if not self._abandoned:
                self._queue.put(CancelledEvent(out_dir=out_dir))
        except Exception as e:
            # Traceback completo a stderr para depuración (queda en el log
            # del usuario); a la UI solo el resumen + la fase.
            traceback.print_exc()
            if not self._abandoned:
                self._queue.put(
                    ErrorEvent(
                        phase=self._last_phase or "Inicialización",
                        message=str(e) or e.__class__.__name__,
                        out_dir=out_dir,
                    )
                )
        finally:
            unregister_callback(self._on_log_line)
