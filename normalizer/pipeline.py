from pathlib import Path

from normalizer.prompts import ANALYZE, DDL, DESIGN
from normalizer.providers import LLMProvider


def _read_input(input_path: Path) -> str:
    """Concatena los archivos del input en un único bundle de texto.

    Acepta archivo único o directorio (no recursivo). Los archivos que no se
    puedan decodificar como UTF-8 se saltan.
    """
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(p for p in input_path.iterdir() if p.is_file())
    if not files:
        raise RuntimeError(f"No se encontraron archivos en {input_path}")

    parts: list[str] = []
    skipped: list[str] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(f.name)
            continue
        parts.append(f"// === {f.name} ===")
        parts.append(text)

    if not parts:
        raise RuntimeError(f"Ningún archivo legible como texto en {input_path}")
    if skipped:
        parts.append(f"// (archivos saltados por no ser texto: {', '.join(skipped)})")

    return "\n\n".join(parts)


def run_pipeline(
    input_path: Path,
    provider: LLMProvider,
    out_dir: Path,
) -> str:
    evidence = _read_input(input_path)
    (out_dir / "01_input.txt").write_text(evidence, encoding="utf-8")

    analysis = provider.generate(ANALYZE.format(evidence=evidence))
    (out_dir / "02_analysis.md").write_text(analysis, encoding="utf-8")

    design = provider.generate(DESIGN.format(analysis=analysis))
    (out_dir / "03_design.md").write_text(design, encoding="utf-8")

    ddl = provider.generate(DDL.format(design=design))
    (out_dir / "04_ddl.sql").write_text(ddl, encoding="utf-8")

    return ddl
