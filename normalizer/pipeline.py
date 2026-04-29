from pathlib import Path

from normalizer.providers import LLMProvider

PROMPT_ANALYZE = """\
Eres un experto en bases de datos NoSQL orientadas a documentos. Recibes un
conjunto de fragmentos de código y datos procedentes de una aplicación que usa
una base de datos documental (típicamente MongoDB). El contenido es
**heterogéneo**: puede incluir, en cualquier combinación, los siguientes tipos
de evidencia:

- Definiciones explícitas de schemas (Mongoose, JSON Schema, dataclasses, etc.).
- Consultas a la base de datos (`find`, `aggregate`, `$project`, `$group`,
  `$lookup`...) que revelan implícitamente la forma de los documentos.
- Operaciones de escritura (`insertOne`, `updateOne` con `$set` / `$push`,
  `bulkWrite`...) que muestran qué campos se almacenan.
- Ejemplos de documentos en JSON o BSON.
- Accesos a campos desde código de aplicación (p. ej. `user.profile.email`,
  `doc["items"][0]["price"]`).
- Comentarios o documentación en lenguaje natural sobre la estructura.

Tu tarea: a partir de toda esa evidencia, **reconstruir el modelo documental
implícito**. No asumas que existen schemas explícitos: en muchos casos la
estructura solo se deduce cruzando consultas y accesos en código.

Para cada colección/entidad documental que detectes, produce:

1. Nombre de la colección.
2. Tabla de atributos: nombre, tipo inferido, si es opcional, ejemplo
   representativo (si lo hay) y la **fuente de evidencia** (qué fragmento
   permitió deducirlo).
3. Para cualquier atributo cuyo valor sea un objeto anidado o un array de
   objetos, describe la sub-estructura recursivamente con el mismo formato. **No
   te limites a marcar `Array` u `Object`**: profundiza hasta los campos hoja.
4. Relaciones detectadas con otras colecciones: referencias por id, listas de
   ids, denormalizaciones (mismo dato copiado en varias colecciones).

Si hay fragmentos que no aportan información sobre el modelo (utilidades,
imports, configuración, lógica ajena...), ignóralos en silencio. Si una pieza
de evidencia es ambigua o contradictoria, indícalo en una columna de
observaciones en lugar de inventar.

Devuelve el resultado en Markdown, una sección por colección.

EVIDENCIA:
---
{evidence}
---
"""

PROMPT_DESIGN = """\
Tienes este análisis de un modelo documental:

---
{analysis}
---

Diseña el modelo relacional **normalizado** (al menos en 3FN) equivalente.
Reglas:
- Cada array de objetos del modelo documental se convierte en una tabla
  separada con clave foránea hacia su entidad propietaria.
- Listas de identificadores (followers, miembros de una sala, etiquetas, etc.)
  se modelan como tablas de relación N:M.
- Para cada tabla define: nombre, columnas (nombre, tipo lógico, nullable),
  clave primaria, claves foráneas y restricciones de unicidad cuando apliquen.
- Resuelve denormalizaciones: si el mismo dato aparece duplicado en varias
  colecciones documentales, decide cuál es la fuente canónica y deja el resto
  como FKs.
- **Reconcilia atributos redundantes dentro de una misma entidad**: si dos
  atributos diferentes apuntan al mismo registro de otra colección (por ejemplo
  uno guarda el `username` y otro el `_id` del mismo usuario), conserva una
  sola FK canónica al PK de la tabla destino y elimina la otra. No emitas dos
  columnas que referencien el mismo registro.
- No introduzcas tablas que no se justifiquen con el análisis previo.

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

    analysis = provider.generate(PROMPT_ANALYZE.format(evidence=evidence))
    (out_dir / "02_analysis.md").write_text(analysis, encoding="utf-8")

    design = provider.generate(PROMPT_DESIGN.format(analysis=analysis))
    (out_dir / "03_design.md").write_text(design, encoding="utf-8")

    ddl = provider.generate(PROMPT_DDL.format(design=design))
    (out_dir / "04_ddl.sql").write_text(ddl, encoding="utf-8")

    return ddl
