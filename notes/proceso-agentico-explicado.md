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

### Groq — top pick

Free tier muy generoso (orden de magnitud ~14k peticiones/día en `llama-3.3-70b-versatile`), latencia muy baja, API **compatible con OpenAI**, modelos con function-calling sólido. Encaja porque:

- Cuota cómoda para iterar.
- Implementar `GroqProvider` se reduce a copiar `GoogleProvider` y cambiar el cliente.
- Sin tarjeta, basta cuenta gratis.
- **Y de paso tacha el cuasirequisito de "segundo proveedor" para la siguiente reunión** — dos pájaros de un tiro.

Modelos con tool-use: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`.

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
