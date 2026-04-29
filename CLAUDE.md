# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

---

## 1. Objetivo inmediato

Construir un **programa que, dado un conjunto de fragmentos de evidencia sobre un modelo documental MongoDB, llame a una API de LLM y produzca automáticamente un modelo relacional normalizado en DDL Oracle** — replicando mediante código y APIs el proceso que hasta ahora se realizaba manualmente en interfaces de chat.

La "evidencia" es heterogénea: schemas explícitos cuando los hay, pero también consultas (`find`/`aggregate`/`$project`), operaciones de escritura, ejemplos de documentos, accesos a campos desde código de aplicación o comentarios. **No se asume que el modelo documental esté declarado en schemas**; en muchos proyectos reales hay que inferirlo cruzando esas fuentes.

**Hito:** prototipo funcional listo para mostrar en la siguiente reunión con tutores.

**Decisiones tomadas:**

- Lenguaje: **Python 3.11+**.
- API por defecto: **Google Generative AI** vía SDK `google-genai`, modelo **`gemma-3-27b-it`** (gratis en el tier gratuito; recomendación de los tutores).
- Pipeline: **multi-paso de 4 fases** (lectura → análisis del modelo documental → diseño relacional → DDL Oracle). Cada paso intermedio se guarda en `out/` para inspección.
- Invocación: **CLI con click** — `python -m normalizer <input>` (los artefactos se escriben en `out/`, incluido el DDL final como `out/04_ddl.sql`).
- Formato de input: **archivo único o directorio curado** con fragmentos heterogéneos.
- **Abstracción de proveedor LLM ya en su sitio** (`normalizer/providers/` con `Protocol LLMProvider`), aunque la única implementación actual sea Google. Multi-proveedor real es **cuasirequisito de la siguiente reunión**.
- Output: DDL compatible con **Oracle**.

**Fuera del alcance de esta fase:**

- UI o frontend.
- Implementaciones reales de proveedores adicionales (la abstracción está, las clases no).
- **Descubrimiento automático en un repositorio completo** — la herramienta NO escanea un repo crudo en busca de evidencia relevante. El input se asume curado por humano (archivo/directorio donde alguien ya recopiló los fragmentos relevantes). El descubrimiento automático requeriría una capa de agentes/heurísticas separada.
- Otros formatos de entrada de la visión completa (URL de repo, texto directo, etc.).

**Datos de prueba:**

Dos datasets, ambos derivados del repositorio [Spruce](https://github.com/dan-divy/spruce). **Importante:** ninguno contiene el repo entero — solo una selección manualmente curada de archivos relevantes para la BD. El repo tiene muchos más directorios y archivos (rutas, vistas, assets, libs cliente, configs, tests…) que no están en `data/`.

- **`data/spruce/`** → caso fácil. Solo los 4 schemas Mongoose explícitos del repo (`analytics.js`, `keys.js`, `room.js`, `user.js`, originalmente en `utils/models/`).
- **`data/spruce-difuso/`** → caso realista. 8 archivos del lado servidor renombrados con prefijo (`route_*.js`, `handler_*.js`) donde el modelo documental **no está declarado** en ningún sitio: solo se infiere cruzando rutas Express, handlers de socket y operaciones contra la BD (creación de objetos `new User({...})`, `posts.push({...})`, accesos `user.followers[i]`, `room.chats.push({...})`, etc.). NO incluye los schemas. Mismo "ground truth" que `spruce/` (mismo UML manual), por lo que es la prueba directa de si el prompt de análisis funciona sin schemas explícitos.

**Baseline de comparación:** **no hay DDL manual**, solo un **diagrama UML** del autor. La comparación final con los resultados del prototipo será **cualitativa** (UML manual ↔ modelo relacional generado), no diff automático.

---

## 2. Estado del prototipo

**Hecho:**

1. Stack decidido y proyecto inicializado (`pyproject.toml`, `.gitignore`, `.env.example`).
2. Estructura de carpetas creada y schemas de Spruce copiados a `data/spruce/`.
3. Lectura de input (archivo único o directorio, no recursivo) implementada.
4. Pipeline de 4 pasos con prompts inline implementado en `pipeline.py`.
5. Abstracción de proveedor LLM con `GoogleProvider` registrado (`normalizer/providers/`).
6. **Caso fácil validado** end-to-end con `data/spruce/` y `gemma-3-27b-it`: el `04_ddl.sql` generado es prácticamente idéntico al DDL que el autor obtenía manualmente en chat.
7. **Caso difuso validado** con `data/spruce-difuso/` (mismo modelo): se recuperan las 11 entidades del UML manual + dos tablas extra legítimas (`post_comments` y `post_likes`) que normalizan los arrays anidados de posts. Se añadió al `PROMPT_DESIGN` una regla explícita de **reconciliación de atributos redundantes** (cuando dos columnas distintas referencian el mismo registro de otra tabla, conservar solo una FK canónica) — eso eliminó la duplicidad `posts.author_id` + `posts.authorID` que aparecía en la primera pasada.

**Siguiente:**

1. **Cuasirequisito de la próxima reunión:** implementar al menos un proveedor LLM adicional (Anthropic u OpenAI) usando la abstracción ya existente en `normalizer/providers/`. Es el camino más corto para satisfacer RU-7 (independencia del proveedor) en la demo.
2. Cuando se vuelva a iterar sobre la calidad del DDL: hay puntos menores conocidos que el autor decidió **no atacar ahora** porque "más o menos funciona" — el `04_ddl.sql` se emite envuelto en ` ```sql ... ``` ` (no es ejecutable tal cual sin pelar el cerco), y se usa `BOOLEAN` que Oracle no tiene nativo en versiones <23. Si en el futuro se fija una versión Oracle objetivo o se necesita ejecutar el SQL automáticamente, esos dos puntos vuelven a ser relevantes.

**Convención de directorios de salida:** cada dataset se ejecuta a su propio `--out-dir` (`out-facil/`, `out-difuso/`, etc.) para no pisarse. El directorio `out/` por defecto NO debe asumirse vinculado a ningún dataset concreto: en este momento contiene un run pisado y no es comparable.

---

## 3. Estructura del código

```
normalizer/
├── __init__.py
├── __main__.py             # `python -m normalizer` → cli.main
├── cli.py                  # click CLI: --provider, --model, --out-dir
├── pipeline.py             # 4 pasos + 3 prompts inline (analyze, design, ddl)
└── providers/
    ├── base.py             # Protocol LLMProvider (name, model, generate(prompt))
    ├── google.py           # GoogleProvider (gemma-3-27b-it por defecto)
    └── __init__.py         # registry + build_provider() + available_providers()
data/
├── spruce/                 # 4 schemas Mongoose (caso fácil)
└── spruce-difuso/          # 8 archivos de servidor sin schemas (caso realista)
out-facil/                  # run de data/spruce/        (gitignored)
out-difuso/                 # run de data/spruce-difuso/ (gitignored)
out/                        # default si no se pasa --out-dir, no asumir contenido
```

Principios que conviene preservar:

- **El pipeline solo conoce `LLMProvider`**: nunca importa SDKs concretos. Añadir un proveedor nuevo es: clase nueva en `providers/`, entrada en `_REGISTRY` y `DEFAULT_MODELS`. Cero cambios en `pipeline.py` o `cli.py`.
- **Prompts inline** en `pipeline.py` mientras sean ~3 y se iteren con frecuencia. Si crecen mucho, extraer a `normalizer/prompts/*.md`.
- **Layout flat** (no `src/`) para que `python -m normalizer` funcione sin `pip install -e .`, aunque la instalación también está soportada.
- **Los prompts no asumen Mongoose ni schemas explícitos.** Hablan de "evidencia heterogénea" (schemas, consultas, ejemplos, accesos en código). Si se cambian, mantener este principio.

---

## 4. Contexto del TFG

### Datos del proyecto

- **Título:** "Uso de LLMs para la transformación de modelos desnormalizados en bases de datos NoSQL orientadas a documentos en modelos normalizados"
- **Autor:** Dani
- **Tipo:** TFG de investigación con desarrollo de herramienta

### Problema que aborda

Las bases de datos NoSQL orientadas a documentos (MongoDB) almacenan datos desnormalizados. Migrarlos a un modelo relacional requiere identificar entidades, detectar relaciones implícitas, eliminar redundancia y diseñar claves primarias y foráneas. Es un proceso manual, complejo y propenso a errores. El TFG explora hasta qué punto los LLMs pueden automatizarlo.

### Spruce como dataset de prueba

[Spruce](https://github.com/dan-divy/spruce) es una aplicación real con MongoDB y schemas definidos explícitamente en el código (Mongoose, en `utils/models/`). Se eligió como caso de estudio por su complejidad moderada y la claridad de sus definiciones de esquema — pero precisamente por eso es el **caso fácil**: en proyectos reales el modelo documental rara vez está declarado tan limpiamente.

Particularidad útil de los schemas de Spruce: muchos arrays están tipados como `Array` genérico, y la estructura real del objeto contenido **solo aparece en los comentarios** al lado del campo (p. ej. `notifications: Array, // [{msg:"...", link:"..."}]`). De ahí salen tablas hijas del modelo relacional como `USER_NOTIFICATIONS` o `CHAT_MESSAGES` — es el LLM quien debe leer esos comentarios.

Entidades esperadas del UML manual (no es un DDL, es un diagrama del autor):
`USERS`, `USER_FOLLOWERS`, `POSTS`, `USER_NOTIFICATIONS`, `CHAT_ROOMS`, `CHAT_ROOM_MEMBERS`, `CHAT_MESSAGES`, `API_KEYS`, `API_KEY_STATS`, `ANALYTICS`, `ANALYTICS_STATS`.

**Sobre `data/spruce-difuso/`:** los 8 archivos copiados (rutas Express + handlers de socket) revelan el modelo documental implícitamente a través del uso. Casos típicos a observar en el `02_analysis.md`:

- Estructura de **POSTS** (con `comments`, `likes`, `static_url`, `caption`, `category`, `createdAt`...): solo aparece en `route_settings.js` cuando se hace `u.posts.push({...})`.
- Estructura de **CHAT_MESSAGES** (con `txt`, `by: {username, profile_pic, _id}`, `time`): solo en `handler_socket.js` con `room.chats.push({...})`. Nótese que `by` está **denormalizado** dentro del chat — el LLM tiene que decidir cómo modelarlo.
- Estructura de **NOTIFICATIONS** (con `msg`, `link`, `time`): aparece repetidamente con `notifications.push(...)` en varios handlers.
- Estructura de **API_KEY_STATS** (`time`, `request`): solo en `route_developer_api.js`.
- Hay incluso un **typo del repo original** (`fistname` en vez de `firstname` en `route_auth.js`). El LLM tendrá que decidir si lo trata como atributo legítimo o lo reconcilia con `firstname`.

El prototipo debe funcionar con cualquier input de evidencia documental, no solo con Spruce.

### Fase experimental previa (completada, vía chat)

Se evaluaron varios LLMs con el mismo input (schemas de Spruce):

| Modelo          | Modo              | Output                     |
| --------------- | ----------------- | -------------------------- |
| GPT-3.5         | Prompt directo    | DDL Oracle + UML           |
| GPT-5           | Prompt directo    | DDL Oracle + UML           |
| Claude Opus 4.6 | Prompt directo    | DDL Oracle + UML + índices |
| Claude Opus 4.6 | Agente (4 tareas) | DDL Oracle completo        |
| GPT-5.3-Codex   | Agente            | DDL Oracle completo        |

El pipeline multi-paso que mejores resultados produjo (Claude Opus 4.6 como agente):

1. Read all MongoDB Schema Models
2. Analyze Schemas and Relationships
3. Design normalized relational model
4. Generate Oracle DDL statements

Esta secuencia de pasos es una referencia para diseñar el pipeline del prototipo.

### Visión completa de la herramienta (futuro, no este prototipo)

Requisitos de usuario de la herramienta final:

- **RU-1** — Formatos de entrada: archivo de schemas (RU-1.1), URL de repositorio (RU-1.2), texto directo (RU-1.3)
- **RU-2** — Análisis automático del modelo documental (entidades, atributos, relaciones)
- **RU-3** — Generación de modelo relacional normalizado (PKs, FKs, sin redundancia)
- **RU-4** — Generación de DDL SQL
- **RU-5** — Elección de LLM por el usuario
- **RU-6** — Independencia del modelo LLM concreto
- **RU-7** — Independencia del proveedor de API (Anthropic, OpenAI, Google…)

### Contexto profesional del autor

Trabaja con un sistema legacy basado en Oracle (~6000 tablas, Oracle Forms, SQL/PLSQL). Esto motiva el interés práctico en LLMs aplicados al análisis y migración de esquemas complejos, y justifica que el DDL de referencia sea **compatible con Oracle**.

### Documentación complementaria del TFG

Memoria, plantilla y documento de experimentos: (preguntar ubicacion o contenido necesario para tomar decisiones y acceder al contenido)
