from pathlib import Path

import click
from dotenv import load_dotenv

from normalizer._log import log
from normalizer.discovery import (
    MAX_FILES,
    MAX_ITERS,
    MAX_TREE_ENTRIES,
    discover_from_url,
)
from normalizer.pipeline import run_pipeline
from normalizer.providers import available_providers, build_provider


@click.command()
@click.argument("input_path", type=str)
@click.option(
    "--provider",
    "provider_name",
    type=click.Choice(available_providers()),
    default="google",
    show_default=True,
    help="Proveedor de LLM.",
)
@click.option(
    "--model",
    default=None,
    help="Modelo del pipeline (analyze/design/DDL). Si no se indica se usa el por defecto.",
)
@click.option(
    "--agent-model",
    default=None,
    help=(
        "Modelo del agente de descubrimiento (solo aplica si INPUT_PATH es una "
        "URL). Requiere soporte de function-calling. Default por proveedor."
    ),
)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directorio donde se guardan los artefactos del pipeline.",
)
@click.option(
    "--max-tree-entries",
    type=int,
    default=MAX_TREE_ENTRIES,
    show_default=True,
    help=(
        "Máximo de entradas del árbol del repositorio que se entrega al agente "
        "(solo aplica si INPUT_PATH es una URL). Reducirlo ayuda con los "
        "límites de cuota (TPM) sobre repositorios grandes."
    ),
)
@click.option(
    "--max-iters",
    type=int,
    default=MAX_ITERS,
    show_default=True,
    help="Máximo de iteraciones del agente (solo aplica si INPUT_PATH es una URL).",
)
@click.option(
    "--max-files",
    type=int,
    default=MAX_FILES,
    show_default=True,
    help=(
        "Máximo de archivos que el agente puede seleccionar como evidencia "
        "(solo aplica si INPUT_PATH es una URL)."
    ),
)
def main(
    input_path: str,
    provider_name: str,
    model: str | None,
    agent_model: str | None,
    out_dir: Path,
    max_tree_entries: int,
    max_iters: int,
    max_files: int,
) -> None:
    """Normaliza un modelo documental MongoDB a DDL Oracle vía LLM.

    INPUT_PATH puede ser:

    - un archivo único con fragmentos relevantes (schemas, consultas, ejemplos
      de documentos, accesos a campos, etc.) recopilados manualmente,

    - un directorio que contenga esos fragmentos en varios archivos (no
      recursivo: se asume que el directorio ya está curado),

    - o una URL de un repositorio Git público (`http(s)://...` o `git@...`):
      en ese caso un agente clona el repo, localiza por sí mismo la evidencia
      relevante y luego corre el pipeline sobre ella.
    """
    load_dotenv()
    out_dir.mkdir(parents=True, exist_ok=True)

    is_url = _is_url(input_path)
    if not is_url:
        pipeline_input = Path(input_path)
        if not pipeline_input.exists():
            raise click.BadParameter(f"No existe: {input_path}")

    agent_provider = (
        build_provider(name=provider_name, model=agent_model, for_agent=True)
        if is_url
        else None
    )
    pipeline_provider = build_provider(name=provider_name, model=model)

    agent_part = f" | agent={agent_provider.model}" if agent_provider else ""
    log(
        f"Provider: {provider_name} | pipeline={pipeline_provider.model}"
        f"{agent_part} | out={out_dir}/"
    )

    if is_url:
        log(f"Descubriendo evidencia desde {input_path}...")
        evidence_dir = discover_from_url(
            url=input_path,
            agent_provider=agent_provider,
            out_dir=out_dir,
            max_iters=max_iters,
            max_files=max_files,
            max_tree_entries=max_tree_entries,
        )
        log(
            f"Evidencia en {evidence_dir} "
            f"(traza en {out_dir}/00_discovery/discovery.md)"
        )
        pipeline_input = evidence_dir

    run_pipeline(
        input_path=pipeline_input, provider=pipeline_provider, out_dir=out_dir
    )
    log(f"DDL generado en {out_dir / '04_ddl.sql'}")
    log(
        f"Artefactos intermedios en {out_dir}/ (01_input, 02_analysis, 03_design)"
    )


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@"))


if __name__ == "__main__":
    main()
