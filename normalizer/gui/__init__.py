"""Interfaz gráfica del normalizer (CustomTkinter).

Capa de presentación que envuelve el mismo núcleo que la CLI
(`run_pipeline`, `discover_from_url`) en una experiencia guiada de tres
pantallas: configuración, ejecución con progreso y visualización del
resultado. Lanzamiento:

    python -m normalizer.gui
"""

from normalizer.gui.app import main

__all__ = ["main"]
