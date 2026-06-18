"""Paquete de la interfaz de línea de comandos.

El código vive en el módulo hermano `cli.py`; este `__init__` solo re-exporta
el punto de entrada `main`, de modo que el *console_script* `normalizer.cli:main`
y los `from normalizer.cli import main` sigan resolviendo sin cambios.
"""

from normalizer.cli.cli import main

__all__ = ["main"]
