"""Tools expuestas al agente de descubrimiento.

Define las `ToolSpec` (formato JSON Schema), un `DiscoveryState` que acumula
las decisiones del agente y un `dispatch()` que ejecuta cualquier ToolCall.
"""

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from normalizer.discovery.filesystem import (
    MAX_FILE_BYTES,
    is_excluded_dir,
    is_excluded_file,
    resolve_within,
)
from normalizer.providers import ToolCall, ToolSpec

READ_FILE_CAP = 50_000
GREP_MAX_HITS = 50


@dataclass
class SelectedEvidence:
    rel_path: str
    reason: str


@dataclass
class TurnTrace:
    """Registro compacto de las tool_calls que el modelo emitió en un turno.

    Sirve para inspeccionar a posteriori si el agente batchea varios calls en
    una sola petición o va uno a uno, relevante para entender el consumo de
    RPM en repos grandes.
    """

    iter: int
    calls: list[str]


@dataclass
class DiscoveryState:
    repo_root: Path
    discovery_dir: Path
    evidence_dir: Path = field(init=False)
    selected: list[SelectedEvidence] = field(default_factory=list)
    turns: list[TurnTrace] = field(default_factory=list)
    is_done: bool = False
    summary: str | None = None

    def __post_init__(self) -> None:
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir = self.discovery_dir / "evidence"
        # Limpiar evidencia de runs anteriores para evitar leaks entre
        # ejecuciones (lo que pasó cuando un retry externo añadió archivos
        # sobre los del run anterior).
        if self.evidence_dir.exists():
            for item in self.evidence_dir.iterdir():
                if item.is_file():
                    item.unlink()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def add_selection(self, rel_path: str, reason: str) -> SelectedEvidence:
        sel = SelectedEvidence(rel_path=rel_path, reason=reason)
        self.selected.append(sel)
        return sel

    def already_selected(self, rel_path: str) -> bool:
        return any(s.rel_path == rel_path for s in self.selected)


TOOL_LIST_DIR = ToolSpec(
    name="list_dir",
    description=(
        "Lista el contenido de un directorio del repositorio clonado. Usa una "
        "ruta relativa a la raíz (cadena vacía o '.' para la raíz). Devuelve "
        "una entrada por línea con prefijo 'd' (directorio) o 'f' (archivo) y "
        "el tamaño en bytes. Se excluyen automáticamente directorios irrelevantes "
        "(node_modules, .git, dist, build, etc.) y archivos binarios."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Ruta relativa al repo. Vacío o '.' = raíz.",
            }
        },
        "required": ["path"],
    },
)

TOOL_READ_FILE = ToolSpec(
    name="read_file",
    description=(
        f"Lee el contenido de un archivo de texto. La salida se trunca a "
        f"{READ_FILE_CAP} bytes (se indica si fue truncada)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Ruta relativa al repo del archivo a leer.",
            }
        },
        "required": ["path"],
    },
)

TOOL_GREP = ToolSpec(
    name="grep",
    description=(
        f"Busca un patrón (regex Python) en los archivos del repo. Devuelve "
        f"hasta {GREP_MAX_HITS} coincidencias con formato 'ruta:linea:texto'. "
        f"Útil para localizar accesos a la BD (`mongoose.Schema`, `.find(`, "
        f"`new Schema`, `collection`, `.aggregate`, etc.)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Expresión regular Python a buscar.",
            },
            "glob": {
                "type": "string",
                "description": (
                    "Glob opcional para filtrar archivos (p. ej. '*.js'). "
                    "Vacío = todos los archivos de texto."
                ),
            },
        },
        "required": ["pattern"],
    },
)

TOOL_SELECT_EVIDENCE = ToolSpec(
    name="select_evidence",
    description=(
        "Marca un archivo como evidencia relevante del modelo documental. El "
        "archivo se copiará al directorio de evidencia que alimenta al "
        "pipeline. Incluye una razón concreta: qué entidades o relaciones "
        "aporta el archivo."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Ruta relativa al repo del archivo a incluir.",
            },
            "reason": {
                "type": "string",
                "description": (
                    "Justificación breve: por qué este archivo aporta "
                    "evidencia sobre el modelo de datos."
                ),
            },
        },
        "required": ["path", "reason"],
    },
)

TOOL_DONE = ToolSpec(
    name="done",
    description=(
        "Termina el descubrimiento. Llama a esta tool cuando consideres que "
        "la evidencia seleccionada es suficiente para reconstruir el modelo "
        "documental completo. Incluye un resumen del modelo detectado y de "
        "los archivos elegidos."
    ),
    parameters={
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": (
                    "Resumen del modelo documental detectado y de la "
                    "evidencia recopilada."
                ),
            }
        },
        "required": ["summary"],
    },
)

ALL_TOOLS: list[ToolSpec] = [
    TOOL_LIST_DIR,
    TOOL_READ_FILE,
    TOOL_GREP,
    TOOL_SELECT_EVIDENCE,
    TOOL_DONE,
]


def dispatch(call: ToolCall, state: DiscoveryState, max_files: int) -> str:
    """Ejecuta una ToolCall y devuelve su resultado como texto.

    El texto devuelto es lo que se reinyecta al modelo en el siguiente turno
    (como mensaje de rol "tool").
    """
    args = call.arguments or {}
    if call.name == "list_dir":
        return _do_list_dir(state.repo_root, args.get("path", ""))
    if call.name == "read_file":
        return _do_read_file(state.repo_root, state, args.get("path", ""))
    if call.name == "grep":
        return _do_grep(
            state.repo_root,
            pattern=args.get("pattern", ""),
            glob=args.get("glob") or None,
        )
    if call.name == "select_evidence":
        return _do_select(
            state,
            rel_path=args.get("path", ""),
            reason=args.get("reason", ""),
            max_files=max_files,
        )
    if call.name == "done":
        state.is_done = True
        state.summary = args.get("summary", "")
        return "ok"
    return f"ERROR: tool desconocida '{call.name}'"


def _do_list_dir(repo_root: Path, rel_path: str) -> str:
    try:
        target = resolve_within(repo_root, rel_path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not target.exists():
        return f"ERROR: no existe '{rel_path}'"
    if not target.is_dir():
        return f"ERROR: '{rel_path}' no es un directorio"

    lines: list[str] = []
    try:
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    except OSError as e:
        return f"ERROR: {e}"
    for entry in entries:
        rel = entry.relative_to(repo_root).as_posix()
        if entry.is_dir():
            if is_excluded_dir(entry.name):
                continue
            lines.append(f"d {rel}/")
        else:
            if is_excluded_file(entry):
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                continue
            lines.append(f"f {rel} [{size}]")
    return "\n".join(lines) if lines else "(directorio vacío tras el filtrado)"


def _do_read_file(
    repo_root: Path, state: DiscoveryState, rel_path: str
) -> str:
    # Releer un archivo que ya marcaste como evidencia no aporta nada nuevo
    # (su contenido ya entra al pipeline) y gasta cuota duplicando los
    # tokens del archivo en el historial. Cortamos antes de leer del disco.
    if state.already_selected(rel_path):
        return (
            f"Ya seleccionado como evidencia: '{rel_path}'. Su contenido "
            "pasa al pipeline; no necesitas releerlo. Si quieres verificar "
            "un detalle puntual, usa `grep` con un patrón específico."
        )
    try:
        target = resolve_within(repo_root, rel_path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not target.exists():
        return f"ERROR: no existe '{rel_path}'"
    if not target.is_file():
        return f"ERROR: '{rel_path}' no es un archivo"
    if is_excluded_file(target):
        return f"ERROR: archivo excluido por tipo: '{rel_path}'"
    try:
        size = target.stat().st_size
    except OSError as e:
        return f"ERROR: {e}"
    if size > MAX_FILE_BYTES:
        return f"ERROR: archivo demasiado grande ({size} bytes)"
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"ERROR: archivo no decodificable como UTF-8: '{rel_path}'"
    except OSError as e:
        return f"ERROR: {e}"
    if len(text) > READ_FILE_CAP:
        text = text[:READ_FILE_CAP] + f"\n... (truncado a {READ_FILE_CAP} bytes)"
    return text


def _do_grep(repo_root: Path, pattern: str, glob: str | None) -> str:
    if not pattern:
        return "ERROR: patrón vacío"
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: regex inválida: {e}"

    hits: list[str] = []
    iterator = repo_root.rglob(glob) if glob else repo_root.rglob("*")
    for path in iterator:
        if not path.is_file():
            continue
        if any(is_excluded_dir(part) for part in path.relative_to(repo_root).parts[:-1]):
            continue
        if is_excluded_file(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(repo_root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                snippet = line.strip()
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                hits.append(f"{rel}:{lineno}:{snippet}")
                if len(hits) >= GREP_MAX_HITS:
                    hits.append(f"... (cortado en {GREP_MAX_HITS} coincidencias)")
                    return "\n".join(hits)
    return "\n".join(hits) if hits else "(sin coincidencias)"


def _do_select(
    state: DiscoveryState, rel_path: str, reason: str, max_files: int
) -> str:
    if not rel_path or not reason:
        return "ERROR: 'path' y 'reason' son obligatorios"
    if state.already_selected(rel_path):
        return f"ya seleccionado previamente: '{rel_path}'"
    if len(state.selected) >= max_files:
        return f"ERROR: límite de {max_files} archivos alcanzado; llama a `done`"
    try:
        target = resolve_within(state.repo_root, rel_path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not target.is_file():
        return f"ERROR: '{rel_path}' no es un archivo"
    if is_excluded_file(target):
        return f"ERROR: tipo de archivo excluido: '{rel_path}'"
    try:
        size = target.stat().st_size
    except OSError as e:
        return f"ERROR: {e}"
    if size > MAX_FILE_BYTES:
        return (
            f"ERROR: archivo demasiado grande ({size} bytes); "
            "usa `grep` para localizar fragmentos relevantes"
        )

    # Copiar al directorio de evidencia con nombre aplanado para evitar
    # colisiones y mantener el directorio del pipeline plano (no recursivo).
    flat_name = rel_path.replace("/", "__").replace("\\", "__")
    dest = state.evidence_dir / flat_name
    try:
        shutil.copyfile(target, dest)
    except OSError as e:
        return f"ERROR: copia falló: {e}"

    state.add_selection(rel_path=rel_path, reason=reason)
    return f"seleccionado: '{rel_path}' ({size} bytes)"
