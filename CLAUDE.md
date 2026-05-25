# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

---

## 1. Objetivo inmediato

Construir un **programa que, dado un conjunto de fragmentos de evidencia sobre un modelo documental MongoDB, llame a una API de LLM y produzca automáticamente un modelo relacional normalizado en DDL Oracle** — replicando mediante código y APIs el proceso que hasta ahora se realizaba manualmente en interfaces de chat.

La "evidencia" es heterogénea: schemas explícitos cuando los hay, pero también consultas (`find`/`aggregate`/`$project`), operaciones de escritura, ejemplos de documentos, accesos a campos desde código de aplicación o comentarios. **No se asume que el modelo documental esté declarado en schemas**; en muchos proyectos reales hay que inferirlo cruzando esas fuentes.

**Hito:** prototipo funcional listo para mostrar en la siguiente reunión con tutores.

**Decisiones tomadas:**

- Lenguaje: **Python 3.11+**.
- API por defecto: **Google Generative AI** vía SDK `google-genai`. Dos modelos por proveedor: el del pipeline (`gemma-4-31b-it`, free, solo texto) y el del agente de descubrimiento (`gemini-2.5-flash-lite`, free, con function-calling). Recomendación inicial de los tutores fue `gemma-3-27b-it`; Google lo retiró en mayo 2026 y se actualizó a `gemma-4-31b-it`.
- **Segundo proveedor implementado: Groq** vía SDK `groq` (API OpenAI-compatible). Defaults: `llama-3.3-70b-versatile` para el pipeline y `llama-3.1-8b-instant` para el agente. Resuelve el cuello de cuota del free tier de Google y cierra el cuasirequisito de "multi-proveedor" del TFG.
- Pipeline: **multi-paso de 4 fases** (lectura → análisis del modelo documental → diseño relacional → DDL Oracle). Cada paso intermedio se guarda en `out/` para inspección.
- Invocación: **CLI con click** — `python -m normalizer <input>` (los artefactos se escriben en `out/`, incluido el DDL final como `out/04_ddl.sql`).
- Formato de input: **archivo único, directorio curado o URL de repositorio Git público** (en el caso URL, un agente clona el repo y elige por sí mismo la evidencia — ver sección 2, hito 8).
- **Abstracción de proveedor LLM** (`normalizer/providers/` con `Protocol LLMProvider`) con dos métodos: `generate(prompt)` (texto-a-texto) y `chat(messages, tools)` (tool-use, para el agente). Implementaciones actuales: `GoogleProvider` y `GroqProvider`. Añadir uno más es: clase nueva en `providers/`, entrada en `_REGISTRY`, `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`.
- Paradigma del agente de descubrimiento: **tool-use nativo del SDK** (no bucle JSON manual ni framework externo). El bucle vive en `discovery/agent.py`; el provider solo expone un turno. Elegido pensando en que el mismo paradigma se reutilizará para el agente de refinamiento (RU-6) en un hito posterior.
- Output: DDL compatible con **Oracle**.

**Fuera del alcance de esta fase:**

- UI o frontend.
- Tercer proveedor adicional (Anthropic, OpenAI, Mistral, etc.). La abstracción está y dos providers ya la usan; añadir un tercero es un copy-paste.
- **Agente de refinamiento interactivo (RU-6)**: dialogar con el resultado para renombrar entidades, fusionar tablas, etc. La extensión `chat()` del provider ya está preparada para ello, pero el flujo no se implementa todavía.
- Descubrimiento sobre repos **privados** (autenticación) o **no-Git**.

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
8. **Agente de descubrimiento desde URL implementado** (`normalizer/discovery/`, RU-1.3 + RU-5): si el `INPUT_PATH` empieza por `http(s)://` o `git@`, la CLI clona el repo (cache en `.cache/repos/`), un agente LLM con tool-use (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`) localiza los archivos relevantes y los deposita en `out/00_discovery/evidence/` junto con una traza `discovery.md`. El pipeline lineal corre a continuación sin cambios sobre ese directorio.
9. **Validación parcial end-to-end** sobre `https://github.com/dan-divy/spruce` (`out-spruce-url/`): el agente eligió 7 archivos (los 4 schemas + 3 rutas) en 5 iteraciones. El `04_ddl.sql` resultante contiene **las 11 entidades del UML manual** + `post_likes` y `post_comments` legítimas (igual que el `out-difuso/`) + 1 tabla `test_names` que es ruido proveniente de un bug ya corregido (un retry externo metió `test/database_tests.js` en `evidence/` además de los 7 del run real).
10. **Bugs corregidos tras la validación:** (a) `DiscoveryState.__post_init__` ahora limpia `evidence/` al instanciar para que no leakeen archivos entre runs; (b) `GoogleProvider.generate()` también usa `_call_with_retry` (antes solo lo hacía `chat()`), con backoff que respeta el `retryDelay` del 429 — esto elimina la necesidad de relanzar el proceso desde fuera ante un rate-limit transitorio.
11. **Rotación de modelos de Google (mayo 2026):** `gemma-3-27b-it` desapareció del catálogo; el nuevo default del pipeline es `gemma-4-31b-it`. El default del agente fue inicialmente `gemini-2.5-flash-lite` (10 RPM, 20 RPD) y se actualizó después a `gemini-3.1-flash-lite` tras descubrir cuota más holgada — ver punto 22.
12. **Segundo proveedor implementado: Groq** (`normalizer/providers/groq.py`). API OpenAI-compatible vía SDK `groq`. Defaults: `llama-3.3-70b-versatile` (pipeline) y `qwen/qwen3-32b` (agente). `Message` se amplió con un campo `tool_name` porque Gemini empareja respuestas de tools por nombre y OpenAI/Groq por id; ahora se rellenan ambos en el bucle del agente.
13. **Gotcha de modelos en Groq para tool-use:** se probaron varios y solo Qwen funciona consistentemente. Resumen:
    - `llama-3.1-8b-instant` y `llama-3.3-70b-versatile`: emiten function calls con sintaxis **markup** (`<function=name>args</function>`) en lugar del slot estructurado `tool_calls`. La API de Groq los rechaza con `tool_use_failed`.
    - `openai/gpt-oss-20b`: usa el slot correcto pero **emite JSON malformado** en los argumentos (truncado al final).
    - `openai/gpt-oss-120b`: chain-of-thought que el parser de Groq **no consigue separar** del output final → `output_parse_failed`. Es el patrón típico de los modelos tipo o1: razonan en voz alta y Groq espera estructura.
    - **`qwen/qwen3-32b`**: funciona consistentemente con el formato OpenAI estructurado. Es el default del agente en Groq.
    - Los Llama siguen valiendo para el **pipeline** (texto-a-texto, sin tools).
14. **Validación end-to-end con Groq** (modelo agente `qwen/qwen3-32b`, modelo pipeline `llama-3.3-70b-versatile`): primer run produjo **10/11 entidades** del UML manual + `key_invokes` como sobre-normalización menor. Segundo run sobre el mismo input produjo **6/11**: Qwen decidió que `analytics` y `keys` eran "secundarios" y los saltó. **Varianza alta del agente con Qwen** — los runs oscilan entre 6 y 10 entidades sobre el mismo input. Por eso se forzó iteración del prompt y exploración de más modelos (siguiente hito).
15. **Catálogo de Groq probado completo para tool-use.** Solo `qwen/qwen3-32b` y `meta-llama/llama-4-scout-17b-16e-instruct` funcionan con la API OpenAI-compatible para nuestro agente. Llama 3.x emite markup en lugar del slot estructurado, `gpt-oss-20b` emite JSON malformado, `gpt-oss-120b` emite chain-of-thought no parseable, y los `groq/compound-*` no aceptan tools del cliente (vienen con sus propias precableadas). Llama 4 recupera POSTS por primera vez (que Qwen suele perder), pero Qwen recupera analytics/keys que Llama 4 suele perder — distintas "personalidades" exploratorias, no Pareto dominado.
16. **System prompt del agente reescrito** (`prompts/discovery_system.md`): de 75 líneas a 38, project-agnostic, con tres principios nuevos. (a) Cobertura sobre parsimonia: "mejor sobre-incluir que perder una entidad" — antes pedíamos "sé selectivo, mejor 6 archivos que 15" y los modelos débiles paraban demasiado pronto. (b) Prohibido descartar sin inspeccionar: no se puede marcar un archivo o directorio como "secundario" sin haber abierto su contenido. (c) Vecindad estructural: si encuentras un schema en `X/Y/foo`, debes inspeccionar los hermanos en `X/Y/` antes de cerrar — heurística agnóstica del layout que cubre el caso típico "schemas viven juntos". Más un suelo de exploración (≥2 subdirs listados, ≥4 archivos inspeccionados) y obligación de justificar descartes top-level en el `summary`.
17. **Lección: el modelo es el cuello de botella del agente, no el prompt.** Validación parcial con el prompt nuevo + Llama 4 Scout (`out-spruce-llama4-v3/`): **7/11 entidades** — mejor que el peor run de Qwen (6/11) pero peor que el mejor (10/11) y muy lejos del 11/11 de Gemini. Llama 4 ignora la regla de vecindad estructural (lee `user.js` pero no toca `room.js`/`keys.js`/`analytics.js` que están en el mismo directorio). El prompt nuevo es necesario y mejora la base, pero **la capacidad del modelo para honrar instrucciones complejas pone un techo** que el prompt no puede saltarse. Para Spruce con tool-use: Gemini 2.5 Flash Lite (Google, 11/11) > Qwen3-32B (Groq, 6-10) > Llama 4 Scout (Groq, 6-7) > Llama 3.x (no funciona).
18. **Qwen3-32B en Groq sufre el TPM cap del free tier** (6000 TPM). Iteraciones con historial moderado (≥6000 tokens en una petición) lo revientan con HTTP 413. El prompt nuevo solo ahorró ~150 tokens, insuficiente. Trabajar este modelo en serio requiere tier dev de pago o trimming agresivo del historial.
19. **Segundo run de Llama 4 Scout aún peor que v3** (`out-spruce-llama4-test/`): 8 iteraciones, **solo 2 archivos seleccionados** (`config/app.js` + `utils/models/user.js`), 4/11 entidades sustanciales en el DDL. El propio `summary` del agente identifica `analytics.js`/`keys.js`/`room.js` como "potencialmente relevantes" y aun así no los abre — ignora frontalmente la regla de vecindad estructural incluso cuando la nombra. Refuerza punto 17: el modelo es el techo y Llama 4 Scout tiene varianza alta + bias contrarian.
20. **Colapso del free tier de Google (mayo 2026).** Fuentes oficiales: Google recortó el free tier en diciembre 2025 "para liberar compute para Gemini 3 Pro" sin aviso previo. Estado actual de la cuenta del autor:
    - `gemini-2.0-flash` y `gemini-2.0-flash-lite`: **`limit: 0`** (retirados del free tier).
    - `gemini-2.5-flash` y `gemini-2.5-flash-lite`: **20 RPD** (antes 250+). Una sola corrida del agente con prompt nuevo (≥10-20 iter) iguala o supera el cap diario.
    - Familia `gemini-3.*`: paid tier focus, no figura en free tier público.
    - La página oficial `ai.google.dev/gemini-api/docs/rate-limits` ya no publica la tabla — redirige al dashboard de AI Studio.
    - **Bomba de relojería**: `MAX_ITERS = 20` coincide con RPD = 20. El prototipo no es defectuoso, simplemente el free tier de Google está dimensionado para "1 corrida/día".
21. **Cerebras identificado como mejor candidato free tier no implementado.** Free tier: 5 RPM / 30K TPM / **1M TPD** por modelo (vs 500K de Groq, 20 RPD de Google). Modelos free: `gpt-oss-120b`, `qwen-3-235b-a22b-instruct-2507` (hermano 7× del Qwen 32B que ya usamos), `llama3.1-8b`, `zai-glm-4.7`. API OpenAI-compatible → adaptar `groq.py` es casi copy-paste. Sin probar todavía. Investigación detallada en `notes/2026-05-25-free-tier-google-y-alternativas.md`.
22. **`gemini-3.1-flash-lite` validado como nuevo default del agente Google.** Inspeccionando el dashboard de AI Studio aparecen modelos `gemini-3.*` en el free tier que no estaban en la página pública. El más interesante: `gemini-3.1-flash-lite` con **15 RPM / 250K TPM / 500 RPD** — 1.5× RPM y **25× RPD** sobre el 2.5-flash-lite anterior. ID estable (no `-preview`), soporta `generateContent` y function-calling. Validación end-to-end sobre `https://github.com/dan-divy/spruce` (`out-spruce-3.1/`): el agente seleccionó los 4 schemas exactos en 13 iteraciones, sin ruido tipo `test/`. El pipeline se completó con Groq porque Gemma devolvió 500/503 transitorios — el cambio toca solo el agente, así que la validación del modelo nuevo es limpia. DDL final: 11/11 entidades del UML + 1 sobre-normalización legítima (`user_rooms`, junction redundante con `room_users`). La "bomba de relojería" del punto 20 queda **desactivada para Spruce**; Cerebras pasa a back-burner.
23. **Nuevo cuello potencial: RPM (no RPD) en proyectos reales.** El run de Spruce tocó **13/15 RPM** porque el agente lanza iteraciones casi seguidas. Con un repo realista (más archivos, jerarquía compleja, más iteraciones de exploración) probablemente saturará el cap y el SDK hará backoff entre turnos — el run se completará pero con wall-clock peor. La cuota diaria (500 RPD) ya no es el cuello; lo es **cuántas requests/min puede emitir el agente**. No bloquea validar proyectos grandes, solo los hace lentos.

**Siguiente:**

1. **Probar el agente con `gemini-3.1-flash-lite` sobre un repo más grande/realista** (no Spruce). El run de Spruce ya rozó el cap RPM con sólo 4 schemas — un proyecto real es el test relevante. Medir: ¿completa la corrida? ¿cuánto baja el wall-clock por el backoff? ¿el modelo mantiene la calidad de selección en repos con más ruido?
2. **Si el RPM cap del free tier se confirma bloqueante** en proyectos reales, las opciones son:
   - **Tier dev de Google** (paid) — sube el RPM pero rompe el "free tier".
   - **Cerebras como provider alternativo** — sigue siendo el candidato más prometedor (qwen-3-235b free, 1M TPD). Antes el caso era el RPD; ahora sería el RPM. Implementación: copy-paste de `groq.py`. Verificar antes en `inference-docs.cerebras.ai/llms.txt` que el modelo elegido soporta tools.
   - **Multi-proveedor balanceado** — agente en Google, pipeline en Groq (esta corrida lo hizo así de facto por el 500 de Gemma). Requeriría un `--agent-provider` separado en la CLI; ahora mismo el `--provider` es único.
3. **Considerar bajar `MAX_ITERS`** o añadir un cap blando — si el agente necesita >15 iter quizá es señal de prompt aún demasiado abierto. Doblemente relevante ahora con el RPM cap.
4. Si la varianza del agente sigue siendo problemática para defender, dos vías:
   - **Subir de modelo**: tier dev de Groq (Qwen sin TPM cap), o billing en Google.
   - **Múltiples runs + agregación**: correr el agente 3 veces y unir las evidencias. Más caro pero baja la varianza efectiva sin tocar prompt.
5. Cuando se vuelva a iterar sobre la calidad del DDL: hay puntos menores conocidos que el autor decidió **no atacar ahora** porque "más o menos funciona" — el `04_ddl.sql` se emite envuelto en ` ```sql ... ``` ` (no es ejecutable tal cual sin pelar el cerco), y se usa `BOOLEAN` que Oracle no tiene nativo en versiones <23. Si en el futuro se fija una versión Oracle objetivo o se necesita ejecutar el SQL automáticamente, esos dos puntos vuelven a ser relevantes.

**Convención de directorios de salida:** cada run usa su propio `--out-dir` (`out-facil/`, `out-difuso/`, `out-spruce-llama4-v3/`, etc.) para no pisarse. Los runs intermedios suelen purgarse cuando dejan de ser referencia; los actuales en disco se ven con `ls -d out-*`. El directorio `out/` por defecto NO debe asumirse vinculado a ningún dataset concreto.

---

## 3. Estructura del código

```
normalizer/
├── __init__.py
├── __main__.py             # `python -m normalizer` → cli.main
├── cli.py                  # click CLI: --provider, --model, --agent-model, --out-dir
├── pipeline.py             # 4 pasos; los prompts se cargan desde normalizer/prompts/
├── prompts/                # prompts como .md intercambiables sin tocar Python
│   ├── __init__.py         # carga al importar: ANALYZE, DESIGN, DDL, DISCOVERY_SYSTEM
│   ├── analyze.md          # paso 1 del pipeline (placeholder {evidence})
│   ├── design.md           # paso 2 del pipeline (placeholder {analysis})
│   ├── ddl.md              # paso 3 del pipeline (placeholder {design})
│   └── discovery_system.md # system prompt del agente de descubrimiento
├── discovery/              # agente que descubre evidencia desde URL de repo
│   ├── __init__.py         # expone discover_from_url()
│   ├── agent.py            # bucle chat()-tools hasta `done` o presupuesto agotado
│   ├── tools.py            # ToolSpecs + dispatch (list_dir, read_file, grep, select_evidence, done)
│   ├── filesystem.py       # filtrado del árbol y validación anti path-traversal
│   └── repo.py             # git clone --depth 1 con cache en .cache/repos/
└── providers/
    ├── base.py             # Protocol LLMProvider con generate() y chat() + dataclasses (Message, ToolSpec, ToolCall, ChatResponse)
    ├── google.py           # GoogleProvider: SDK google-genai
    ├── groq.py             # GroqProvider: SDK groq (OpenAI-compatible)
    └── __init__.py         # registry + build_provider(for_agent=...) + DEFAULT_MODELS / DEFAULT_AGENT_MODELS
data/
├── spruce/                 # 4 schemas Mongoose (caso fácil)
└── spruce-difuso/          # 8 archivos de servidor sin schemas (caso realista)
notes/                      # notas de sesión (YYYY-MM-DD-<tema>.md); contexto histórico complementario a CLAUDE.md
out-*/                      # cada run usa su propio --out-dir (gitignored)
                            # Convención: out-<dataset>[-<variante>]/ p. ej.
                            #   out-facil/, out-difuso/, out-spruce-url/,
                            #   out-spruce-llama4-v3/  (el actual en disco)
out/                        # default si no se pasa --out-dir, no asumir contenido
.cache/repos/               # repos clonados por el agente              (gitignored)
```

**Sobre `notes/`:** material complementario para la memoria del TFG. Dos tipos:

- **Logs de sesión** con formato `YYYY-MM-DD-<tema>.md`: el *qué se hizo y por qué* de una sesión grande, útil para reconstruir el razonamiento detrás de varios commits relacionados. Crear solo si la sesión cierra un hito o introduce una decisión arquitectural.
- **Documentos vivos** con nombre temático sin fecha (p. ej. `proceso-agentico-explicado.md`): explicación conceptual de partes del código pensada para defender el TFG y nutrir la memoria. Crecen a medida que se exploran nuevos aspectos.

Ninguno es el estado actual (eso vive en CLAUDE.md) ni reemplaza al historial git.

Principios que conviene preservar:

- **El pipeline solo conoce `LLMProvider`**: nunca importa SDKs concretos. Añadir un proveedor nuevo es: clase nueva en `providers/`, entrada en `_REGISTRY`, `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`. Cero cambios en `pipeline.py` o `cli.py`.
- **Dos modelos por proveedor**: el del pipeline (`--model`, defaults en `DEFAULT_MODELS`) puede ser barato/free porque solo hace texto→texto; el del agente (`--agent-model`, defaults en `DEFAULT_AGENT_MODELS`) necesita function-calling — por eso para Google el default del agente es `gemini-3.1-flash-lite` y no `gemma-4-31b-it`.
- **El agente despacha tools, el provider solo expone un turno.** `LLMProvider.chat(messages, tools)` devuelve la decisión del modelo (texto o `tool_calls`); el bucle agéntico vive en `discovery/agent.py`. Esto mantiene la responsabilidad de "saber del SDK" dentro del provider y la de "saber del repo" dentro de `discovery/`.
- **Prompts en `normalizer/prompts/*.md`**, intercambiables editando el archivo sin tocar Python. `__init__.py` los carga al importar y los expone como `ANALYZE`, `DESIGN`, `DDL`, `DISCOVERY_SYSTEM`. Los del pipeline tienen placeholders `{evidence}`/`{analysis}`/`{design}` (formato `str.format`); el del agente no. Cuidado al `.format()` un prompt cuyo contenido tiene `{...}` literales (caso de `discovery_system.md`, con `new Schema({...})` en los ejemplos): por eso no se le aplica `.format()` en el código actual.
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

RU-1. Suministro del modelo de datos de entrada
El usuario debe poder proporcionar al sistema el modelo de base de datos desnormalizado que se quiere analizar, a través de distintos mecanismos según el grado de elaboración del material disponible.
RU-1.1 Carga desde archivo de schemas
El usuario debe poder seleccionar un único archivo que contenga la definición explícita de los schemas de una base de datos documental (por ejemplo, schemas Mongoose en JavaScript) y entregárselo al sistema como entrada.
RU-1.2 Carga desde directorio de evidencia heterogénea
El usuario debe poder proporcionar un conjunto de archivos previamente curados que contengan evidencia heterogénea del modelo documental: schemas explícitos, consultas, operaciones de escritura, ejemplos de documentos, accesos a campos desde código de aplicación, comentarios, etc..) Y obtener un resultado igualmente útil cuando no exista una declaración explicita de schemas.

RU-1.3 Análisis a partir de la URL de un repositorio
El usuario debe poder proporcionar únicamente la URL pública de un repositorio de código que contenga una aplicación basada en una base de datos documental, sin necesidad de seleccionar manualmente los archivos relevantes ni de preparar ningún material previo.
RU-2. Análisis del modelo documental
El usuario debe poder obtener, a partir de la entrada proporcionada, una descripción comprensible del modelo documental subyacente que le permita conocer cómo se ha interpretado su material.
RU-2.1 Identificación de entidades y atributos
El usuario debe poder conocer qué entidades (colecciones de documentos) se han identificado en su entrada, así como los atributos que componen cada una y, en la medida de lo posible, sus tipos de datos.
RU-2.2 Detección de relaciones implícitas
El usuario debe poder conocer las relaciones entre entidades que se han detectado, distinguiendo entre referencias por identificador, documentos embebidos y arrays anidados, incluso cuando estas relaciones no estuvieran declaradas formalmente en su material.
RU-2.3 Trazabilidad del análisis
El usuario debe poder consultar un documento intermedio que explique con qué evidencias se ha llegado a cada entidad, atributo o relación detectados, de modo que pueda validar o discutir el razonamiento del sistema.
RU-3. Generación del modelo relacional normalizado
El usuario debe poder obtener, a partir del modelo documental analizado, un modelo relacional normalizado equivalente que le sirva como base de partida para una migración o un rediseño.
RU-3.1 Diseño de tablas, claves primarias y foráneas
El usuario debe obtener un modelo relacional con tablas, claves primarias bien definidas y claves foráneas explícitas para las relaciones detectadas.
RU-3.2 Eliminación de redundancias
El usuario debe obtener un modelo relacional que minimice las redundancias presentes en el modelo documental original: arrays embebidos normalizados en tablas hijas, valores duplicados en distintos documentos consolidados en tablas independientes y atributos repetidos por denormalización reconciliados en una única columna canónica.
RU-3.3 Generación de DDL Oracle
El usuario debe poder obtener el modelo relacional final como un conjunto de sentencias DDL compatibles con Oracle (CREATE TABLE, claves primarias, claves foráneas y restricciones).
RU-4. Independencia y configuración del proveedor de LLM
El usuario no debe quedar atado a un único proveedor de LLM, ni a un único modelo dentro de un proveedor.
RU-4.1 Elección del proveedor
El usuario debe poder elegir, en el momento de invocar la herramienta, qué proveedor de LLM se utilizará (por ejemplo, Google, Anthropic, OpenAI).
RU-4.2 Elección del modelo concreto
El usuario debe poder seleccionar, dentro del proveedor elegido, el modelo concreto a emplear (por ejemplo, distintos modelos de la misma familia).
RU-4.3 Gestión segura de credenciales
El usuario debe poder configurar las credenciales (API keys) de los proveedores sin tener que modificar el código de la herramienta y sin que éstas queden registradas en repositorios públicos.
RU-5. Uso de agentes para análisis de repositorios
El usuario debe poder delegar en agentes inteligentes la tarea de localizar dentro de un repositorio cuál es la información relevante para reconstruir el modelo documental.
RU-5.1 Descubrimiento autónomo de archivos relevantes
El usuario debe poder confiar en que, dada únicamente la URL de un repositorio, los agentes localicen por sí mismos los archivos que contienen evidencia útil del modelo documental, sin necesidad de que el usuario los identifique o los aporte manualmente.
RU-5.2 Justificación de las decisiones del agente
El usuario debe poder consultar una traza o explicación de por qué el agente ha seleccionado unos archivos y descartado otros, para poder confiar en su criterio o corregirlo.
RU-6. Interacción del usuario con el resultado mediante agentes
El usuario debe poder no sólo recibir un resultado final estático, sino dialogar con el sistema para refinarlo según su criterio.
RU-6.1 Revisión y modificación guiada del modelo relacional
Una vez generado el modelo relacional, el usuario debe poder solicitar cambios en lenguaje natural (renombrar entidades, fusionar tablas, dividir una entidad, reinterpretar una relación, etc.), y un agente debe encargarse de aplicar esos cambios manteniendo la coherencia del modelo y del DDL resultante.
RU-6.2 Iteración hasta resultado satisfactorio
El usuario debe poder iterar varias rondas de refinamiento con el agente hasta dar por bueno el modelo, sin tener que reiniciar todo el pipeline desde cero en cada cambio.
RU-7. Interfaz de uso de la herramienta
El usuario debe poder utilizar la herramienta mediante una interfaz adecuada a su perfil, ya sea técnica o no técnica.
RU-7.1 Interfaz de línea de comandos (CLI)
El usuario debe poder utilizar la herramienta desde una interfaz de línea de comandos, de modo que pueda integrarla en pipelines automatizados o utilizarla en entornos sin escritorio gráfico.
RU-7.2 Interfaz gráfica de usuario (GUI)
El usuario debe poder utilizar la herramienta desde una interfaz gráfica que le permita cargar la entrada de forma visual, seguir el avance del proceso, inspeccionar los resultados intermedios, visualizar el modelo relacional generado y dialogar con el agente de refinamiento, sin necesidad de conocer la sintaxis de la línea de comandos.
RU-8. Inspección de los resultados intermedios
El usuario debe poder inspeccionar todos los artefactos producidos por el sistema durante el proceso, no sólo el DDL final, para entender, depurar y comparar ejecuciones.
RU-8.1 Acceso a los artefactos por fases
El usuario debe poder acceder a los resultados de cada fase del proceso (entrada agregada, análisis del modelo documental, diseño relacional, DDL final) como archivos independientes que pueda abrir y consultar.
RU-8.2 Aislamiento de ejecuciones
El usuario debe poder lanzar varias ejecuciones sobre distintos casos de prueba sin que los resultados de una sobrescriban los de otra.
RU-9. Prototipo CLI
El usuario debe poder disponer de un prototipo en línea de comandos que cubra el flujo completo de la herramienta para los casos de entrada de tipo archivo y directorio curado.
RU-9.1 Ejecución end-to-end
El usuario del prototipo debe poder, mediante una única invocación, ejecutar todo el proceso de transformación (lectura, análisis, diseño, DDL) y obtener el DDL Oracle final sobre los datasets de prueba.
RU-9.2 Validación frente al modelo de referencia
El usuario debe poder validar el prototipo comparando cualitativamente su salida con el modelo relacional de referencia elaborado manualmente para el repositorio de prueba seleccionado(Spruce).

### Contexto profesional del autor

Trabaja con un sistema legacy basado en Oracle (~6000 tablas, Oracle Forms, SQL/PLSQL). Esto motiva el interés práctico en LLMs aplicados al análisis y migración de esquemas complejos, y justifica que el DDL de referencia sea **compatible con Oracle**.

### Documentación complementaria del TFG

Memoria, plantilla y documento de experimentos: (preguntar ubicacion o contenido necesario para tomar decisiones y acceder al contenido)
