from pathlib import Path

import click
from dotenv import load_dotenv

from normalizer.pipeline import run_pipeline


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
    "--model",
    default="gemma-3-27b-it",
    show_default=True,
    help="Modelo de Google Generative AI a usar.",
)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directorio donde se guardan los artefactos intermedios del pipeline.",
)
def main(input_path: Path, output: Path, model: str, out_dir: Path) -> None:
    """Normaliza schemas MongoDB a DDL Oracle vía LLM.

    INPUT_PATH puede ser un archivo único o un directorio (en cuyo caso se
    procesan todos los .js que contenga).
    """
    load_dotenv()
    out_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    ddl = run_pipeline(input_path=input_path, model=model, out_dir=out_dir)
    output.write_text(ddl, encoding="utf-8")
    click.echo(f"DDL generado en {output}")
    click.echo(f"Artefactos intermedios en {out_dir}/")


if __name__ == "__main__":
    main()
