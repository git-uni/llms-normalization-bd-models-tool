# Sesión 25 mayo 2026 — Colapso del free tier de Google, prueba con Llama 4 Scout y catálogo de alternativas

Sin commits. Sesión exploratoria a partir de la hipótesis "algo no está bien en el proceso del agente" tras un mal run con Llama 4 Scout. Cierra con la conclusión opuesta: **el proceso del agente funciona; el cuello es la combinación capacidad-del-modelo + cuota-del-free-tier**.

---

## 1. Hipótesis de partida y prueba con Llama 4 Scout

Tras el run anterior `out-spruce-llama4-v3/` (7/11 entidades, ya en CLAUDE.md punto 17), se relanzó el mismo modelo con el prompt nuevo sobre la URL de Spruce → `out-spruce-llama4-test/`.

Resultado **peor** que v3:

- **8 iteraciones**, **2 archivos seleccionados**: `config/app.js` y `utils/models/user.js`.
- El propio `summary` del agente identifica `analytics.js`, `keys.js`, `room.js` como "potencialmente relevantes" y aun así no los abre — viola frontalmente la regla de **vecindad estructural** del prompt nuevo (todos viven en `utils/models/` junto a `user.js`).
- DDL final: 6 tablas pero solo 4 con atributos reales. Faltan CHAT_MESSAGES, API_KEYS, API_KEY_STATS, ANALYTICS, ANALYTICS_STATS.

Esto sugería dos lecturas posibles:
- (a) **Hipótesis del usuario**: hay algo mal en el bucle del agente, las tools o el prompt.
- (b) **Hipótesis alternativa**: Llama 4 Scout es inestable y Spruce lo expone.

Para discriminar, hacía falta un run con un modelo confiable (Gemini).

## 2. Intentos con Google y el colapso del free tier

Tres runs, los tres fallidos por 429:

| Modelo | Resultado |
|---|---|
| `gemini-2.5-flash-lite` (default) | Cuota diaria ya agotada de la sesión anterior. |
| `gemini-2.5-flash` | Falló a mitad de descubrimiento (~iter 20+): `limit: 20` para `generate_content_free_tier_requests`. Antes de petar había cubierto los 4 schemas de `utils/models/` — cumplía la vecindad. |
| `gemini-2.0-flash` | Falló en la **primera llamada** con `limit: 0`. Modelo retirado del free tier en esta cuenta. |

`out-spruce-gemini25flash/` quedó con 5 archivos en evidence (los 4 schemas + `database_tests.js`) pero sin `discovery.md` ni pipeline ejecutado — la excepción aborta antes.

### Investigación de fuentes oficiales

Búsqueda dirigida en `ai.google.dev`, `discuss.ai.google.dev` y `cloud.google.com`. Hallazgos confirmados:

- **Diciembre 2025**: Google recortó el free tier "para liberar compute para Gemini 3 Pro" sin aviso previo (post oficial de Logan Kilpatrick en el foro). Texto models bajaron a **10-20 RPD**, antes 250+.
- **Mayo 2026**: la página oficial `ai.google.dev/gemini-api/docs/rate-limits` ya **no publica la tabla de límites**, redirige al dashboard de AI Studio (gated).
- **2.0-flash**: `limit: 0` significa sin acceso free tier — no es un agotamiento por uso, es retirada.
- **Familia 3.x**: paid tier focus, no figura en free tier público.

**Consecuencia operativa**: Google es inviable como free tier para nuestros runs de prueba. Una sola corrida del agente con el prompt nuevo (≥10-20 iter) iguala o supera el RPD diario del único modelo aún accesible (`gemini-2.5-flash`).

### Bomba de relojería en el diseño

`MAX_ITERS = 20` en `discovery/agent.py` coincide casi exactamente con `RPD = 20` del free tier actual de Google. Aunque el modelo funcione perfecto, una sola corrida puede comerse la cuota diaria. **Esto es una observación de diseño, no un bug**: el agente no debería ser consciente del tier comercial. Pero documenta que el free tier de Google está dimensionado para "1 corrida/día".

## 3. Catálogo de proveedores alternativos (free tier)

Investigación en docs oficiales:

### Groq (ya implementado)

Free tier por modelo:

| Modelo | RPM | RPD | TPM | TPD |
|---|---|---|---|---|
| `qwen/qwen3-32b` | 60 | 1.000 | **6K** | 500K |
| `meta-llama/llama-4-scout-...` | 30 | 1.000 | **30K** | 500K |
| `llama-3.3-70b-versatile` | 30 | 1.000 | 12K | 100K |

El cap real es **TPM**, no RPD. Qwen 6K es lo que mata las iteraciones largas (confirma CLAUDE.md punto 18). Llama 4 tiene **5× más margen TPM** pero menor calidad.

### Cerebras (candidato no explorado)

Free tier: **5 RPM / 30K TPM / 1M TPH / 1M TPD por modelo**.

Modelos free confirmados:
- `gpt-oss-120b` (tool-use confirmado en docs)
- `qwen-3-235b-a22b-instruct-2507` ← **hermano mayor 7× del que usamos en Groq**
- `llama3.1-8b`
- `zai-glm-4.7` (tool-use confirmado en docs)

5 RPM exige ≥12 s entre llamadas → ~4 min para un run de 20 iter. Aceptable. API OpenAI-compatible → adaptar `groq.py` cambiando endpoint y key es casi un copy-paste.

Incertidumbres antes de cablearlo:
1. Cerebras no documenta explícitamente que `qwen-3-235b` soporte tools (sí `gpt-oss-120b` y `zai-glm-4.7`). Verificar antes vía `llms.txt` o prueba directa.
2. 5 RPM exigirá probablemente un `time.sleep(12)` defensivo en el bucle o un retry agresivo.

### OpenRouter (multiplicador)

- Sin créditos: **50 free-model req/día**, 20 RPM.
- Con $10 de crédito: 1000/día.
- Tool-calling soportado para varios free (gpt-oss-120b/20b, Laguna M.1, CoBuddy, etc.).

Valor: acceso unificado a muchos modelos free con una integración. 50 RPD aguanta ~2 corridas/día.

### GitHub Models y Mistral (descartados de momento)

- **GitHub Models**: free/pro 10-15 RPM, RPD caps no publicados, function-calling per-model **no documentado en la página principal** — habría que ir uno a uno.
- **Mistral**: free tier existe, números detrás del login. Function-calling solo en Small/Large. Más fricción que Cerebras.

## 4. Reintento Groq + Qwen y abandono

Para validar la sospecha de que Qwen TPM=6K es el cuello en runs largos con prompt nuevo, se lanzó `out-spruce-qwen-retry/` con `qwen/qwen3-32b`. Tras varios minutos sin progreso visible (`evidence/` vacío, log solo con "Descubriendo…"), se abortó manualmente.

Diagnóstico **probable** (no probado): el `_call_with_retry` del `GroqProvider` está respetando el `retry-after` de 429s tras chocar con el cap TPM, durmiendo silenciosamente. Para confirmar haría falta logging dentro del provider — no se ha tocado en esta sesión.

## 5. Conclusiones para defender

1. **El proceso del agente NO es el problema.** Gemini 2.5 Flash, antes de petar por cuota, había cubierto los 4 schemas de `utils/models/` cumpliendo la regla de vecindad estructural. El prompt y el bucle hacen lo que tienen que hacer cuando el modelo es capaz.

2. **El cuello tiene dos caras independientes:**
   - **Capacidad del modelo**: Llama 4 Scout en este run cogió 2 archivos donde Gemini iba a por todos los hermanos. Mismo prompt, mismo input, modelos distintos → resultados radicalmente distintos. Refuerza CLAUDE.md punto 17.
   - **Cuota del free tier**: Google está prácticamente cerrado; Groq+Qwen tiene TPM tan estrecho que el agente con prompt nuevo se rate-limitea silenciosamente.

3. **Camino realista a corto plazo**: añadir Cerebras como tercer provider y probar con `qwen-3-235b`. Es la única vía free hoy que combina (a) modelo más capable que Qwen 32B, (b) cuota razonable (1M TPD), (c) integración trivial (OpenAI-compatible).

4. **Camino realista si se acepta gasto**: habilitar billing en Google ($10 crédito) o pasar a tier dev de Groq desbloquea el TPM cap de Qwen. Ninguna requiere tocar código.

## 6. Estado del repo al cerrar

- **Runs en disco**: `out-facil/`, `out-difuso/`, `out-spruce-llama4-v3/` (referencia previa), más los de esta sesión `out-spruce-llama4-test/`, `out-spruce-gemini25flash/`, `out-spruce-gemini20flash/`, `out-spruce-google-test/`, `out-spruce-qwen-retry/`. Los nuevos tienen resultados parciales o nulos; conviene purgar los que no se vayan a referenciar.
- **Sin cambios en el código.** Solo investigación.

---

## Pendiente

- **Cablear CerebrasProvider** copiando `groq.py` y probando con `qwen-3-235b-a22b-instruct-2507`.
- **Re-validar Gemini 2.5 Flash mañana** con la cuota fresca para confirmar que termina los 11/11 con el prompt nuevo.
- **Considerar bajar `MAX_ITERS`** o añadir un cap blando — si el agente necesita >15 iter quizá es señal de prompt aún demasiado abierto.
