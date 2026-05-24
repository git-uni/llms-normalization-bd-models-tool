"""Helpers de filesystem para el agente de descubrimiento.

Centraliza dos cosas:
- qué archivos/directorios del repo se ignoran siempre (ruido), y
- validación de rutas para impedir que el agente escape del repo clonado.
"""

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


def is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIRS


def is_excluded_file(path: Path) -> bool:
    name_lower = path.name.lower()
    for suffix in EXCLUDED_SUFFIXES:
        if name_lower.endswith(suffix):
            return True
    return False


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


def build_tree_summary(repo_root: Path, max_entries: int = 600) -> str:
    """Listado plano del repo, filtrado, con tamaño en bytes.

    Formato por línea: `<tipo> <ruta-relativa> [<bytes>]`
    donde <tipo> es 'd' (directorio) o 'f' (archivo).
    """
    repo_root = repo_root.resolve()
    lines: list[str] = []
    truncated = False

    def walk(current: Path) -> None:
        nonlocal truncated
        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name))
        except OSError:
            return
        for entry in entries:
            if len(lines) >= max_entries:
                truncated = True
                return
            rel = entry.relative_to(repo_root).as_posix()
            if entry.is_dir():
                if is_excluded_dir(entry.name):
                    continue
                lines.append(f"d {rel}/")
                walk(entry)
            else:
                if is_excluded_file(entry):
                    continue
                try:
                    size = entry.stat().st_size
                except OSError:
                    continue
                if size > MAX_FILE_BYTES:
                    continue
                lines.append(f"f {rel} [{size}]")

    walk(repo_root)
    if truncated:
        lines.append(f"... (árbol truncado a {max_entries} entradas)")
    return "\n".join(lines)
