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
