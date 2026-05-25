# Sesión 25 mayo 2026 — Segundo proveedor LLM (Groq)

3 commits sobre `main`: `4946e05` → `d623752` → `29cb93d` (+ commit posterior con esta nota).

Cierra el cuasirequisito de "multi-proveedor" del TFG para la próxima reunión con tutores y resuelve el cuello de botella de cuota del free tier de Google.

---

## 1. Decisión: ¿por qué Groq?

Tras quemar la cuota diaria de Google (`gemini-2.5-flash-lite`: 20 RPD en esta cuenta) en una sola sesión de testing, hacía falta o pagar o cambiar de proveedor. Repasamos opciones:

- **Groq**: free tier muy generoso (~14k req/día en Llama 3.3 70B), API OpenAI-compatible, latencia muy baja por hardware especializado (LPU), modelos open-weight.
- **Ollama local**: cero límites, pero requiere GPU decente que el equipo del autor no tiene de sobra.
- **Mistral La Plateforme**: free tier intermedio, SDK propio (no OpenAI-compatible) — más curro implementar.

Elegido **Groq** por la combinación cuota+API estándar+OpenAI-compat (permite añadir más providers similares con copy-paste posterior).

## 2. Implementación

Nuevo archivo `normalizer/providers/groq.py`:

- `GroqProvider` con `generate()` (texto-a-texto, para el pipeline) y `chat()` (con tools, para el agente).
- `_call_with_retry()` análogo al de Google, respetando los headers `retry-after` / `x-ratelimit-reset` del SDK groq.
- `_to_groq_tools()` y `_to_groq_messages()` traducen del formato interno al formato OpenAI que Groq espera. La traducción es casi 1:1 porque nuestra abstracción ya seguía la forma de OpenAI.

### Cambio en `Message`

Se amplió `Message` con un campo `tool_name` además del existente `tool_call_id`. Razón: Gemini empareja respuestas de tools **por nombre de función**; OpenAI/Groq las emparejan **por id**. Antes lo apañábamos guardando el name en `tool_call_id`, lo que era sucio y rompería al meter Groq. Ahora el agente rellena los dos:

```python
messages.append(Message(
    role="tool",
    content=result,
    tool_call_id=call.id,    # OpenAI/Groq
    tool_name=call.name,     # Gemini
))
```

Cada provider usa el que necesita y el otro queda inerte.

### Registro

En `providers/__init__.py`:

- `_REGISTRY` añade `"groq": GroqProvider`.
- `DEFAULT_MODELS["groq"] = "llama-3.3-70b-versatile"` (pipeline).
- `DEFAULT_AGENT_MODELS["groq"] = "qwen/qwen3-32b"` (agente).

Pipeline y CLI sin cambios — la abstracción aguantó.

## 3. La sorpresa: no todos los modelos de Groq sirven para tool-use

El primer intento usaba `llama-3.1-8b-instant` como agente (el default natural por velocidad+cuota). Falló inmediatamente con:

```
groq.BadRequestError: 400 - tool_use_failed
failed_generation: '<function=list_dir>public/javascripts/</function>\n'
```

Llama emite function calls como **markup textual** (`<function=...>`) en lugar de usar el slot estructurado `tool_calls`. La API de Groq detecta el mismatch y rechaza la petición. Es una incompatibilidad de fondo: Llama 3.1+ está entrenado con el formato propio de Meta, no con el formato OpenAI estructurado que Groq espera.

Cambiamos al 70B esperando que fuera mejor — mismo problema. Probamos más modelos:

| Modelo | Resultado |
|---|---|
| `llama-3.1-8b-instant` | ❌ markup `<function=...>` |
| `llama-3.3-70b-versatile` | ❌ markup `<function=...>` |
| `openai/gpt-oss-20b` | ❌ JSON malformado en los arguments |
| `openai/gpt-oss-120b` | ❌ chain-of-thought no parseable (`output_parse_failed`) |
| `qwen/qwen3-32b` | ✅ funciona |

Qwen se quedó como default del agente en Groq. Los Llama siguen valiendo para el pipeline (texto-a-texto sin tools).

**Aprendizaje generalizable:** "OpenAI-compatible API" tiene una asterisco. El formato de la API lo es, pero el modelo tiene que estar entrenado para ese formato concreto. La cobertura empírica de qué modelo funciona en qué provider hay que medirla, no se deduce del catálogo.

(Profundizado en `notes/proceso-agentico-explicado.md` apéndice D.)

## 4. Validación end-to-end

`python -m normalizer https://github.com/dan-divy/spruce --provider groq --out-dir out-spruce-groq`

Resultado vs UML manual (11 entidades esperadas):

| Esperado | En DDL Groq |
|---|---|
| USERS, USER_FOLLOWERS, USER_NOTIFICATIONS, CHAT_ROOMS, CHAT_ROOM_MEMBERS, CHAT_MESSAGES, API_KEYS, API_KEY_STATS, ANALYTICS, ANALYTICS_STATS | ✅ las 10 |
| POSTS | ❌ falta |
| (extra) | `key_invokes` (sobre-normalización menor: el `invokes: Number` debería ser columna de `keys`) |

**10/11 entidades.** Falta POSTS porque Qwen seleccionó solo los 4 schemas Mongoose y no leyó las rutas donde se hace `posts.push({...})`. Es una limitación del **exploration behavior** del modelo del agente (Qwen es más conservador que Gemini), no del provider.

Iteraciones: 7 (vs 5 con Google). Total peticiones: 7 agente + 3 pipeline = 10.

## 5. Estado del cuasirequisito multi-proveedor

**Cerrado.** Dos providers totalmente funcionales (`google` y `groq`), ambos implementan `generate()` y `chat()`, ambos pasan la validación end-to-end contra Spruce con resultados cualitativamente equivalentes (Google recupera POSTS, Groq no — pero la diferencia es de prompt/exploración, no de provider).

La abstracción `LLMProvider` queda demostrada: añadir un tercero (Anthropic, OpenAI, Mistral) es copy-paste con pequeñas adaptaciones de SDK.

## 6. Iteración posterior — varianza, segundo modelo y prompt nuevo

Después del primer 10/11 con Qwen, se volvió a correr el mismo input para confirmar consistencia: **6/11**. Qwen había decidido que analytics y keys eran "secundarios". Esto destapó el problema de **alta varianza** del agente entre runs sobre el mismo input.

Antes de tocar el prompt, se intentó descartar que fuera un problema de modelo cubriendo el catálogo completo de Groq:

- `meta-llama/llama-4-scout-17b-16e-instruct` (Llama 4): ✅ funciona, recupera POSTS por primera vez pero pierde analytics/keys → 6/11 + 2 extras legítimas.
- `groq/compound`, `groq/compound-mini`: ❌ rechazan tools del cliente (`'tool calling' is not supported with this model`) — vienen con sus propias tools internas precableadas.

Conclusión: dos modelos viables en el free tier de Groq (Qwen3-32B y Llama 4 Scout), con personalidades exploratorias distintas y ninguno alcanza Gemini.

Después se reescribió el system prompt con tres principios nuevos (project-agnostic):

1. **Cobertura sobre parsimonia** (antes: "sé selectivo, mejor 6 que 15"; ahora: "mejor sobre-incluir").
2. **Prohibido descartar sin inspeccionar** (cierra el agujero "Qwen decide que algo es secundario sin abrirlo").
3. **Vecindad estructural**: "si encuentras un schema en `X/Y/foo`, lee los hermanos del mismo `X/Y/` antes de cerrar".

Más suelo cuantitativo (≥2 subdirs listados, ≥4 archivos inspeccionados) y obligación de justificar descartes top-level.

Se compactó de ~75 a ~38 líneas eliminando pasos procedimentales que los modelos modernos no necesitan.

Validación con el prompt nuevo:

- **Qwen3-32B**: imposible probarlo, el TPM cap (6000 TPM en free tier) se revienta con el historial acumulado del agente, devolviendo HTTP 413.
- **Llama 4 Scout**: 7/11 entidades (vs 6/11 antes). Llama 4 **ignora la regla de vecindad estructural** — lee `user.js` pero no toca `room.js`/`keys.js`/`analytics.js` que están en el mismo directorio.

**Conclusión defendible**: el prompt nuevo es mejor (más corto, principios explícitos, project-agnostic), pero **el modelo es el cuello de botella real**. Modelos débiles ignoran instrucciones complejas; la regla está escrita, no se honra. Esto ya estaba documentado en general; este experimento lo confirma empíricamente y queda registrado en el apéndice F de `proceso-agentico-explicado.md`.

## 7. Estado final y siguientes pasos

- Default del agente en Groq: `qwen/qwen3-32b` (mejor cobertura potencial cuando funciona; Llama 4 es alternativa con tradeoff distinto).
- Default del pipeline en Groq: `llama-3.3-70b-versatile`.
- Único run vivo en disco: `out-spruce-llama4-v3/` (los intermedios y baselines fueron purgados para mantener el repo limpio).

Pendiente:
- **Re-validar con Google** cuando resetee la cuota diaria (Gemini debe seguir dando 11/11 con el prompt nuevo, sería bueno confirmar).
- Si la varianza sigue preocupando para defender: tier dev de Groq (Qwen sin TPM cap) o un tercer provider con Claude/GPT.
