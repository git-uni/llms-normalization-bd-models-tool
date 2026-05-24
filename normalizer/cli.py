from pathlib import Path

import click
from dotenv import load_dotenv

from normalizer.discovery import discover_from_url
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
def main(
    input_path: str,
    provider_name: str,
    model: str | None,
    agent_model: str | None,
    out_dir: Path,
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

    if _is_url(input_path):
        agent_provider = build_provider(
            name=provider_name, model=agent_model, for_agent=True
        )
        click.echo(f"Descubriendo evidencia desde {input_path}...")
        evidence_dir = discover_from_url(
            url=input_path, agent_provider=agent_provider, out_dir=out_dir
        )
        click.echo(
            f"Evidencia en {evidence_dir} (traza en {out_dir}/00_discovery/discovery.md)"
        )
        pipeline_input = evidence_dir
    else:
        pipeline_input = Path(input_path)
        if not pipeline_input.exists():
            raise click.BadParameter(f"No existe: {input_path}")

    pipeline_provider = build_provider(name=provider_name, model=model)
    run_pipeline(
        input_path=pipeline_input, provider=pipeline_provider, out_dir=out_dir
    )
    click.echo(f"DDL generado en {out_dir / '04_ddl.sql'}")
    click.echo(
        f"Artefactos intermedios en {out_dir}/ (01_input, 02_analysis, 03_design)"
    )


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@"))


if __name__ == "__main__":
    main()
