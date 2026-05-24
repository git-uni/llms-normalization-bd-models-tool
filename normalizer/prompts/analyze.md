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
