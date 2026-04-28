from pathlib import Path

import click
from dotenv import load_dotenv

from normalizer.pipeline import run_pipeline
from normalizer.providers import available_providers, build_provider


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=Path("out/output.sql"),
    show_default=True,
    help="Ruta del DDL Oracle generado.",
)
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
    help="Modelo concreto del proveedor. Si no se indica se usa el por defecto.",
)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directorio donde se guardan los artefactos intermedios del pipeline.",
)
def main(
    input_path: Path,
    output: Path,
    provider_name: str,
    model: str | None,
    out_dir: Path,
) -> None:
    """Normaliza un modelo documental MongoDB a DDL Oracle vía LLM.

    INPUT_PATH puede ser:

    - un archivo único con fragmentos relevantes (schemas, consultas, ejemplos
      de documentos, accesos a campos, etc.) recopilados manualmente, o

    - un directorio que contenga esos fragmentos en varios archivos (no
      recursivo: se asume que el directorio ya está curado).
    """
    load_dotenv()
    out_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    provider = build_provider(name=provider_name, model=model)
    ddl = run_pipeline(input_path=input_path, provider=provider, out_dir=out_dir)
    output.write_text(ddl, encoding="utf-8")
    click.echo(f"DDL generado en {output}")
    click.echo(f"Artefactos intermedios en {out_dir}/")


if __name__ == "__main__":
    main()
