import threading
import time
from pathlib import Path

from normalizer._log import log
from normalizer.prompts import ANALYZE, DDL, DESIGN
from normalizer.providers import LLMProvider


class PipelineCancelled(Exception):
    """Cancelación cooperativa solicitada por el usuario.

    El núcleo (pipeline y agente) la levanta cuando detecta el `cancel_event`
    señalizado entre fases o entre iteraciones. Los artefactos ya escritos a
    disco se preservan: la cancelación es limpia, no destruye estado parcial.
    """


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise PipelineCancelled()


def _read_input(input_path: Path) -> str:
    """Concatena los archivos del input en un único bundle de texto.

    Acepta archivo único o directorio (no recursivo). Los archivos que no se
    puedan decodificar como UTF-8 se saltan.
    """
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(p for p in input_path.iterdir() if p.is_file())
    if not files:
        raise RuntimeError(f"No se encontraron archivos en {input_path}")

    parts: list[str] = []
    skipped: list[str] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(f.name)
            continue
        parts.append(f"// === {f.name} ===")
        parts.append(text)

    if not parts:
        raise RuntimeError(f"Ningún archivo legible como texto en {input_path}")
    if skipped:
        parts.append(f"// (archivos saltados por no ser texto: {', '.join(skipped)})")

    return "\n\n".join(parts)


def run_pipeline(
    input_path: Path,
    provider: LLMProvider,
    out_dir: Path,
    cancel_event: threading.Event | None = None,
) -> str:
    """Ejecuta las tres fases del pipeline (análisis, diseño, DDL).

    `input_path` es un archivo único o un directorio (no recursivo). Cada
    fase escribe su artefacto en `out_dir` antes de continuar, de modo que
    los resultados parciales son inspeccionables si la corrida se interrumpe.

    `cancel_event` (opcional) permite a un caller externo (típicamente la
    GUI) cancelar la corrida entre fases. Si está señalizado, se levanta
    `PipelineCancelled` y los artefactos ya escritos se preservan.
    """
    _check_cancel(cancel_event)
    evidence = _read_input(input_path)
    (out_dir / "01_input.txt").write_text(evidence, encoding="utf-8")
    _check_cancel(cancel_event)

    log("Pipeline: ANÁLISIS ...")
    t0 = time.monotonic()
    analysis = provider.generate(ANALYZE.format(evidence=evidence))
    (out_dir / "02_analysis.md").write_text(analysis, encoding="utf-8")
    log(f"Pipeline: ANÁLISIS ok ({int(time.monotonic() - t0)}s)")
    _check_cancel(cancel_event)

    log("Pipeline: DISEÑO ...")
    t0 = time.monotonic()
    design = provider.generate(DESIGN.format(analysis=analysis))
    (out_dir / "03_design.md").write_text(design, encoding="utf-8")
    log(f"Pipeline: DISEÑO ok ({int(time.monotonic() - t0)}s)")
    _check_cancel(cancel_event)

    log("Pipeline: DDL ...")
    t0 = time.monotonic()
    ddl = provider.generate(DDL.format(design=design))
    (out_dir / "04_ddl.sql").write_text(ddl, encoding="utf-8")
    log(f"Pipeline: DDL ok ({int(time.monotonic() - t0)}s)")

    return ddl
