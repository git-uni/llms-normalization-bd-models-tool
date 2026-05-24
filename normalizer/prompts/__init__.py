"""Prompts del pipeline y del agente, cargados desde archivos .md hermanos.

Editar los .md y volver a correr basta para intercambiar un prompt: no hace
falta tocar Python. Los placeholders (`{evidence}`, `{analysis}`, `{design}`)
siguen el formato de `str.format`.
"""

from pathlib import Path

_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")


ANALYZE = _load("analyze")
DESIGN = _load("design")
DDL = _load("ddl")
DISCOVERY_SYSTEM = _load("discovery_system")

__all__ = ["ANALYZE", "DESIGN", "DDL", "DISCOVERY_SYSTEM"]
