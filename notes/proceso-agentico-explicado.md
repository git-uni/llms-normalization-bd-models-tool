# Proceso agéntico — explicación para la memoria

Documento vivo que recoge cómo funciona el agente de descubrimiento del prototipo, pensado como material para la memoria del TFG. Crece a medida que se exploran nuevos aspectos; cada sección apunta al archivo y líneas concretas del código.

**Índice y estado:**

1. [Qué es tool-use / function calling conceptualmente](#1-qué-es-tool-use--function-calling-conceptualmente) — cubierto
2. [El bucle del agente, paso a paso](#2-el-bucle-del-agente-paso-a-paso) — cubierto
3. Roles de mensajes y traducción a Gemini — pendiente
4. `ToolSpec`, `ToolCall`, `ChatResponse` — pendiente
5. `DiscoveryState` y `dispatch` — pendiente

**Apéndices:**

- [A. Cuántas peticiones consume un run del agente](#a-cuántas-peticiones-consume-un-run-del-agente)
- [B. El modelo del agente es intercambiable vía CLI](#b-el-modelo-del-agente-es-intercambiable-vía-cli)
- [C. Alternativas gratuitas a Google con cuota suficiente](#c-alternativas-gratuitas-a-google-con-cuota-suficiente)
- [D. Los formatos de function calling y por qué seguimos el de OpenAI](#d-los-formatos-de-function-calling-y-por-qué-seguimos-el-de-openai)
- [E. Sobre Groq como proveedor (contexto para defender la elección)](#e-sobre-groq-como-proveedor-contexto-para-defender-la-elección)
- [F. Diseño del system prompt del agente y por qué el modelo es el cuello de botella](#f-diseño-del-system-prompt-del-agente-y-por-qué-el-modelo-es-el-cuello-de-botella)

---

## 1. ¿Qué es tool-use / function calling conceptualmente?

### El LLM solo genera texto. Punto.

Esto es lo primero que hay que tener claro: un LLM no "ejecuta" código, no "llama" funciones, no "abre" archivos. Lo único que hace es **generar tokens** (trocitos de texto) a continuación de un prompt. Cuando decimos "el agente lee un archivo del repo", lo que realmente pasa es:

1. El LLM **genera texto** que dice "quiero leer el archivo X".
2. **Nuestro código Python** (no el LLM) ve ese texto, abre el archivo de verdad y lo lee.
3. El contenido del archivo se inserta en el prompt como **texto adicional**.
4. El LLM ve ese texto en el siguiente turno y sigue generando.

El LLM no toca el disco nunca. El disco solo lo toca Python.

### ¿Y entonces qué es "function calling"?

"Function calling" o "tool use" es una **convención estructurada** para ese ida-y-vuelta. Dos opciones:

**Opción A — ingenua (prompt-as-JSON):** podríamos pedir en el system prompt "responde siempre en JSON con la forma `{tool: ..., args: ...}` o `{respuesta_final: ...}`" y parsear el texto generado nosotros. Funciona pero es frágil: a veces el modelo se sale del formato, mete comentarios, rompe el JSON.

**Opción B — function calling nativo:** los SDKs modernos (Google, Anthropic, OpenAI) tienen un **slot estructurado** en la API específicamente para esto:

- En la petición, declaras las "tools" que el modelo puede invocar (nombre, descripción, parámetros).
- En la respuesta, además del campo `text` hay un campo `function_calls` separado.
- El modelo ha sido **entrenado** para usar ese slot cuando decide invocar una tool, y para usar `text` cuando da la respuesta final.

Ventajas sobre la opción A: el formato no se rompe (el SDK lo valida), está separado limpiamente del texto libre, el modelo entrenado en este protocolo lo respeta mejor.

### El flujo de un turno con tools

Esquemáticamente lo que pasa en cada vuelta del bucle del agente:

```
[Petición]
  system: "eres un agente que..."
  user:   "explora este repo y encuentra evidencia..."
  tools:  [list_dir, read_file, grep, select_evidence, done]   ← schemas

         ↓ envío a Gemini

[Respuesta]
  text:           (vacío o None)
  function_calls: [{name: "list_dir", args: {path: "models/"}}]

         ↓ tu código Python intercepta el function_call

[Despacho local]
  Python ejecuta dispatch(call) → "f models/user.js [1251]\nf models/room.js..."

         ↓ siguiente petición incluye ese resultado

[Nueva petición]
  system: "eres un agente que..."
  user:   "explora este repo..."
  assistant: (mensaje con function_call list_dir)
  tool:   (resultado del list_dir)            ← se reinyecta como mensaje nuevo
  user:   (implícito: "sigue")
  tools:  [...]
```

El bucle **continúa hasta que el modelo responde sin `function_calls`** (texto libre = respuesta final) o llama a una tool especial como nuestro `done` que rompemos a propósito.

### Por qué necesitas el bucle (no es opcional)

Una sola llamada al LLM con tools declaradas **no resuelve el problema completo** porque el modelo no tiene los resultados todavía. La primera respuesta solo puede decir "para empezar quiero leer X". Necesitas:

1. Ejecutar X.
2. Mostrarle el resultado.
3. Que decida qué hacer a continuación.
4. Repetir.

Esto es lo que en nuestro código vive en `discovery/agent.py:56-82` — el `for i in range(max_iters):` con `provider.chat(messages, ALL_TOOLS)` dentro.

### Dónde está cada pieza en nuestro código

| Concepto | Dónde vive | Qué hace |
|---|---|---|
| Declaración de tools (schemas) | `discovery/tools.py:53-152` (`TOOL_LIST_DIR`, etc.) | `ToolSpec` con `name`, `description`, `parameters` JSON Schema |
| Traducción al SDK de Google | `providers/google.py:_to_gemini_tools` | convierte `ToolSpec` → `types.FunctionDeclaration` |
| Petición de un turno | `providers/google.py:chat()` | empaqueta historial + tools, llama a `generate_content`, parsea respuesta |
| Despacho de la tool | `discovery/tools.py:dispatch()` | ejecuta de verdad la acción en Python según `call.name` |
| Bucle | `discovery/agent.py:discover_from_url` | acumula `messages`, alterna petición → dispatch → resultado |

### Lo que el LLM ve vs lo que tú escribes

Una cosa que despista: el `SYSTEM_PROMPT` del agente (`prompts/discovery_system.md`) describe en lenguaje natural lo que las tools hacen. Pero **eso no es lo que activa la tool**. Lo que de verdad activa la tool es la **declaración estructurada** en el array `tools` de la petición — es decir, los `ToolSpec` con su `description` y `parameters`. El system prompt sirve para dar contexto adicional (cómo trabajar, en qué orden, criterios), pero las tools en sí están descritas dos veces:

- En el system prompt (instrucción humana, para guiar)
- En el array `tools` (declaración estructurada, lo que el modelo realmente "ve" como invocable)

Ambas tienen que ser coherentes; si las desincronizas, el modelo se confunde.

---

## 2. El bucle del agente, paso a paso

Recorrido línea a línea por `discovery/agent.py` (~120 líneas, todo el núcleo agéntico está ahí).

### Fase 0 — Setup (líneas 36-53)

Antes de meter al LLM en el bucle hay tres pasos de preparación:

**Línea 36 — `repo_root = clone_repo(url)`**
Llama a `discovery/repo.py:clone_repo`, que hace `git clone --depth 1 <url> .cache/repos/<sha>`. Si ya está clonado en caché, lo reutiliza tal cual y devuelve la ruta. El LLM no se entera de esto; trabaja sobre el filesystem local como si nada.

**Líneas 37-40 — `state = DiscoveryState(...)`**
Crea el objeto de estado (lo veremos a fondo en la sección 5). Lo importante ahora es saber que `state` acumula **lo que el agente va decidiendo** a lo largo del bucle: archivos seleccionados, razones, resumen final, flag `is_done`. Es la memoria del agente del lado Python — el LLM no ve este objeto, lo manipula indirectamente vía las tools.

**Línea 41 — `tree = build_tree_summary(repo_root)`**
Genera un listado plano del repo filtrado (sin `node_modules/`, sin binarios). Algo como:

```
d normalizer/
d normalizer/discovery/
f normalizer/discovery/agent.py [3568]
...
```

Esto es lo único que el LLM ve para hacerse una idea inicial de qué hay en el repo. **No le metemos el contenido de los archivos**, solo el listado — para que decida él qué leer.

**Líneas 43-53 — Construcción del historial inicial (`messages`)**
Aquí está el bootstrap del agente. Dos mensajes:

- `system`: el contenido de `discovery_system.md` — instrucciones permanentes ("eres un agente que…", "cómo trabajar", "reglas duras").
- `user`: la "tarea concreta" de esta sesión — URL del repo, árbol y orden ("localiza la evidencia y termina con `done`").

Este `messages` es una **lista que va a crecer en cada iteración**. Cada vuelta añade:

- el mensaje del asistente (su respuesta de ese turno, incluyendo function_calls si hubo),
- y los mensajes `tool` (los resultados de despachar cada function_call).

### Fase 1 — El bucle (líneas 55-82)

```python
for i in range(max_iters):                              # ← presupuesto duro
    iters_used = i + 1
    response = agent_provider.chat(messages, ALL_TOOLS) # ← un turno del LLM
    messages.append(response.assistant_message)         # ← guarda lo que dijo

    if not response.tool_calls:                         # ← respondió texto libre
        ...
        break

    for call in response.tool_calls:                    # ← uno o varios calls
        result = dispatch(call, state, max_files=max_files)
        messages.append(Message(role="tool", content=result, tool_call_id=call.name))

    if state.is_done:                                   # ← el agente llamó a done()
        break
```

#### Línea 56 — `for i in range(max_iters)`

**Presupuesto duro.** El agente NO controla cuántas vueltas dar. Si llega a 20 iteraciones sin pedir `done`, cortamos. Esto es **vital**: sin esto, un fallo del modelo (entrar en un bucle estéril de `list_dir`) costaría cuota indefinidamente. La regla general en agentes: nunca confíes en que el modelo termine por sí solo, ponle límite por arriba siempre.

#### Línea 58 — `response = agent_provider.chat(messages, ALL_TOOLS)`

**El único punto donde se habla con el LLM en todo el archivo.** Le pasamos:

- `messages`: todo el historial acumulado hasta ahora.
- `ALL_TOOLS`: las 5 declaraciones de tools (cada vuelta las mandamos otra vez; la API es stateless).

`response` es un `ChatResponse` con tres campos: `assistant_message`, `text`, `tool_calls`.

Hay una cosa importante aquí: **el historial se manda entero cada vez**. La API de Gemini (y de los demás) no recuerda nada entre llamadas; cada petición es independiente. Por eso `messages` crece y se reenvía completo en cada iteración. Esto también explica por qué se acaba la cuota rápido: los tokens del historial cuentan en cada turno.

#### Línea 59 — `messages.append(response.assistant_message)`

Antes de despachar nada, **el mensaje del asistente entra al historial**. Esto es importante: si en el turno siguiente vuelves a llamar al modelo sin haber añadido su propia respuesta, "olvida" lo que él mismo decidió. El asistente tiene que verse a sí mismo en el historial para mantener coherencia (ej.: "ya pedí `list_dir(models/)`, así que ahora pediré `read_file(models/user.js)`").

#### Líneas 61-69 — Caso "el modelo respondió sin tools"

Si `response.tool_calls` está vacío, significa que el modelo decidió responder con texto libre en lugar de seguir invocando herramientas. En la dinámica que diseñamos, **esto es anómalo**: nuestro contrato (en el system prompt) es que siempre termine llamando a `done`. Si lo salta y responde texto, no hay un cierre limpio. Salimos del bucle pero anotamos un WARN en el resumen para que se vea en `discovery.md`.

#### Líneas 71-79 — Despachar cada function_call

```python
for call in response.tool_calls:
    result = dispatch(call, state, max_files=max_files)
    messages.append(Message(role="tool", content=result, tool_call_id=call.name))
```

Tres cosas pasan aquí:

1. **`dispatch(call, state, …)`** — el código real que ejecuta lo que el LLM pidió. Está en `discovery/tools.py:dispatch`, mira `call.name` y ramifica a `_do_list_dir`, `_do_read_file`, etc. Devuelve un `str` con el resultado (un listado, el contenido del archivo, una confirmación de selección…). Esto es Python puro contra el filesystem; el LLM no está implicado en esta línea.
2. **Algunas tools modifican `state`** — concretamente `select_evidence` añade al `state.selected`, `done` pone `state.is_done = True` y guarda el `summary`. Ese es el "canal" por el que las decisiones del modelo se materializan del lado Python.
3. **`messages.append(Message(role="tool", ...))`** — el resultado del despacho se reinyecta al historial como un mensaje nuevo de rol `tool`. Así el LLM lo verá en el siguiente turno. El `tool_call_id=call.name` es porque Gemini empareja resultados con llamadas por nombre (no por id, a diferencia de OpenAI/Anthropic). Eso se ve en detalle en la sección 3.

Nota sutil: el `for` itera sobre `response.tool_calls` porque **un solo turno puede contener varias function_calls** (el modelo puede pedir paralelizar). En nuestros runs reales casi siempre es 1 por turno, pero el código contempla N.

#### Líneas 81-82 — `if state.is_done: break`

Después de despachar todas las calls del turno, miramos si alguna fue `done`. Si sí, salimos del bucle. Esta es la **salida normal**.

### Fase 2 — Cierre (líneas 84-92)

```python
if not state.is_done and iters_used >= max_iters:
    state.summary = (... + "[WARN: presupuesto agotado ...]")

_write_discovery_md(state, url=url, iters_used=iters_used)
return state.evidence_dir
```

Detectamos el caso "agotó el presupuesto sin llamar a `done`" (otro caso anómalo, anotamos WARN). Luego escribimos `discovery.md` con la traza completa: URL, repo local, iteraciones, archivos seleccionados con sus razones, resumen del agente. Y devolvemos `state.evidence_dir` a la CLI, que se la pasa al pipeline como si fuera un directorio curado a mano.

### Resumen visual de un turno

```
                    ┌─────────────────────┐
                    │ messages (crece)    │
 ─────────────────► │ + ALL_TOOLS         │ ─────► provider.chat() ──┐
 ┌──┐               └─────────────────────┘                          │
 │  │                                                                ▼
 │ Si is_done                                              ┌──────────────────┐
 │ o sin tool_calls,                                       │ ChatResponse:    │
 │ break                                                   │ - assistant_msg  │
 │  ▲                                                      │ - text           │
 │  │                                                      │ - tool_calls[]   │
 │  │                                                      └──────────────────┘
 │  │                                                                │
 │  │       ┌────────────────────────────────────────────────────────┘
 │  │       ▼
 │  │  messages.append(assistant_message)
 │  │       │
 │  │       ▼
 │  │  ¿hay tool_calls?
 │  │       │
 │  │   ┌───┴───┐
 │  │   no      sí
 │  │   │       │
 │  └───┘       ▼
 │       for call in tool_calls:
 │           result = dispatch(call, state)
 │           messages.append(Message(role="tool", content=result, ...))
 │           # algunas tools mutan state (select_evidence, done)
 │                       │
 └───────────────────────┘
```

### Conceptos clave para defender este archivo

1. **El bucle es necesario** porque el LLM no ve los resultados de sus propias decisiones hasta que se los enseñas explícitamente en el siguiente turno.
2. **El historial crece y se reenvía completo cada turno** — la API es stateless.
3. **El presupuesto duro (`max_iters`) es obligatorio**, no opcional: protege contra bucles estériles.
4. **`state` es la "memoria estructurada"** del lado Python; el `messages` es la "memoria conversacional" del lado LLM. Ambas crecen en paralelo y reflejan lo mismo desde dos ángulos.
5. **Hay tres salidas:** `done` (normal), respuesta sin tool_calls (anómala, WARN), presupuesto agotado (anómala, WARN). Las tres están contempladas.
6. **Las tools pueden venir en lote en un turno** (el `for call in response.tool_calls`); el código no asume "una por vuelta".

---

## A. Cuántas peticiones consume un run del agente

Depende del tamaño del repo y de cuántas vueltas necesite el agente:

| Fase | Llamadas | Modelo / cuota |
|---|---|---|
| Agente (descubrimiento) | **N** iteraciones del bucle, 1 `chat()` por vuelta | `gemini-2.5-flash-lite` (20 RPD free en esta cuenta) |
| Pipeline (analyze + design + DDL) | **3** llamadas `generate()` fijas | `gemma-4-31b-it` (cuota separada) |
| **Total contra la API** | **N + 3** | repartido en dos quotas distintas |

`N` en runs reales:

- **Repo limpio con schemas explícitos** (Spruce caso fácil, observado): **5 iteraciones**. El agente encuentra `utils/models/` rápido, lo lista, selecciona los 4 schemas + algunas rutas y llama a `done`.
- **Repo realista mediano:** estimado **8-12 iteraciones**.
- **Tope duro:** **20 iteraciones** (`MAX_ITERS` en `agent.py:24`).

Rango realista por run:

- Mínimo: **~8 peticiones** (5 agente + 3 pipeline).
- Típico: **~13** (10 agente + 3 pipeline).
- Máximo: **23** (20 agente + 3 pipeline).

### Detalles importantes

**El retry transparente sobre 429 multiplica:** si una llamada lógica falla con rate-limit y reintenta, eso son 2 o más peticiones HTTP reales para una única llamada lógica. Hasta 4× por configuración en `google.py:_MAX_RETRIES`.

**Los tokens crecen cuadráticamente con N**, no las peticiones. Cada turno del agente reenvía **el historial completo** (la API es stateless). Turno 1: ~3000 tokens. Turno 5: ~15000+ tokens.

**Las dos cuotas son independientes** porque son modelos distintos. En esta cuenta concreta el cuello de botella es el agente: 20 RPD significan **~4 runs end-to-end por día** del caso fácil. Si quieres más, hay que cambiar de modelo o pagar.

**Optimización barata si se vuelve un problema:** meter en el primer prompt al agente algunas pistas del árbol ya pre-procesadas para reducir N. Hoy le mandamos el árbol crudo y deducir requiere 1-2 vueltas extra.

---

## B. El modelo del agente es intercambiable vía CLI

El flag está en `cli.py:25-31`:

```python
@click.option(
    "--agent-model",
    default=None,
    help="Modelo del agente de descubrimiento (...). Requiere soporte de function-calling.",
)
```

Es texto libre — pasa lo que pongas directo al SDK del proveedor sin validar contra una lista predefinida.

### Cómo encaja con `--provider`

Las dos opciones se combinan: `--provider` elige la **clase** del proveedor; `--agent-model` elige el **modelo concreto** que esa clase invoca:

```bash
# Default todo Google
python -m normalizer https://github.com/x/y

# Cambiar solo el modelo del agente, dentro de Google
python -m normalizer https://github.com/x/y --agent-model gemini-2.5-flash

# Si en el futuro existe AnthropicProvider:
python -m normalizer https://github.com/x/y --provider anthropic --agent-model claude-haiku-4-5
```

### Restricciones

**Sí está restringido al proveedor especificado**, pero implícitamente: `build_provider(name=provider_name, model=agent_model, for_agent=True)` instancia la clase de `provider_name`, y esa clase solo habla con su propio SDK. Si pones `--provider google --agent-model claude-haiku-4-5`, el `GoogleProvider` mandará la petición a la API de Google con `model="claude-haiku-4-5"` y Google devolverá 404 NOT_FOUND.

**No hay validación de capacidades.** Si pones `--agent-model gemma-4-31b-it` (un modelo que no soporta function-calling), el agente lanzará `chat()` con tools declaradas, la API rechazará la petición y verás un error en la primera iteración.

**No hay validación contra el catálogo del proveedor.** Cualquier string vale. Lo único que se valida es el `--provider` (vía `click.Choice(available_providers())`).

### Dos flags porque el pipeline y el agente tienen necesidades distintas

- `--model` (pipeline): solo necesita generar texto → cualquier modelo barato vale.
- `--agent-model` (agente): necesita function-calling → tiene que ser un modelo capable.

Por eso `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS` son diccionarios separados, no uno solo.

---

## C. Alternativas gratuitas a Google con cuota suficiente

Google ahoga enseguida con tools (20 RPD en el tier gratis de `gemini-2.5-flash-lite`). Tres opciones para iterar más cómodamente:

### Groq — top pick (implementado)

Free tier muy generoso (orden de magnitud ~14k peticiones/día en `llama-3.3-70b-versatile`), latencia muy baja, API **compatible con OpenAI**, hospeda modelos open-weight. Encajó porque:

- Cuota cómoda para iterar.
- Implementar `GroqProvider` se redujo a copiar `GoogleProvider` y cambiar el cliente (~100 líneas).
- Sin tarjeta, basta cuenta gratis.
- Cierra el cuasirequisito de "segundo proveedor" del TFG.

**Aviso empírico: no todos los modelos del catálogo de Groq sirven para tool-use con la API OpenAI-compatible.** Se probaron cuatro candidatos contra el repo Spruce; solo uno funciona:

| Modelo | Resultado |
|---|---|
| `llama-3.1-8b-instant` | ❌ emite function calls en formato markup (`<function=...>`) en vez del slot estructurado → `tool_use_failed` |
| `llama-3.3-70b-versatile` | ❌ mismo problema que el 8B |
| `openai/gpt-oss-20b` | ❌ usa el slot correcto pero emite JSON malformado en los argumentos |
| `openai/gpt-oss-120b` | ❌ chain-of-thought en voz alta que el parser de Groq no consigue separar → `output_parse_failed` |
| `qwen/qwen3-32b` | ✅ funciona consistentemente |

Por eso el default del agente en Groq es **`qwen/qwen3-32b`**. Los Llama siguen valiendo para el **pipeline** (texto-a-texto, sin tools).

El motivo de fondo de estos fallos está en el apéndice D: los modelos están entrenados con formatos de function calling distintos, y solo aquellos entrenados específicamente para el formato OpenAI estructurado funcionan limpiamente en una API OpenAI-compatible.

**Validación end-to-end** sobre `https://github.com/dan-divy/spruce` con `--provider groq`. Resultados observados:

- **Primer run con Qwen3-32B (agente) + Llama 3.3 70B (pipeline):** 10/11 entidades + `key_invokes` (sobre-normalización menor).
- **Segundo run mismo input mismo modelos:** 6/11 — Qwen decidió que analytics y keys eran "secundarios" y los saltó. **Varianza alta del agente entre runs sobre el mismo input.**
- **Run con Llama 4 Scout + prompt v3 compacto** (`out-spruce-llama4-v3/`): 7/11 + 2 extras legítimas (post_likes, post_comments). Llama 4 recupera POSTS por primera vez (cruza user.js con routes/), pero pierde keys/analytics aunque están en el mismo directorio que user.js.

Conclusión empírica: los modelos en el free tier de Groq tienen distintas "personalidades exploratorias" — Qwen tiende a leer más schemas pero ignora rutas; Llama 4 lee pocos archivos pero cruza schemas con código de aplicación. Ninguno alcanza el 11/11 de Gemini 2.5 Flash Lite en Google. Más profundo en el apéndice F.

### Ollama local — opción nuclear

Con GPU decente (8GB+ VRAM idealmente), **ningún rate-limit, ningún coste, sin internet**. API HTTP local. Modelos con tool-use: `llama3.1`, `llama3.3`, `qwen2.5`, `mistral-nemo`.

Trade-off: latencia >> nube si no hay GPU buena. Calidad del 8B menor que la del 70B en Groq.

Atractivo para la defensa porque elimina la dependencia externa, pero solo si el equipo lo soporta.

### Mistral "La Plateforme" — backup honorable

Free tier con `mistral-small-latest` y `open-mistral-nemo`, ambos con function-calling. Más generoso que Google pero menos que Groq. SDK propio (`mistralai`), no OpenAI-compatible — más curro implementar.

### Recomendación

**Implementar `GroqProvider` ya.** Razones:

1. Resuelve el problema de cuota inmediato.
2. Cierra el cuasirequisito de "multi-proveedor" del TFG en el mismo movimiento.
3. La API OpenAI-compatible se podrá reusar para añadir OpenAI/OpenRouter/Anthropic con esfuerzo aún menor.
4. Los modelos Llama 3.3 70B son competitivos para esta tarea.

---

## D. Los formatos de function calling y por qué seguimos el de OpenAI

### Por qué hay varios formatos

"Function calling" **no es un estándar único**. Apareció en mitad de 2023 cuando OpenAI lo lanzó en su API. Cada proveedor que vino después (Anthropic, Google) implementó su propia versión, parecida pero no idéntica. Y por el otro lado, los LLMs en sí están entrenados para emitir function calls en uno u otro formato según sus datos de entrenamiento.

Hay **dos planos** que confunden si no los separas:

1. **El formato de la API del proveedor** (cómo declaras tools en la petición HTTP y cómo vienen los results en la respuesta).
2. **El formato que el modelo emite internamente** (cómo está entrenado para "decir quiero llamar X").

Lo normal es que el servidor del proveedor traduzca entre los dos. Lo anormal — el caso de Llama-en-Groq — es cuando el modelo emite un formato y la API espera otro y la traducción falla.

### Los cuatro formatos que están en circulación

**1. OpenAI (el de facto)** — lanzado mid-2023. La mayoría de proveedores ofrecen "OpenAI-compatible APIs" que lo replican exacto.

```json
// Petición: tools
[{"type": "function", "function": {"name": "list_dir", "description": "...", "parameters": {...JSON Schema...}}}]

// Respuesta: assistant message
{"role": "assistant", "content": null,
 "tool_calls": [{"id": "call_abc123", "type": "function",
                 "function": {"name": "list_dir", "arguments": "{\"path\":\"models/\"}"}}]}

// Resultado de tool de vuelta
{"role": "tool", "tool_call_id": "call_abc123", "content": "..."}
```

Cada call tiene **id único**, los results se emparejan por id, los `arguments` van como **string JSON** (no objeto), las tools son una lista plana.

Lo usan: OpenAI, Groq, Together AI, Fireworks, Mistral, DeepSeek, OpenRouter, vLLM, llama.cpp servidor… prácticamente todos los providers comerciales y self-hosted.

**2. Anthropic (Claude)** — más nuevo (finales 2023). Estructura distinta pero conceptualmente parecida.

```json
// Petición
{"tools": [{"name": "list_dir", "description": "...", "input_schema": {...}}]}

// Respuesta: content como array de blocks
{"content": [
  {"type": "text", "text": "Voy a explorar..."},
  {"type": "tool_use", "id": "toolu_xxx", "name": "list_dir", "input": {"path": "models/"}}
]}

// Resultado de vuelta
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_xxx", "content": "..."}]}
```

Diferencias clave: el `content` es **array de blocks**, no string. Los results van con rol `user` (no `tool`). Los arguments ya vienen como **objeto JSON** (no string). Empareja por id.

**3. Google Gemini** — otra variante. Lo más distintivo: **no usa IDs, empareja por nombre de función**.

```python
# Petición
tools=[Tool(function_declarations=[FunctionDeclaration(name="list_dir", ...)])]

# Respuesta: parts dentro del content
candidate.content.parts = [Part(function_call=FunctionCall(name="list_dir", args={"path": "models/"}))]

# Resultado de vuelta
Content(role="user", parts=[Part.from_function_response(name="list_dir", response={"result": "..."})])
```

Estructura de **parts** dentro de un content, role del result es **`user`** (no `tool`), no hay IDs, el matching se hace por **nombre de función**. Esto último es una limitación real: si el modelo llama a la misma tool dos veces en un turno, no puedes asociar limpiamente cada result a su call.

**4. Markup/texto (el que rompe Llama-en-Groq)** — algunos modelos están entrenados para emitir function calls como **texto literal con marcadores**, no como campo estructurado. Meta entrenó Llama 3.1+ con un formato propio:

```
<|python_tag|>list_dir.call(path="models/")<|eom_id|>
```

O Llama 3.2/3.3 con variantes:

```
<function=list_dir>{"path": "models/"}</function>
```

El modelo emite eso como **texto plano dentro de `content`**. Funciona bien si el cliente sabe parsearlo (servidores Llama-specific), pero **falla cuando lo metes detrás de una API OpenAI-compatible** porque el modelo emite markup y la API espera el slot estructurado `tool_calls`. Eso es exactamente lo que pasa con los Llama en Groq.

### ¿Qué formato usamos nosotros?

**Internamente seguimos la forma de OpenAI**, traducida a dataclasses neutras en `providers/base.py`:

```python
@dataclass
class ToolSpec:                    # ↔ OpenAI's "function" block
    name: str
    description: str
    parameters: dict[str, Any]     # JSON Schema, igual que OpenAI

@dataclass
class ToolCall:                    # ↔ OpenAI's "tool_calls[]" entry
    id: str                        # call_id único
    name: str
    arguments: dict[str, Any]      # ya deserializado a dict (OpenAI lo da string)

@dataclass
class Message:                     # ↔ OpenAI's "messages[]" entry
    role: Role                     # "system" / "user" / "assistant" / "tool"
    content: str | None
    tool_calls: list[ToolCall]     # solo si role=assistant
    tool_call_id: str | None       # solo si role=tool (id para OpenAI/Groq)
    tool_name: str | None          # solo si role=tool (nombre para Gemini)
    raw: Any                       # objeto crudo del SDK por si hay que reusarlo
```

Y cada provider traduce a/desde su formato nativo:

- `GoogleProvider._to_gemini_tools` / `_to_gemini_contents` → traducen al formato Gemini (parts, function_call, role=`user` con function_response, matching por nombre).
- `GroqProvider._to_groq_tools` / `_to_groq_messages` → pasan al formato OpenAI casi 1:1 (es justo lo que Groq espera).

Por eso `GroqProvider` es más corto que `GoogleProvider`: el formato interno es casi idéntico al de Groq.

### ¿Por qué OpenAI y no otro?

Tres razones, en orden de peso:

1. **Es el de facto estándar.** Si tu abstracción interna se parece a OpenAI, integrar un proveedor nuevo es trivial cuando ese proveedor ofrece "OpenAI-compatible API" (que es casi todos los que no son OpenAI/Anthropic/Google). Se vio claro en Groq: 100 líneas y va.
2. **El matching por id es estrictamente más expresivo que el matching por nombre.** Permite que el modelo llame a la misma tool varias veces en un turno y emparejar cada result a su call. Gemini no puede.
3. **JSON Schema para parámetros** es el formato que toda la industria adoptó. No hay alternativa real.

**¿Es el más usado?** Sí, sin duda. La frase "OpenAI-compatible API" es marketing precisamente porque ese formato se convirtió en el estándar al que todo el mundo apunta. Anthropic y Google tienen sus propios formatos pero la mayoría de SDKs de terceros (LangChain, LlamaIndex…) abstraen primero al formato OpenAI y traducen desde ahí.

### Implicación práctica al elegir un modelo

Cuando elijas un modelo para el agente, dos preguntas:

1. **¿El proveedor expone una API que respeta el formato OpenAI?** Casi todos sí.
2. **¿Está el modelo entrenado para emitir function calls en ese formato (estructurado) o en markup?** Esto es lo difícil de averiguar a priori — solo se ve probando.

Heurística rápida:

- **Modelos de OpenAI, Anthropic, Google nativos** → entrenados específicamente para sus APIs, funcionan bien con sus propios formatos.
- **OpenAI `gpt-oss-*`** → open-source de OpenAI, *en principio* entrenados para el formato estructurado, *en la práctica* dan problemas en Groq (CoT no separable, JSON truncado).
- **Qwen 2.5+ / Qwen3** → Alibaba entrenó tool-use compatible con OpenAI. Funciona consistentemente.
- **Mistral** → idem, compatible con OpenAI.
- **Llama 3.1+** → markup nativo, **roto contra OpenAI-compat APIs** salvo que el servidor traduzca (algunos lo hacen, Groq no).

---

## E. Sobre Groq como proveedor (contexto para defender la elección)

### Quiénes son

Startup estadounidense fundada en 2016 por **Jonathan Ross**, uno de los ingenieros originales del TPU de Google. Sede en Mountain View. Hardware especializado primero, servicio cloud después. Han levantado bastante capital (varios cientos de millones, valoración ~2-3B USD a 2024).

### Su tesis técnica

GPUs (NVIDIA) son **chips de propósito general** optimizados para entrenamiento de modelos: muchísima paralelización masiva, mucha memoria. Buenos para "muchas operaciones a la vez". Pero la **inferencia** (correr un modelo ya entrenado para generar texto) tiene un patrón de cómputo distinto: es esencialmente **secuencial** — cada token depende del anterior. Las GPUs lo hacen, pero infrautilizando recursos.

Groq diseñó un chip propio llamado **LPU (Language Processing Unit)** específicamente para inferencia de modelos de lenguaje. Arquitectura determinista, sin caché, pipeline optimizado para generación token-a-token. El resultado es **velocidad**: a igualdad de modelo, Groq genera 5-10× más tokens/seg que la misma inferencia en GPU.

Para que te hagas una idea: Llama 3.3 70B en Groq da ~250-500 tokens/seg sostenidos. En OpenAI o Anthropic estás en el rango 30-80 tokens/seg. Esta velocidad es su diferenciador y el motivo por el que la gente los conoce.

### Lo que sí hacen y lo que no

**No entrenan modelos propios.** No hay un "modelo Groq" como hay un "GPT" o un "Claude". Toman modelos open-weight (publicados gratis por sus creadores) y los corren en su hardware. Los principales:

- **Llama** (Meta) — familia 3.1, 3.3.
- **Mistral** y **Mixtral** — modelos europeos open-weight.
- **Qwen** (Alibaba) — modelos chinos.
- **gpt-oss** (OpenAI open-source) — open-weight de OpenAI.

Cuando llamas a la API de Groq pidiendo `qwen/qwen3-32b`, estás hablando con el **modelo de Alibaba**, hospedado en hardware de Groq. El modelo lo podrías correr en local con Ollama si tuvieras la GPU; Groq solo te da la velocidad y la disponibilidad.

### Modelo de negocio y free tier

Cobran por token vía API (precios más baratos que OpenAI/Anthropic) y venden hardware/clusters a empresas. Su free tier es **deliberadamente generoso** por dos razones:

1. **Captar developers.** La velocidad vende sola en cuanto la pruebas.
2. **Su coste marginal es bajo.** Como el hardware es más eficiente, regalar inferencia les sale más barato.

Cuota free típica: 30 RPM y ~14k req/día en `llama-3.3-70b-versatile`. Comparado con los 20 RPD de Google es otra liga.

### Por qué encaja con el TFG (más allá de la cuota)

- **Es la "cara amable" de los modelos open-source.** Para la memoria: "el prototipo no depende de un proveedor cerrado; usamos modelos open-weight (Qwen3-32B de Alibaba, Llama 3.3 de Meta) corridos en infraestructura comercial (Groq) que es intercambiable con correrlos en local (Ollama)".
- **API OpenAI-compatible** = el estándar de facto en la industria. Añadir Anthropic u OpenAI luego es trivial sobre el mismo patrón.
- **Demuestra RU-7** (independencia de proveedor) con dos providers de naturaleza muy distinta: Google (modelos propietarios) vs Groq (modelos abiertos). Argumento defensivo bueno.

### Trampa de nombres

**Groq** (con **q**) — la empresa de inferencia, fundada 2016 por Jonathan Ross (ex-Google TPU).
**Grok** (con **k**) — el chatbot de xAI (la empresa de Elon Musk), lanzado 2023.

Son **dos cosas distintas y sin relación**. Groq es anterior; han demandado a xAI varias veces por la confusión. Importante pronunciarlo/escribirlo bien en la defensa.

---

## F. Diseño del system prompt del agente y por qué el modelo es el cuello de botella

El system prompt del agente (`normalizer/prompts/discovery_system.md`) ha pasado por dos iteraciones tras los runs iniciales. Esta sección resume las decisiones de diseño y la lección de fondo.

### Versión inicial — y por qué fallaba

La versión original era larga (~75 líneas) e incluía instrucciones como:

> Sé selectivo: el objetivo no es seleccionar muchos archivos sino los imprescindibles para entender el modelo. **Mejor 6 archivos clave que 15 redundantes.**

> Si descartas algo ruidoso a propósito, está bien — **no necesitas justificarlo**, solo no lo selecciones.

Estas frases sesgaban al agente hacia parar pronto. Modelos buenos las calibraban bien (Gemini lograba 11/11); modelos más débiles las sobreinterpretaban y producían cobertura muy variable. Caso concreto: en un run de Qwen3-32B sobre Spruce, el resumen del agente justificaba haber omitido analytics y keys con "no son críticos para la estructura principal" — Qwen tomó nuestra licencia de "descarta sin justificar" y la combinó con un juicio erróneo sobre qué era relevante.

### Versión actual — tres principios de fondo

La revisión (`prompts/discovery_system.md` ~38 líneas) invierte el sesgo y añade reglas explícitas:

1. **Cobertura sobre parsimonia.** "Mejor sobre-incluir que perder una entidad" reemplaza "mejor 6 que 15". Justificación de fondo: el pipeline siguiente puede ignorar evidencia redundante sin coste, pero **no puede inventar entidades que no le pases**. La asimetría de coste justifica el sesgo a sobre-incluir.

2. **Prohibido descartar sin inspeccionar.** "No puedes calificar un archivo o subdirectorio como 'secundario' sin haber abierto su contenido". Convierte una decisión opcional en una obligación: o lees, o no descartas.

3. **Vecindad estructural.** "Si encuentras un schema en `X/Y/foo`, debes inspeccionar los hermanos del mismo `X/Y/` antes de cerrar". Esto **es project-agnostic**: no menciona `models/` ni `routes/` ni ningún path concreto, solo el patrón "los schemas viven juntos". Vale para cualquier layout (Java packages, Go modules, Python `app/db/`, etc.).

Además: suelo cuantitativo (≥2 subdirs listados, ≥4 archivos inspeccionados antes de `done`) y obligación de justificar en el `summary` cada subdirectorio top-level no explorado.

### Por qué NO se baja a paths concretos

Sería tentador añadir "si ves un directorio llamado `models/` o `schemas/`, léelo entero". **No se hace** porque la herramienta tiene que valer para cualquier repo con BD documental, no solo para los que sigan el layout de Spruce. Un repo Java pondría las entidades en `com/foo/entity/`, un proyecto Go en `internal/db/models/`, un Flask app en `app/models.py`. Atar el prompt a nombres concretos lo rompe en cualquier proyecto que no siga la convención asumida.

La heurística "vecindad estructural" es la versión generalizable del mismo principio: **agrupar por proximidad estructural, no por nombre**. Funciona porque "los schemas viven cerca" es invariante del layout.

### La lección de fondo: prompt necesario, no suficiente

Con el prompt nuevo, Llama 4 Scout sobre Spruce subió de 6/11 a 7/11 entre runs distintos — mejora real pero modesta. **Llama 4 ignora la regla de vecindad estructural**: lee `user.js` (en `utils/models/`) y no toca `room.js`/`keys.js`/`analytics.js` aunque son hermanos directos. La regla está, el modelo no la honra.

Esto es la lección defendible:

> **La capacidad del modelo para razonar y seguir instrucciones complejas pone un techo a lo que el prompt puede lograr.**

El prompt es **necesario** (sin él, modelos débiles paran mucho más pronto) pero **no suficiente** (modelos débiles ignoran reglas explícitas). El gradiente observado en Spruce con el prompt nuevo:

| Modelo del agente | Cobertura típica |
|---|---|
| Gemini 2.5 Flash Lite (Google) | 11/11 |
| Qwen3-32B (Groq free) | 6-10 (alta varianza) |
| Llama 4 Scout (Groq free) | 6-7 (varianza moderada) |
| Llama 3.x | no funciona (formato markup) |

Esto se conecta con la separación pipeline / agente: el pipeline es tarea estructurada y tolera modelos mid-tier; el agente es razonamiento abierto y exige un modelo de gama alta. Es el cuello de botella real del flujo URL → DDL.

### Palancas para subir el techo

Por orden de coste:

1. **Refinar el prompt** (ya hecho). Coste cero, mejora modesta sobre modelos débiles.
2. **Subir de modelo en el mismo proveedor.** En Groq significa tier dev (Qwen sin TPM cap). En Google significa Gemini 2.5 Flash o Pro. Coste: dinero o más cuota.
3. **Añadir un proveedor con un modelo más capable.** Claude Haiku 4.5, GPT-4o-mini. Coste: implementación de un Provider más + tarjeta de crédito.
4. **Múltiples runs + agregación.** Correr el agente 3 veces y unir las evidencias seleccionadas. Más caro en cuota pero reduce varianza efectiva sin tocar nada del código. Útil si la limitación es varianza, no techo absoluto.

### Implicación para defender el TFG

Esto es un ejemplo concreto de los **límites del approach agéntico**: la calidad de la salida no depende solo del software bien diseñado, depende del modelo que lo ejecuta. La arquitectura es robusta (la abstracción `LLMProvider` permite intercambiar libremente), pero la **cobertura efectiva** sobre un repo nuevo va a fluctuar con el modelo elegido. Hacer esto explícito en la memoria — con la tabla de cobertura por modelo y la lección "el modelo es el cuello de botella" — distingue un TFG técnico riguroso de uno que vende la herramienta como caja negra que "siempre funciona".
