"""Clonado superficial y cacheado de repositorios públicos."""

import hashlib
import subprocess
from pathlib import Path

CACHE_DIR = Path(".cache") / "repos"


def clone_repo(url: str, cache_root: Path | None = None) -> Path:
    """Clona `url` a un directorio local cacheado y devuelve su ruta.

    Si el repo ya está clonado en cache se reutiliza sin re-descargar. El
    clonado es `--depth 1` para no traer toda la historia.
    """
    cache_root = (cache_root or CACHE_DIR).resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    target = cache_root / digest

    if target.exists() and (target / ".git").exists():
        return target

    if target.exists():
        # Directorio a medias de un intento anterior: limpiar y reintentar.
        _rmtree(target)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("`git` no está disponible en el PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git clone falló para {url}:\n{exc.stderr or exc.stdout}"
        ) from exc

    return target


def _rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)
