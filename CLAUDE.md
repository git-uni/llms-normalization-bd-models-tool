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
- Invocación: **CLI con click** — `python -m normalizer <input> -o output.sql`.
- Formato de input: **archivo único o directorio curado** con fragmentos heterogéneos.
- **Abstracción de proveedor LLM ya en su sitio** (`normalizer/providers/` con `Protocol LLMProvider`), aunque la única implementación actual sea Google. Multi-proveedor real es **cuasirequisito de la siguiente reunión**.
- Output: DDL compatible con **Oracle**.

**Fuera del alcance de esta fase:**

- UI o frontend.
- Implementaciones reales de proveedores adicionales (la abstracción está, las clases no).
- **Descubrimiento automático en un repositorio completo** — la herramienta NO escanea un repo crudo en busca de evidencia relevante. El input se asume curado por humano (archivo/directorio donde alguien ya recopiló los fragmentos relevantes). El descubrimiento automático requeriría una capa de agentes/heurísticas separada.
- Otros formatos de entrada de la visión completa (URL de repo, texto directo, etc.).

**Datos de prueba:**
Los schemas Mongoose del repositorio [Spruce](https://github.com/dan-divy/spruce) están copiados en `data/spruce/` (4 archivos: `analytics.js`, `keys.js`, `room.js`, `user.js`). Sirven como caso de prueba pero **representan el caso fácil** — tienen schemas explícitos con tipos declarados. El prototipo debe funcionar también con inputs donde el modelo documental sea implícito.

**Baseline de comparación:** **no hay DDL manual**, solo un **diagrama UML** del autor. La comparación final con los resultados del prototipo será **cualitativa** (UML manual ↔ modelo relacional generado), no diff automático.

---

## 2. Estado del prototipo

**Hecho:**

1. Stack decidido y proyecto inicializado (`pyproject.toml`, `.gitignore`, `.env.example`).
2. Estructura de carpetas creada (`normalizer/` con paquete + `data/spruce/` con input de prueba).
3. Schemas de Spruce copiados a `data/spruce/`.
4. Lectura de input (archivo único o directorio, no recursivo) implementada.
5. Pipeline de 4 pasos con prompts inline implementado en `pipeline.py`.
6. Abstracción de proveedor LLM con `GoogleProvider` registrado (`normalizer/providers/`).

**Siguiente:**

1. El autor obtiene una API key de Google AI Studio y la pone en `.env` (`GOOGLE_API_KEY=`).
2. Ejecutar el pipeline end-to-end con Spruce y revisar los artefactos `01_input.txt`, `02_analysis.md`, `03_design.md`, `04_ddl.sql` en `out/`.
3. Iterar sobre los prompts hasta que el modelo relacional generado sea coherente con el UML manual.
4. Probar con un input "no-Spruce" donde el modelo documental no esté en schemas explícitos sino disperso en consultas/código — esto es lo que valida que el prompt de análisis no está sobreajustado al caso fácil.

---

## 3. Estructura del código

```
normalizer/
├── __init__.py
├── __main__.py             # `python -m normalizer` → cli.main
├── cli.py                  # click CLI: --output, --provider, --model, --out-dir
├── pipeline.py             # 4 pasos + 3 prompts inline (analyze, design, ddl)
└── providers/
    ├── base.py             # Protocol LLMProvider (name, model, generate(prompt))
    ├── google.py           # GoogleProvider (gemma-3-27b-it por defecto)
    └── __init__.py         # registry + build_provider() + available_providers()
data/spruce/                # 4 schemas Mongoose como input de prueba
out/                        # artefactos intermedios y DDL final (gitignored)
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
