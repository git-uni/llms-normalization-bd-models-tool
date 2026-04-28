from pathlib import Path

from normalizer.llm import generate

PROMPT_ANALYZE = """\
Eres un experto en modelado de bases de datos. A continuación tienes los schemas
de MongoDB (Mongoose) de una aplicación. Tu tarea es analizarlos y producir un
inventario detallado.

Para cada schema describe:
1. Todos sus atributos con su tipo declarado.
2. Para cada atributo cuyo tipo declarado sea `Array` o cuyo contenido no sea un
   tipo primitivo, infiere su estructura interna a partir de los **comentarios
   de ejemplo** que aparecen al lado del campo en el código fuente. Esos
   comentarios son la fuente principal para detectar arrays anidados de objetos
   y deben tratarse como parte del schema, no como ruido.
3. Posibles relaciones con otras entidades (referencias por id, listas de ids,
   denormalizaciones, etc.).

Devuelve el resultado en Markdown estructurado: una sección por entidad con una
tabla de atributos que distinga nombre, tipo declarado, tipo real inferido,
ejemplo y observaciones, seguida de una lista de relaciones detectadas.

SCHEMAS:
---
{schemas}
---
"""

PROMPT_DESIGN = """\
Tienes el siguiente análisis de un modelo documental MongoDB:

---
{analysis}
---

Diseña un modelo relacional **normalizado** (al menos en 3FN) equivalente.
Reglas:
- Cada array de objetos debe convertirse en una tabla separada con clave foránea
  hacia su entidad propietaria.
- Listas de identificadores (followers, chat_rooms, miembros de sala, etc.) se
  modelan como tablas de relación N:M.
- Para cada tabla define: nombre, columnas (nombre, tipo lógico, nullable),
  clave primaria, claves foráneas y restricciones de unicidad cuando apliquen.
- No introduzcas redundancias innecesarias.

Devuelve el modelo en Markdown, una sección por tabla. **No** generes DDL en
este paso.
"""

PROMPT_DDL = """\
A partir de este modelo relacional:

---
{design}
---

Genera el DDL **compatible con Oracle**. Requisitos:
- Usa tipos Oracle: VARCHAR2, NUMBER, DATE, TIMESTAMP, CLOB cuando aplique.
- Define PRIMARY KEY, FOREIGN KEY, NOT NULL y UNIQUE de forma explícita.
- Ordena los CREATE TABLE de manera que ninguna FK referencie una tabla aún no
  creada.
- Devuelve **solo** sentencias SQL ejecutables, sin explicaciones ni bloques de
  código markdown.
"""


def _read_input(input_path: Path) -> str:
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(input_path.glob("*.js"))
    if not files:
        raise RuntimeError(f"No se encontraron schemas en {input_path}")
    parts: list[str] = []
    for f in files:
        parts.append(f"// === {f.name} ===")
        parts.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def run_pipeline(input_path: Path, model: str, out_dir: Path) -> str:
    schemas_text = _read_input(input_path)
    (out_dir / "01_input.txt").write_text(schemas_text, encoding="utf-8")

    analysis = generate(model, PROMPT_ANALYZE.format(schemas=schemas_text))
    (out_dir / "02_analysis.md").write_text(analysis, encoding="utf-8")

    design = generate(model, PROMPT_DESIGN.format(analysis=analysis))
    (out_dir / "03_design.md").write_text(design, encoding="utf-8")

    ddl = generate(model, PROMPT_DDL.format(design=design))
    (out_dir / "04_ddl.sql").write_text(ddl, encoding="utf-8")

    return ddl
