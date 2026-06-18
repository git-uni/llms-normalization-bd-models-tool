"""Paquete del *pipeline* de transformación.

El código vive en el módulo hermano `pipeline.py`; este `__init__` re-exporta
la API pública (`run_pipeline` y la excepción `PipelineCancelled`) para que los
`from normalizer.pipeline import ...` del resto del sistema sigan resolviendo
sin cambios.
"""

from normalizer.pipeline.pipeline import PipelineCancelled, run_pipeline

__all__ = ["PipelineCancelled", "run_pipeline"]
