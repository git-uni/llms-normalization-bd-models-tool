# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

---

## 1. Objetivo inmediato

Construir un **programa que, dado un conjunto de fragmentos de evidencia sobre un modelo documental MongoDB, llame a una API de LLM y produzca automáticamente un modelo relacional normalizado en DDL Oracle** — replicando mediante código y APIs el proceso que hasta ahora se realizaba manualmente en interfaces de chat.

La "evidencia" es heterogénea: schemas explícitos cuando los hay, pero también consultas (`find`/`aggregate`/`$project`), operaciones de escritura, ejemplos de documentos, accesos a campos desde código de aplicación o comentarios. **No se asume que el modelo documental esté declarado en schemas**; en muchos proyectos reales hay que inferirlo cruzando esas fuentes.

**Hito:** prototipo funcional listo para mostrar en la siguiente reunión con tutores.

**Decisiones tomadas:**

- Lenguaje: **Python 3.11+**.
- Pipeline: **multi-paso de 4 fases** (lectura → análisis del modelo documental → diseño relacional → DDL Oracle). Cada paso intermedio se guarda en `out/` para inspección.
- Invocación: **CLI con click** — `python -m normalizer <input>` — más **GUI CustomTkinter** equivalente — `python -m normalizer.gui` — que orquesta el mismo núcleo en un hilo trabajador. La GUI vive en el extra opcional `[gui]` (`pip install -e .[gui]`).
- Formato de input: **archivo único, directorio curado o URL de repositorio Git público**. En el caso URL, un agente clona el repo y elige por sí mismo la evidencia.
- **Abstracción de proveedor LLM** (`normalizer/providers/` con `Protocol LLMProvider`) con dos métodos: `generate(prompt)` (texto-a-texto, para el pipeline) y `chat(messages, tools)` (tool-use, para el agente). Implementaciones: `GoogleProvider` y `GroqProvider`.
- Dos modelos por proveedor: el del pipeline (barato, solo texto) y el del agente (con function-calling). Defaults vigentes:
  - Google: `gemma-4-31b-it` (pipeline) + `gemini-3.1-flash-lite` (agente, 15 RPM / 250K TPM / 500 RPD).
  - Groq: `llama-3.3-70b-versatile` (pipeline) + `qwen/qwen3-32b` (agente).
- Paradigma del agente de descubrimiento: **tool-use nativo del SDK** (no bucle JSON manual ni framework externo). El bucle vive en `discovery/agent.py`; el provider solo expone un turno. Elegido pensando en que el mismo paradigma se reutilizará para el agente de refinamiento (RU-6) en un hito posterior.
- Output: DDL compatible con **Oracle**.

**Fuera del alcance de esta fase:**

- Tercer proveedor (Anthropic, OpenAI, Mistral, Cerebras…). La abstracción está y dos providers ya la usan; añadir uno es copy-paste.
- **Agente de refinamiento interactivo (RU-6)**: dialogar con el resultado para renombrar entidades, fusionar tablas, etc. La extensión `chat()` ya lo soporta, el flujo no.
- Descubrimiento sobre repos **privados** o **no-Git**.

**Datos de prueba:**

Dos datasets, ambos derivados del repositorio [Spruce](https://github.com/dan-divy/spruce). Ninguno contiene el repo entero — solo selección manualmente curada para BD.

- **`data/spruce/`** → caso fácil. Los 4 schemas Mongoose explícitos del repo (`analytics.js`, `keys.js`, `room.js`, `user.js`).
- **`data/spruce-difuso/`** → caso realista. 8 archivos del lado servidor (`route_*.js`, `handler_*.js`) donde el modelo documental **no está declarado**: solo se infiere cruzando rutas Express, handlers de socket y operaciones contra la BD (`new User({...})`, `posts.push({...})`, `room.chats.push({...})`, etc.). Mismo ground truth UML que `spruce/`.

**Baseline de comparación:** **no hay DDL manual**, solo un **diagrama UML** del autor. La comparación final será **cualitativa** (UML manual ↔ modelo relacional generado).

---

## 2. Estado del prototipo

**Validado:**

- **Caso fácil** (`data/spruce/`) y **caso difuso** (`data/spruce-difuso/`) end-to-end: el DDL recupera las 11 entidades del UML manual (+ tablas hijas legítimas como `post_comments`, `post_likes`). Para difuso hizo falta una regla explícita en `design.md` de **reconciliación de atributos redundantes** (dos columnas que referencian el mismo registro de otra tabla → conservar solo una FK canónica).
- **Descubrimiento desde URL** (`normalizer/discovery/`, RU-1.3 + RU-5): la CLI clona el repo (cache en `.cache/repos/`), el agente con tool-use (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`) selecciona archivos y los deposita en `out/00_discovery/evidence/` junto con traza `discovery.md` (tabla `Iter | Tool calls`) y `tree.txt` (lo que el agente vio en su primer mensaje). Validado contra `https://github.com/dan-divy/spruce`: agente selecciona los 4 schemas exactos, DDL 11/11 entidades.
- **Habitica end-to-end con Google** (`out-habitica-2026-06-01/`, 2026-06-01): 10min 32s wall-clock, 13 iter del agente, 11 archivos seleccionados, 2 × 429 absorbidos por el retry, DDL final 31 tablas. Cobertura tipo "Run A" del histórico (sin batching, 0.85 archivos/iter) — recupera el User entero descompuesto en 13 tablas + Tasks, Groups, Challenges, Messages, Webhooks, Subscriptions, Transactions, Tags. Sigue sin recuperar Coupon, Blocker, IapPurchaseReceipt, NewsPost, EmailUnsubscription, PushDevice, Inbox ni el subdir `analytics/`. Confirma el "principal vs secundario" sigue presente sin batching activo.
- **Multi-proveedor**: Google y Groq intercambiables; cierra el cuasirequisito multi-proveedor del TFG. Para el **pipeline texto-a-texto** ambos funcionan; para el **agente sobre repos grandes** solo Google (ver lección "Frontera Groq").
- **GUI CustomTkinter (RU-7.2)** end-to-end estructural: tres pantallas (configuración con persistencia de API key en `.env` vía `dotenv.set_key`, ejecución con barra de progreso por fases + tabla viva del agente + log, resultado con diagrama ER auto-generado del DDL + pestañas markdown/SQL + ZIP). Lanzamiento: `python -m normalizer.gui`. Verificación programática completa (todas las pantallas se construyen, el flujo de eventos `log()` → callback → cola → render funciona, parser DDL → 11 tablas / 11 FKs sobre `out-facil/`). Verificación interactiva con LLM real pendiente del autor.

**Lecciones que conviene no olvidar:**

- **El modelo es el techo del agente, no el prompt.** Sobre Spruce con tool-use: Gemini (Google) > Qwen3-32B (Groq) > Llama 4 Scout (Groq) > Llama 3.x (no funciona). Iterar el prompt sube el suelo pero la capacidad del modelo para honrar instrucciones complejas pone un techo.
- **Tool-use en Groq es delicado.** Solo `qwen/qwen3-32b` y `meta-llama/llama-4-scout-17b-16e-instruct` funcionan con el slot estructurado. Llama 3.x emite markup `<function=...>`, `gpt-oss-20b` emite JSON malformado, `gpt-oss-120b` emite chain-of-thought no parseable, `groq/compound-*` no aceptan tools del cliente. Los Llama 3.x siguen valiendo para el **pipeline**.
- **Patrón "principal vs secundario" del agente.** Modelos débiles cierran el descubrimiento tras abrir 3-4 archivos del dir de modelos calificando el resto de hermanos como "auxiliares". El prompt actual (`prompts/discovery_system.md`) ataca esto con tres palancas: (a) **Principio del hermano**: si encuentras un schema en `X/Y/foo`, inspeccionas los hermanos en `X/Y/` antes de cerrar — el filtro principal/secundario lo hace el pipeline posterior, no el agente; (b) **dos pasadas obligatorias**: declarativa (grep de schemas explícitos) e implícita (mirar el árbol restante buscando escrituras/accesos/seeds); (c) **batching como regla dura**: una respuesta = una petición, `select_evidence` consecutivos van batchéados.
- **Varianza alta del agente.** Sobre el mismo input (Habitica, mismo prompt, mismo modelo) se han visto runs de 5 a 22 archivos. El batching como regla dura sube el techo pero no elimina la varianza. La pasada implícita sigue siendo "posible pero no garantizada".
- **Árbol BFS + cap 2000**: `build_tree_summary` usa BFS (no DFS) y cap 2000 entradas (~30K tokens) precisamente para que el agente vea **todos los top-level dirs** antes de profundizar — versiones DFS antiguas hacían invisible `website/` en Habitica. Sufijos `.test.js/.test.ts/.spec.js/.spec.ts` se excluyen solo del dump del árbol, no globalmente (siguen accesibles vía `read_file`/`grep`).
- **Observabilidad por stderr (`[mm:ss]`)**: helper único `normalizer/_log.py`. Instrumentados arranque del CLI, las 3 `generate()` del pipeline, clonado, cada iteración del agente con sus tool_calls compactas, y los retries del provider antes del `sleep`. Default siempre on. La GUI consume el mismo flujo registrando un *callback* con `register_callback()`, sin necesidad de parsear stderr ni de duplicar canales.
- **Cancelación cooperativa** (`PipelineCancelled` en `pipeline.py`). `run_pipeline` y `discover_from_url` aceptan un `cancel_event: threading.Event` opcional que se comprueba entre fases y entre iteraciones del agente. Si el evento está señalizado, se levanta la excepción y los artefactos ya escritos a disco se preservan. La CLI no lo usa hoy; la GUI sí, con el botón Cancelar.
- **Retries de Google extendidos a 5xx.** `_call_with_retry` en `google.py` reintenta `{429, 500, 502, 503, 504}` respetando el `retryDelay` del 429. Gemma devuelve 500/503 transitorios con cierta frecuencia. En Groq solo `RateLimitError`.
- **Frontera Groq free × árbol BFS=2000** (verificada 2026-06-01 sobre Habitica). El árbol que el agente recibe en su primer mensaje user genera ~30-50K tokens, y los dos modelos free de Groq que aceptan tools quedan por debajo: `qwen/qwen3-32b` 6K TPM → 413 con 33 270 tokens enviados (extiende punto 18 antiguo); `meta-llama/llama-4-scout-17b-16e-instruct` 30K TPM → 413 con 48 319 tokens enviados. **Para el agente sobre URL de repos medianos+, Groq free no es viable** con la configuración actual del árbol. Para el pipeline texto-a-texto sí: `llama-3.3-70b-versatile` corre `data/spruce-difuso/` end-to-end en **18s** (vs ~4min de Gemma) con 2 × 429 absorbidos, DDL final 9 tablas — 7/11 cobertura del UML manual vs 11/11 que sacaba Gemma sobre el mismo input. Pierde la familia `keys/key_stats` y `analytics/analytics_stats` (las menos representadas en el difuso). Trade-off explícito velocidad↔calidad inter-proveedor con el mismo input.
- **Cerebras free queda descartado** (verificado 2026-06-01). Catálogo reducido a `gpt-oss-120b` + `zai-glm-4.7`; familia Qwen deprecada feb-2026. Pero el bloqueante real es el **cap de contexto 8 192 tokens en free tier**, que ni nuestro árbol (~30-50K) ni `01_input.txt` de un dataset medio caben. Tier dev de Cerebras sí lo permite (sin cap diario, RPM altos) pero rompe el "free". Punto 21 antiguo queda invalidado.

**Siguiente:**

0. **Verificación end-to-end interactiva de la GUI** (pendiente del autor): correr los 6 casos del plan §8 — archivo, directorio, URL, cancelación mid-run, error de API, Graphviz ausente — con API keys reales. Tras la primera corrida, confirmar que el diagrama ER renderiza con `winget install Graphviz.Graphviz` y recompilar las figuras Mermaid del cap 2 (`bash memoria/build.sh`).
1. **Pasada implícita real en repo sin Mongoose.** Hoy no está validada contra MongoDB nativo donde la grep declarativa no dé hits — el agente se conforma con la pasada declarativa cuando el dir de modelos es rico. Buscar un repo público con MongoDB sin Mongoose como próximo dataset.
2. **Reducir varianza del batching.** Si se vuelve bloqueante: tool nueva `select_evidence_batch(items=[...])` que materialice el batching en una sola call, o agrupar `select_evidence` consecutivos en `dispatch()`.
3. **Nudges contra "principal vs secundario" sin tocar prompt**: devolver al agente, tras `read_file`, qué hermanos del dir aún no ha leído. Cachear `read_file` en `DiscoveryState` para que relecturas no cuesten iter.
4. **Calidad del DDL — puntos menores aparcados:** el `04_ddl.sql` se emite envuelto en ` ```sql ... ``` ` (no ejecutable sin pelar el cerco), y se usa `BOOLEAN` que Oracle <23 no tiene nativo. Solo relevantes si se fija versión Oracle o se necesita ejecución automática.
5. **Z.ai como tercer proveedor (no implementado, candidato más prometedor)**. `GLM-4.5-Flash` y `GLM-4.7-Flash` están en free tier sin tarjeta, **128K de contexto** (absorbe el árbol BFS=2000 de Habitica sin TPM cap), function-calling soportado oficialmente, API OpenAI-compatible. El cuello del free es **1 petición concurrente**, que ya cumplimos por diseño (el bucle del agente es secuencial). Implementación: nuevo `normalizer/providers/zai.py` ≈ copy-paste de `groq.py` con `base_url` y modelos por defecto distintos, registro en `_REGISTRY` / `DEFAULT_MODELS` / `DEFAULT_AGENT_MODELS`. Validación pulgar: Spruce-URL primero, luego Habitica para comparar con el run Google del 2026-06-01 sobre el mismo input. Verificado por WebFetch a `docs.z.ai` el 2026-06-01.
6. **Multi-proveedor balanceado** (sin implementar). Hoy `--provider` es único y obliga a usar el mismo para pipeline y agente. Añadir `--agent-provider` separado permitiría combinaciones tipo "agente Google + pipeline Groq" (que ya hicimos de facto en runs antiguos como fallback ante 5xx de Gemma). Cambio en `cli.py` + nada más, ya que el provider lo construye `build_provider(for_agent=...)`.

**Convención de directorios de salida:** cada run usa su propio `--out-dir` (`out-facil/`, `out-difuso/`, `out-spruce-url/`, etc.). Los intermedios se purgan cuando dejan de ser referencia; los actuales en disco con `ls -d out-*`. `out/` por defecto NO se asume vinculado a ningún dataset.

---

## 3. Estructura del código

```
normalizer/
├── __init__.py
├── __main__.py             # `python -m normalizer` → cli.main
├── _log.py                 # log() a stderr + callback registry para la GUI
├── cli.py                  # click CLI: --provider, --model, --agent-model, --out-dir
├── pipeline.py             # 4 fases + PipelineCancelled + parámetro cancel_event
├── prompts/                # prompts como .md intercambiables sin tocar Python
│   ├── __init__.py         # carga al importar: ANALYZE, DESIGN, DDL, DISCOVERY_SYSTEM
│   ├── analyze.md          # paso 1 del pipeline (placeholder {evidence})
│   ├── design.md           # paso 2 del pipeline (placeholder {analysis})
│   ├── ddl.md              # paso 3 del pipeline (placeholder {design})
│   └── discovery_system.md # system prompt del agente de descubrimiento
├── discovery/              # agente que descubre evidencia desde URL de repo
│   ├── __init__.py         # expone discover_from_url()
│   ├── agent.py            # bucle chat()-tools + cancel_event entre iteraciones
│   ├── tools.py            # ToolSpecs + dispatch (list_dir, read_file, grep, select_evidence, done)
│   ├── filesystem.py       # filtrado del árbol y validación anti path-traversal
│   └── repo.py             # git clone --depth 1 con cache en .cache/repos/
├── providers/
│   ├── base.py             # Protocol LLMProvider + dataclasses (Message, ToolSpec, ToolCall, ChatResponse)
│   ├── google.py           # GoogleProvider: SDK google-genai
│   ├── groq.py             # GroqProvider: SDK groq (OpenAI-compatible)
│   └── __init__.py         # registry + build_provider(for_agent=...) + DEFAULT_MODELS / DEFAULT_AGENT_MODELS
└── gui/                    # CustomTkinter — extra opcional [gui]
    ├── __init__.py
    ├── __main__.py         # `python -m normalizer.gui` → app.main
    ├── app.py              # NormalizerApp: root + navegación entre las 3 pantallas
    ├── state.py            # GuiState: dataclass con configuración + run state
    ├── controller.py       # GuiController + ENV_KEY_BY_PROVIDER + persist_api_key
    ├── ddl_graph.py        # parser DDL → DOT + render PNG con fallback gracioso
    ├── windows/
    │   ├── config.py       # ConfigScreen: entrada + proveedor + credenciales
    │   ├── run.py          # RunScreen: chips por fase + tabla agente + log
    │   └── result.py       # ResultScreen: tabview ER/markdown/SQL + ZIP
    └── components/
        ├── markdown_view.py  # MarkdownView sobre CTkTextbox con tags
        └── sql_view.py       # SqlView sobre CTkTextbox con pygments
data/
├── spruce/                 # 4 schemas Mongoose (caso fácil)
└── spruce-difuso/          # 8 archivos de servidor sin schemas (caso realista)
notes/                      # notas de sesión y documentos vivos (ver abajo)
out-*/                      # cada run usa su propio --out-dir (gitignored)
.cache/repos/               # repos clonados por el agente (gitignored)
```

**Sobre `notes/`:** material complementario para la memoria del TFG.

- **Logs de sesión** `YYYY-MM-DD-<tema>.md`: el *qué se hizo y por qué* de una sesión grande. Crear solo si cierra un hito o introduce una decisión arquitectural.
- **Documentos vivos** con nombre temático sin fecha (p. ej. `proceso-agentico-explicado.md`): explicación conceptual para defender el TFG.

Ninguno es el estado actual (eso vive aquí) ni reemplaza al historial git.

**Principios que conviene preservar:**

- **El pipeline solo conoce `LLMProvider`**: nunca importa SDKs concretos. Añadir un proveedor nuevo es: clase nueva en `providers/`, entrada en `_REGISTRY`, `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`. Cero cambios en `pipeline.py` o `cli.py`.
- **Dos modelos por proveedor**: el del pipeline (`--model`) puede ser barato porque solo hace texto→texto; el del agente (`--agent-model`) necesita function-calling.
- **El agente despacha tools, el provider solo expone un turno.** `LLMProvider.chat(messages, tools)` devuelve texto o `tool_calls`; el bucle agéntico vive en `discovery/agent.py`. Saber del SDK → provider. Saber del repo → `discovery/`. `Message` tiene un campo `tool_name` porque Gemini empareja respuestas de tools por nombre y OpenAI/Groq por id; se rellenan ambos.
- **Prompts en `normalizer/prompts/*.md`**, intercambiables editando el archivo sin tocar Python. Los del pipeline tienen placeholders `{evidence}`/`{analysis}`/`{design}` (formato `str.format`); el del agente no — y no se le aplica `.format()` porque su contenido tiene `{...}` literales (`new Schema({...})` en ejemplos).
- **Layout flat** (no `src/`) para que `python -m normalizer` funcione sin `pip install -e .`.
- **Los prompts no asumen Mongoose ni schemas explícitos.** Hablan de "evidencia heterogénea". Mantener este principio.
- **Paridad funcional CLI / GUI.** La GUI no reimplementa lógica: importa `run_pipeline`, `discover_from_url` y los catálogos de `providers` exactamente igual que la CLI. Toda extensión del pipeline o del agente queda accesible desde ambas interfaces sin tocar la capa de presentación. La GUI solo añade orquestación (hilo trabajador + cola + cancel_event) y visualización (render markdown / SQL / ER del DDL ya generado).

---

## 4. Contexto del TFG

### Datos del proyecto

- **Título:** "Uso de LLMs para la transformación de modelos desnormalizados en bases de datos NoSQL orientadas a documentos en modelos normalizados"
- **Autor:** Dani
- **Tipo:** TFG de investigación con desarrollo de herramienta

### Problema que aborda

Las BD NoSQL orientadas a documentos (MongoDB) almacenan datos desnormalizados. Migrarlos a un modelo relacional requiere identificar entidades, detectar relaciones implícitas, eliminar redundancia y diseñar claves primarias y foráneas. Es un proceso manual, complejo y propenso a errores. El TFG explora hasta qué punto los LLMs pueden automatizarlo.

### Spruce como dataset de prueba

[Spruce](https://github.com/dan-divy/spruce) es una aplicación real con MongoDB y schemas Mongoose explícitos (en `utils/models/`). Se eligió por su complejidad moderada y la claridad de sus definiciones — pero precisamente por eso es el **caso fácil**.

Particularidad útil: muchos arrays están tipados como `Array` genérico, y la estructura real **solo aparece en los comentarios** (`notifications: Array, // [{msg:"...", link:"..."}]`). De ahí salen tablas hijas como `USER_NOTIFICATIONS` o `CHAT_MESSAGES` — es el LLM quien lee esos comentarios.

Entidades esperadas del UML manual:
`USERS`, `USER_FOLLOWERS`, `POSTS`, `USER_NOTIFICATIONS`, `CHAT_ROOMS`, `CHAT_ROOM_MEMBERS`, `CHAT_MESSAGES`, `API_KEYS`, `API_KEY_STATS`, `ANALYTICS`, `ANALYTICS_STATS`.

**Sobre `data/spruce-difuso/`:** los 8 archivos revelan el modelo implícitamente. Casos típicos:

- **POSTS** (`comments`, `likes`, `static_url`, `caption`...): solo en `route_settings.js` (`u.posts.push({...})`).
- **CHAT_MESSAGES** (`txt`, `by: {username, profile_pic, _id}`, `time`): solo en `handler_socket.js`. `by` denormalizado — el LLM decide cómo modelarlo.
- **NOTIFICATIONS** (`msg`, `link`, `time`): `notifications.push(...)` en varios handlers.
- **API_KEY_STATS** (`time`, `request`): solo en `route_developer_api.js`.
- **Typo del repo original** (`fistname` vs `firstname` en `route_auth.js`): el LLM tiene que decidir si lo reconcilia.

El prototipo debe funcionar con cualquier evidencia documental, no solo con Spruce.

### Fase experimental previa (vía chat, completada)

Evaluación previa con varios LLMs sobre los schemas de Spruce (GPT-3.5, GPT-5, Claude Opus 4.6, GPT-5.3-Codex). El pipeline multi-paso que mejor funcionó (Claude Opus 4.6 como agente) tenía 4 pasos: leer schemas → analizar → diseñar relacional → DDL Oracle. **Esa secuencia es la referencia del pipeline actual.**

### Visión completa de la herramienta (futuro)

Requisitos de usuario (resumen — el detalle completo vive en la memoria del TFG):

- **RU-1** Entrada: archivo (1.1), directorio curado (1.2), URL de repositorio (1.3).
- **RU-2** Análisis del modelo documental: entidades/atributos (2.1), relaciones implícitas (2.2), trazabilidad (2.3).
- **RU-3** Modelo relacional normalizado: tablas y FKs (3.1), eliminación de redundancias (3.2), DDL Oracle (3.3).
- **RU-4** Independencia de proveedor: elección de proveedor (4.1), de modelo (4.2), credenciales seguras (4.3).
- **RU-5** Agentes para análisis de repos: descubrimiento autónomo (5.1), justificación de decisiones (5.2).
- **RU-6** Refinamiento interactivo del resultado mediante agente: cambios en lenguaje natural (6.1), iteración (6.2). **No implementado en este prototipo.**
- **RU-7** Interfaz: CLI (7.1), GUI (7.2 — fuera de scope).
- **RU-8** Inspección: artefactos por fases (8.1), aislamiento de ejecuciones (8.2).
- **RU-9** Prototipo CLI end-to-end (9.1) validable cualitativamente contra el UML manual de Spruce (9.2).

### Contexto profesional del autor

Trabaja con sistema legacy Oracle (~6000 tablas, Oracle Forms, SQL/PLSQL). Esto motiva el interés práctico y justifica que el DDL de referencia sea **compatible con Oracle**.

### Documentación complementaria del TFG

Memoria, plantilla y documento de experimentos: (preguntar ubicación o contenido necesario para tomar decisiones).
