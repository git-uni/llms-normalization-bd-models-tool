# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

**Fase actual: depurar la memoria oficial del TFG** (`memoria/cap01.md … cap09.md`). El prototipo
está terminado y validado; el trabajo vivo es revisar los comentarios que los tutores dejan sobre
la memoria. Este documento es la **referencia del código** contra la que se contrasta lo que la
memoria afirma: si un capítulo describe una capacidad, debe corresponder con lo que hace el código
descrito aquí. Las convenciones de **redacción** de la memoria (qué se menciona, qué tono, qué no
inventar) viven en la memoria persistente del asistente, no aquí. Las mecánicas de
puntuación y tipografía sí están aquí (§6).

---

## 1. Objetivo y decisiones

**Qué hace:** dado un conjunto de fragmentos de evidencia sobre un modelo documental MongoDB, llama
a una API de LLM y produce automáticamente un modelo relacional normalizado en DDL Oracle —
replicando mediante código y APIs el proceso que antes se hacía a mano en interfaces de chat.

La "evidencia" es heterogénea: schemas explícitos cuando los hay, pero también consultas
(`find`/`aggregate`/`$project`), operaciones de escritura, ejemplos de documentos, accesos a campos
desde código de aplicación o comentarios. **No se asume que el modelo documental esté declarado en
schemas**; en muchos proyectos reales hay que inferirlo cruzando esas fuentes.

**Decisiones arquitectónicas firmes:**

- Lenguaje: **Python 3.11+**. Layout *flat* (no `src/`) para que `python -m normalizer` funcione sin `pip install -e .`.
- Pipeline: **3 llamadas al LLM** (`generate()`: analyze → design → DDL) sobre un input ya leído.
  Produce **4 artefactos numerados** en el `--out-dir`: `01_input.txt` (lectura/concatenación, sin
  LLM), `02_analysis.md`, `03_design.md`, `04_ddl.sql`. Cada artefacto se escribe antes de seguir,
  de modo que los resultados parciales son inspeccionables si la corrida se interrumpe.
- Invocación: **CLI con click** (`python -m normalizer <input>`) más **GUI CustomTkinter**
  equivalente (`python -m normalizer.gui` o el script `normalizer-gui`), que orquesta el mismo
  núcleo en un hilo trabajador. La GUI vive en el extra opcional `[gui]` (`pip install -e .[gui]`).
- Input: **archivo único, directorio curado (no recursivo) o URL de repositorio Git público**. Con
  URL, un agente clona el repo y selecciona por sí mismo la evidencia.
- **Abstracción de proveedor LLM** (`normalizer/providers/`, interfaz `LLMProvider`) con tres
  métodos: `generate(prompt)` (texto-a-texto, para el pipeline), `chat(messages, tools)` (tool-use,
  para el agente) y `list_models(for_agent)` (catálogo dinámico, que la GUI usa para poblar combos).
  Implementaciones: `GoogleProvider` y `GroqProvider`.
- **Dos modelos por proveedor**: el del pipeline (`--model`, barato porque solo hace texto→texto) y
  el del agente (`--agent-model`, requiere function-calling). Defaults (en `providers/__init__.py`):
  - Google: `gemma-4-31b-it` (pipeline) + `gemini-3.1-flash-lite` (agente).
  - Groq: `llama-3.3-70b-versatile` (pipeline) + `qwen/qwen3-32b` (agente).
- Agente de descubrimiento: **tool-use nativo del SDK** (no bucle JSON manual ni framework externo).
  El bucle vive en `discovery/agent.py`; el provider solo expone un turno de `chat()`.
- Output: DDL compatible con **Oracle**.

**Fuera del alcance de este prototipo:**

- **RU-6, agente de refinamiento interactivo** (dialogar con el resultado para renombrar/fusionar
  tablas, etc.). La extensión `chat()` ya lo soportaría, pero el flujo no está construido.
- Tercer proveedor (Anthropic, OpenAI, Mistral…). La abstracción está y dos providers la usan;
  añadir uno es: clase nueva en `providers/`, entrada en `_REGISTRY`, `DEFAULT_MODELS` y
  `DEFAULT_AGENT_MODELS`. Cero cambios en `pipeline` o `cli`.
- Descubrimiento sobre repos **privados** o **no-Git**.

---

## 2. Estructura del código

```
normalizer/
├── __init__.py
├── __main__.py             # `python -m normalizer` → cli.main
├── _log.py                 # log() a stderr + registro de callbacks para la GUI
├── cli/                    # paquete CLI (código en cli.py; __init__ re-exporta main)
│   ├── __init__.py
│   └── cli.py              # click CLI: --provider, --model, --agent-model, --out-dir, --max-tree-entries, --max-iters, --max-files
├── pipeline/               # paquete del pipeline (__init__ re-exporta API pública)
│   ├── __init__.py
│   └── pipeline.py         # 3 fases LLM + PipelineCancelled + cancel_event
├── prompts/                # prompts como .md intercambiables sin tocar Python
│   ├── __init__.py         # carga al importar: ANALYZE, DESIGN, DDL, DISCOVERY_SYSTEM
│   ├── analyze.md          # paso 1 del pipeline (placeholder {evidence})
│   ├── design.md           # paso 2 del pipeline (placeholder {analysis})
│   ├── ddl.md              # paso 3 del pipeline (placeholder {design})
│   └── discovery_system.md # system prompt del agente de descubrimiento
├── discovery/              # agente que descubre evidencia desde URL de repo
│   ├── __init__.py         # expone discover_from_url()
│   ├── agent.py            # bucle chat()-tools + cancel_event + traza turno a turno
│   ├── tools.py            # ToolSpecs + DiscoveryState + dispatch (list_dir, read_file, grep, select_evidence, done)
│   ├── filesystem.py       # filtrado del árbol (BFS), exclusiones y anti path-traversal
│   └── repo.py             # git clone --depth 1 con cache en .cache/repos/
├── providers/
│   ├── base.py             # interfaz LLMProvider + dataclasses (Message, ToolSpec, ToolCall, ChatResponse)
│   ├── google.py           # GoogleProvider: SDK google-genai
│   ├── groq.py             # GroqProvider: SDK groq (OpenAI-compatible)
│   └── __init__.py         # registry + build_provider(for_agent=...) + DEFAULT_MODELS / DEFAULT_AGENT_MODELS
└── gui/                    # CustomTkinter — extra opcional [gui]
    ├── __init__.py
    ├── __main__.py         # `python -m normalizer.gui` → app.main
    ├── app.py              # NormalizerApp: root + navegación entre las 3 pantallas
    ├── state.py            # GuiState + PhaseInfo: configuración + estado de la corrida
    ├── controller.py       # GuiController (hilo trabajador + cola) + ENV_KEY_BY_PROVIDER + persist_api_key
    ├── ddl_graph.py        # parser DDL → DOT + render PNG (con fallback si falta Graphviz)
    ├── windows/
    │   ├── config.py       # ConfigScreen: entrada + proveedor + modelos dinámicos + credenciales
    │   ├── run.py          # RunScreen: fases del pipeline + tabla del agente + log
    │   └── result.py       # ResultScreen: tabview ER/markdown/SQL + ZIP + abrir corridas previas
    └── components/
        ├── markdown_view.py  # MarkdownView sobre CTkTextbox (tablas como widgets reales)
        └── sql_view.py       # SqlView sobre CTkTextbox con pygments
data/
├── spruce/                 # 4 schemas Mongoose (caso fácil)
└── spruce-difuso/          # 8 archivos de servidor sin schemas (caso realista)
notes/                      # notas de sesión y documentos vivos (ver §5)
out-*/                      # cada run usa su propio --out-dir (gitignored)
.cache/repos/               # repos clonados por el agente (gitignored)
```

**Principios de diseño a preservar:**

- **El pipeline solo conoce `LLMProvider`**: nunca importa SDKs concretos. Saber del SDK → provider.
  Saber del repo → `discovery/`.
- **El agente despacha tools, el provider solo expone un turno.** `chat(messages, tools)` devuelve
  texto o `tool_calls`; el bucle agéntico vive en `discovery/agent.py`. `Message` tiene `tool_name`
  y `tool_call_id` porque Gemini empareja respuestas de tools por nombre y OpenAI/Groq por id; se
  rellenan ambos y cada provider usa el suyo.
- **Prompts en `normalizer/prompts/*.md`**, intercambiables editando el archivo. Los del pipeline
  llevan placeholders `{evidence}`/`{analysis}`/`{design}` (formato `str.format`); el del agente no,
  y no se le aplica `.format()` porque su contenido tiene `{...}` literales (ejemplos `new Schema({...})`).
- **Los prompts no asumen Mongoose ni schemas explícitos.** Hablan de "evidencia heterogénea".
- **Paridad funcional CLI / GUI.** La GUI no reimplementa lógica: importa `run_pipeline`,
  `discover_from_url` y los catálogos de `providers` igual que la CLI. Toda extensión del núcleo
  queda accesible desde ambas interfaces. La GUI solo añade orquestación (hilo + cola + cancel_event)
  y visualización (render markdown / SQL / ER del DDL ya generado).

---

## 3. Rationale arquitectónico durable

Por qué el código es como es (sin telemetría de corridas concretas):

- **El modelo es el techo del agente, no el prompt.** Sobre tool-use: Gemini > Qwen3-32B >
  Llama 4 Scout > Llama 3.x (no funciona). Iterar el prompt sube el suelo, pero la capacidad del
  modelo para honrar instrucciones complejas pone un techo.
- **Frontera de tool-use por proveedor.** En Groq solo `qwen/qwen3-32b` y
  `meta-llama/llama-4-scout-17b-16e-instruct` emiten el slot estructurado `tool_calls` correctamente;
  el resto (Llama 3.x, gpt-oss-*, compound) emite markup raro o JSON truncado. Los Llama 3.x siguen
  valiendo para el **pipeline** texto-a-texto. Para el **agente sobre repos grandes**, el árbol que
  recibe en el primer mensaje (~30-50K tokens) supera el TPM del tier gratis de Groq; en la práctica
  el agente sobre URL se corre con Google.
- **Tres palancas del prompt del agente** (`prompts/discovery_system.md`) contra el patrón "modelos
  débiles cierran tras abrir 3-4 archivos del dir de modelos": (a) **principio del hermano** — si
  encuentras un schema en `X/Y/foo`, inspecciona los hermanos de `X/Y/` antes de cerrar; (b) **dos
  pasadas obligatorias** — declarativa (grep de schemas explícitos, multi-stack) e implícita (mirar
  el árbol restante buscando escrituras/accesos/seeds); (c) **batching como regla dura** — una
  respuesta = una petición; `select_evidence` consecutivos van en una sola respuesta.
- **Árbol BFS + cap configurable, default 2000** (`filesystem.build_tree_summary`, constante
  `MAX_TREE_ENTRIES`): recorrido por niveles (no DFS) para que el agente vea **todos los top-level
  dirs** antes de profundizar. El cap se expone como `--max-tree-entries` (CLI) y campo de la GUI,
  y viaja por `discover_from_url(max_tree_entries=...)` (junto a `--max-iters`/`--max-files`, ya
  cableados). Sufijos `.test.*`/`.spec.*` se excluyen solo del dump del árbol, no globalmente
  (siguen accesibles vía `read_file`/`grep`).
- **Observabilidad por stderr** (`_log.py`): helper único `log()` que emite `[mm:ss] mensaje`.
  Default siempre on. La GUI consume el mismo flujo registrando un callback con `register_callback()`,
  sin parsear stderr ni duplicar canales; `reset_clock()` reinicia el reloj al arrancar la corrida.
- **Cancelación cooperativa** (`PipelineCancelled`). `run_pipeline` y `discover_from_url` aceptan un
  `cancel_event: threading.Event` opcional que se comprueba entre fases, al inicio de cada iteración
  del agente y entre tools de un mismo turno. Los artefactos ya escritos se preservan. **La CLI no
  lo usa; la GUI sí**, con `GuiController.cancel_and_abandon()`: transición inmediata a la pantalla
  de resultado y deja el hilo huérfano `daemon` terminando en background la llamada HTTP no abortable.
- **Retries.** Google (`google.py`) reintenta `{429, 500, 502, 503, 504}` respetando el `retryDelay`
  del 429 (Gemma devuelve 5xx transitorios con cierta frecuencia). Groq solo reintenta `RateLimitError`.
- **El agente no relee evidencia ya seleccionada** (`tools.py`): un `read_file` sobre un archivo ya
  marcado con `select_evidence` se corta antes de leer del disco (duplicaría tokens en el historial).

---

## 4. Contexto del TFG

### Datos del proyecto

- **Título:** "Uso de LLMs para la transformación de modelos desnormalizados en bases de datos
  NoSQL orientadas a documentos en modelos normalizados"
- **Autor:** Dani
- **Tipo:** TFG de investigación con desarrollo de herramienta

### Problema que aborda

Las BD NoSQL orientadas a documentos (MongoDB) almacenan datos desnormalizados. Migrarlos a un
modelo relacional requiere identificar entidades, detectar relaciones implícitas, eliminar
redundancia y diseñar claves primarias y foráneas: proceso manual, complejo y propenso a errores.
El TFG explora hasta qué punto los LLMs pueden automatizarlo.

### Spruce como dataset de prueba

[Spruce](https://github.com/dan-divy/spruce) es una aplicación real con MongoDB y schemas Mongoose
explícitos (en `utils/models/`). Es el **caso fácil**. Particularidad útil: muchos arrays están
tipados como `Array` genérico y su estructura real **solo aparece en los comentarios**
(`notifications: Array, // [{msg:"...", link:"..."}]`); de ahí salen tablas hijas como
`USER_NOTIFICATIONS` o `CHAT_MESSAGES` — es el LLM quien lee esos comentarios.

Entidades esperadas del UML manual (baseline de comparación; **no hay DDL manual**):
`USERS`, `USER_FOLLOWERS`, `POSTS`, `USER_NOTIFICATIONS`, `CHAT_ROOMS`, `CHAT_ROOM_MEMBERS`,
`CHAT_MESSAGES`, `API_KEYS`, `API_KEY_STATS`, `ANALYTICS`, `ANALYTICS_STATS`. La comparación final es
**cualitativa** (UML manual ↔ modelo relacional generado).

### Requisitos de usuario (RU)

- **RU-1** Entrada: archivo (1.1), directorio curado (1.2), URL de repositorio (1.3). ✅
- **RU-2** Análisis del modelo documental: entidades/atributos (2.1), relaciones implícitas (2.2),
  trazabilidad (2.3). ✅
- **RU-3** Modelo relacional normalizado: tablas y FKs (3.1), eliminación de redundancias (3.2),
  DDL Oracle (3.3). ✅
- **RU-4** Independencia de proveedor: elección de proveedor (4.1), de modelo (4.2), credenciales
  seguras (4.3). ✅
- **RU-5** Agentes para análisis de repos: descubrimiento autónomo (5.1), justificación de
  decisiones (5.2, traza `discovery.md`). ✅
- **RU-6** Refinamiento interactivo del resultado mediante agente: cambios en lenguaje natural (6.1),
  iteración (6.2). ❌ **Fuera de alcance de este prototipo.**
- **RU-7** Interfaz: CLI (7.1) ✅, GUI (7.2) ✅.
- **RU-8** Inspección: artefactos por fases (8.1), aislamiento de ejecuciones (8.2, `--out-dir`). ✅
- **RU-9** Prototipo end-to-end (9.1) validable cualitativamente contra el UML manual de Spruce (9.2). ✅

### Estado del prototipo (resumen, sin telemetría de corridas)

- **Caso fácil** (`data/spruce/`) y **caso difuso** (`data/spruce-difuso/`) end-to-end: el DDL
  recupera las 11 entidades del UML manual (+ tablas hijas legítimas). El difuso necesitó una regla
  explícita en `design.md` de reconciliación de atributos redundantes (dos columnas que referencian
  el mismo registro → una sola FK canónica).
- **Descubrimiento desde URL** validado contra Spruce y contra repos públicos grandes (el agente
  con Google selecciona evidencia, deja traza `discovery.md` + `tree.txt`, y el pipeline produce DDL).
- **Multi-proveedor**: Google y Groq intercambiables. Pipeline texto-a-texto en ambos; agente sobre
  repos grandes solo viable en Google (ver "Frontera de tool-use" en §3).
- **GUI CustomTkinter (RU-7.2)** end-to-end estructural: tres pantallas (configuración con
  persistencia de API key en `.env`, ejecución con fases del pipeline + tabla viva del agente + log,
  resultado con diagrama ER auto-generado del DDL + pestañas markdown/SQL + ZIP).

### Contexto profesional del autor

Trabaja con sistema legacy Oracle (~6000 tablas, Oracle Forms, SQL/PLSQL). De ahí el interés
práctico y que el DDL de referencia sea **compatible con Oracle**.

---

## 5. Datasets, artefactos y notas

- **`data/spruce/`** → caso fácil: los 4 schemas Mongoose explícitos del repo (`analytics.js`,
  `keys.js`, `room.js`, `user.js`).
- **`data/spruce-difuso/`** → caso realista: 8 archivos del lado servidor (`route_*.js`,
  `handler_*.js`) donde el modelo documental **no está declarado**; se infiere cruzando rutas
  Express, handlers de socket y operaciones contra la BD (`new User({...})`, `posts.push({...})`,
  `room.chats.push({...})`…). Mismo ground truth UML que `spruce/`. (Son los únicos datasets
  committeados; las corridas URL contra repos públicos grandes viven en `out-*/`, gitignored, y no
  forman parte del repo.)

**Convención de directorios de salida:** cada run usa su propio `--out-dir` (`out-facil/`,
`out-difuso/`, etc.), todos gitignored (`out-*/`). `out/` por defecto NO se asume vinculado a ningún
dataset.

**Sobre `notes/`:** material complementario para la memoria del TFG.

- **Logs de sesión** `YYYY-MM-DD-<tema>.md`: el *qué se hizo y por qué* de una sesión grande.
- **Documentos vivos** con nombre temático sin fecha (p. ej. `proceso-agentico-explicado.md`,
  `gui-explicada.md`): explicación conceptual para defender el TFG.

Ninguno es el estado actual (eso vive aquí) ni reemplaza al historial git.

---

## 6. Mecánicas de redacción

Al redactar texto para el proyecto (memoria, *prompts*, respuestas en chat), el objetivo es prosa
natural. Hay que evitar el registro tan reconocible de un texto generado por IA. Reglas concretas:

- **Sin guiones largos (rayas).** No usar el carácter `—` (ni `–`). No está en el teclado español y
  delata el texto al instante. Para un inciso, usar paréntesis o comas. Para una pausa fuerte,
  partir en dos frases. El guion corto `-` solo para palabras compuestas o rangos.
- **Sin incisos con raya** (el patrón "texto `—`algo`—` más texto"). Es el *tell* más visible.
  Reescribir con paréntesis o con comas.
- **Punto y coma con moderación.** La mayoría de los `;` se leen mejor como dos frases, o con una
  coma o un paréntesis. Reservar el `;` para separar elementos de una lista que ya llevan comas
  dentro.
- **Solo caracteres del teclado.** Comillas rectas en vez de tipográficas, tres puntos en vez del
  carácter único de puntos suspensivos, sin símbolos especiales.
- **Frases más cortas.** Si una frase encadena varias subordinadas con comas y rayas, conviene
  partirla.

Aplica a lo que escribo en los `.md` de la memoria y en las respuestas. Los `.md` ya existentes se
limpian a medida que se tocan.
