"""Helpers de filesystem para el agente de descubrimiento.

Centraliza dos cosas:
- qué archivos/directorios del repo se ignoran siempre (ruido), y
- validación de rutas para impedir que el agente escape del repo clonado.
"""

from collections import deque
from pathlib import Path

EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".github",
        ".vscode",
        ".idea",
        "node_modules",
        "bower_components",
        "vendor",
        "dist",
        "build",
        "out",
        "target",
        "coverage",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".cache",
        ".next",
        ".nuxt",
        ".venv",
        "venv",
        "env",
    }
)

EXCLUDED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".min.js",
        ".min.css",
        ".map",
        ".lock",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".mp3",
        ".mp4",
        ".mov",
        ".wav",
        ".class",
        ".jar",
        ".pyc",
        ".so",
        ".dll",
        ".exe",
    }
)

MAX_FILE_BYTES = 200_000

# Sufijos de archivos que se omiten del DUMP del árbol inicial pero NO se
# excluyen globalmente. El agente puede seguir leyéndolos o grepeándolos si
# encuentra su path por otra vía (p. ej. un `grep` da hit en un .test.js
# que contiene un schema de fixture). Razón de la exclusión local:
# repos grandes (Habitica: 4000+ archivos) generan demasiado ruido de
# tests en el árbol y agotan el cap sin aportar señal.
TREE_SKIP_SUFFIXES: frozenset[str] = frozenset(
    {
        ".test.js",
        ".test.ts",
        ".test.jsx",
        ".test.tsx",
        ".spec.js",
        ".spec.ts",
    }
)


def is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIRS


def is_excluded_file(path: Path) -> bool:
    name_lower = path.name.lower()
    for suffix in EXCLUDED_SUFFIXES:
        if name_lower.endswith(suffix):
            return True
    return False


def _skip_in_tree(path: Path) -> bool:
    name_lower = path.name.lower()
    return any(name_lower.endswith(s) for s in TREE_SKIP_SUFFIXES)


def resolve_within(repo_root: Path, rel_path: str) -> Path:
    """Resuelve `rel_path` dentro de `repo_root` y rechaza escapes.

    Acepta tanto "" o "." (raíz del repo) como rutas relativas con `/` o `\\`.
    Lanza ValueError si la ruta apunta fuera del repo.
    """
    repo_root = repo_root.resolve()
    cleaned = (rel_path or "").strip().lstrip("/\\")
    if cleaned in ("", "."):
        return repo_root
    candidate = (repo_root / cleaned).resolve()
    if not _is_relative_to(candidate, repo_root):
        raise ValueError(f"Ruta fuera del repo: {rel_path!r}")
    return candidate


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def build_tree_summary(repo_root: Path, max_entries: int = 2000) -> str:
    """Listado plano del repo, filtrado, con tamaño en bytes.

    Formato por línea: `<tipo> <ruta-relativa> [<bytes>]`
    donde <tipo> es 'd' (directorio) o 'f' (archivo).

    Recorrido **BFS por niveles** (no DFS): primero se enumera todo el nivel
    raíz, luego nivel 1, etc. Garantía que da BFS: si el cap se agota, los
    top-level dirs ya han aparecido completos. DFS alfabético antes podía
    consumirse 600 entradas dentro de `test/` antes de llegar a `website/`,
    dejando dirs candidatos sin visibilidad en el primer mensaje del agente.

    Archivos cuyo sufijo está en `TREE_SKIP_SUFFIXES` (tests `.test.js` /
    `.spec.ts`, etc.) se omiten del árbol para que no acaparen el cap, pero
    siguen siendo accesibles vía `read_file`/`grep` si el agente los
    encuentra por otra vía.
    """
    repo_root = repo_root.resolve()
    lines: list[str] = []
    queue: deque[Path] = deque([repo_root])
    truncated = False

    while queue and not truncated:
        current = queue.popleft()
        try:
            entries = sorted(
                current.iterdir(), key=lambda p: (p.is_file(), p.name)
            )
        except OSError:
            continue
        for entry in entries:
            if len(lines) >= max_entries:
                truncated = True
                break
            rel = entry.relative_to(repo_root).as_posix()
            if entry.is_dir():
                if is_excluded_dir(entry.name):
                    continue
                lines.append(f"d {rel}/")
                queue.append(entry)
            else:
                if is_excluded_file(entry) or _skip_in_tree(entry):
                    continue
                try:
                    size = entry.stat().st_size
                except OSError:
                    continue
                if size > MAX_FILE_BYTES:
                    continue
                lines.append(f"f {rel} [{size}]")

    if truncated:
        lines.append(f"... (árbol truncado a {max_entries} entradas)")
    return "\n".join(lines)
