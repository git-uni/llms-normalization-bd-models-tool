# Sesión 25 mayo 2026 — Gemini 3.1 Flash Lite, prompt v4 y primer repo real (Habitica)

Tres movimientos encadenados en una sola sesión, motivados por la "bomba de relojería" del free tier de Google descrita en CLAUDE.md punto 20.

---

## 1. Descubrimiento: el free tier de Google sigue teniendo modelos útiles

El dashboard de AI Studio expone modelos `gemini-3.*` que la página pública de rate limits ya no documenta. Captura del dashboard de la cuenta del autor: `Gemini 3.1 Flash Lite` aparece con **15 RPM / 250K TPM / 500 RPD** en el tier gratis. Comparado con el 2.5 Flash Lite que estábamos usando como agente (10 RPM / 250K TPM / **20 RPD**) son 1.5× el RPM y **25× el RPD**.

Otros aparecidos en el dashboard que no figuran en docs públicas:
- `Gemini 3 Flash` (5 RPM / 250K TPM)
- `Gemini 3.5 Flash` (5 RPM / 250K TPM)
- `Gemma 4 26B` (15 RPM / TPM ilimitado, alternativa al 31B del pipeline)

Validado el ID estable (`gemini-3.1-flash-lite`, no preview) con `client.models.list()` y un test de function-calling de 1 turno con tool dummy. Responde con `ToolCall` estructurado, sin texto parásito → drop-in replacement del 2.5.

**Decisión:** cambiar `DEFAULT_AGENT_MODELS["google"]` a `gemini-3.1-flash-lite`. Cero cambios en el pipeline.

---

## 2. Validación end-to-end sobre Spruce (caso conocido)

Run con el agente nuevo + pipeline `gemma-4-31b-it` en `out-spruce-3.1/`:
- Discovery: 13 iteraciones, 4 archivos exactos (los 4 schemas de `utils/models/`). **Sin ruido tipo `test/`** (a diferencia de runs anteriores con 2.5 que metían `test/database_tests.js`).
- DDL: **11/11 entidades del UML manual** + 1 sobre-normalización legítima (`user_rooms`, junction redundante con `room_users`).

Detalle operativo: el pipeline cayó dos veces con 500/503 del servidor de Gemma (`gemma-4-31b-it`). El `_call_with_retry` solo trata 429, no 5xx. Se completó relanzando con Groq como pipeline. Patrón de inestabilidad transitoria que ya hemos visto 3-4 veces — apuntado en CLAUDE.md "Siguiente" como fix puntual independiente.

Resultado: la bomba de relojería del punto 20 queda **desactivada para Spruce**. Cerebras pasa a back-burner (ya no urge un free tier alternativo).

---

## 3. Primer repo "de verdad": Habitica

Spruce es el caso conocido del autor (curado, schemas explícitos limpios). Para validar el prototipo en un proyecto real se eligió **Habitica** (`https://github.com/HabitRPG/habitica`): app de gamificación con años en producción, backend Node + Mongoose, schemas en `website/server/models/`. Tamaño razonable — monorepo grande pero el dir de modelos está acotado.

### Run inicial (prompt v3, caps 15/20) — `out-habitica/` v3

- Discovery: 11 iteraciones, **4 archivos seleccionados** (`user/schema.js`, `task.js`, `group.js`, `challenge.js`).
- El propio summary del agente: *"Se exploraron y descartaron subdirectorios como `migrations/` y `test/` por ser código auxiliar… priorizando los archivos de modelo en `website/server/models/`."*
- DDL: 30 tablas. Bien estructuradas dentro de lo seleccionado, pero faltan entidades obvias.

Inspección del repo real revela que `website/server/models/` contiene **17 archivos JS** de modelos. El agente abrió 4 y descartó 13, entre ellos: `message.js`, `coupon.js`, `subscriptionPlan.js`, `transaction.js`, `tag.js`, `webhook.js`, `blocker.js`, `newsPost.js`, `iapPurchaseReceipt.js`, `emailUnsubscription.js`, `userHistory.js`, `userNotification.js`, `pushDevice.js`. **Todas son entidades documentales reales**, no auxiliares.

Patrón: el agente filtra por "principal vs secundario" — exactamente lo que el prompt v3 intentaba atajar con la regla 1 ("prohibido descartar sin inspeccionar") + regla 2 ("vecindad estructural"), pero el modelo lo aplica un nivel más adentro: lista el dir, "inspecciona" mirando los nombres, decide cuáles son principales, abre solo esos, descarta el resto.

### Refinamiento del prompt (v3 → v4)

Análisis previo al cambio:

- **El primer mensaje user al agente ya contiene el árbol filtrado del repo** (hasta 600 entradas, sin ruido). El prompt v3 ni lo nombraba. Brecha factual.
- **Regla "no descartar sin inspeccionar" + "vecindad estructural"** decían lo mismo desde dos ángulos. Endurecerlas en iteraciones sucesivas no había mejorado el comportamiento del modelo — empezaba a parecer rendimiento decreciente.
- **`MAX_FILES = 15` (cap de selecciones)** y **`MAX_ITERS = 20`** chocaban con la regla nueva "cubrir el dir entero" si el dir tenía >15 archivos. Habitica tiene 17.

Cambios del v4 (`prompts/discovery_system.md`, 55 → 41 líneas):

1. **Mención explícita del árbol inicial** en la sección de estrategia: *"no necesitas `list_dir` sobre la raíz"*. Atajo a 1 iter redundante por run.
2. **Fusión de las reglas 1+2 en "Principio del hermano"**, con la formulación operativa más clave: *"el filtro de 'principal vs secundario' o 'central vs auxiliar' lo hace el pipeline posterior, **no tú**"*. Invierte explícitamente la heurística mental observada.
3. **Condición de `done` reforzada**: *"si identificaste un directorio de modelos, lo has cubierto entero (todos sus archivos de código no-test/non-index)"*. Convierte la cobertura del dir en condición de cierre, no en sugerencia.
4. **Eliminada la regla 4 "no inventes rutas"** — redundante con el error que devuelve la tool al fallar la resolución.
5. **Comprimida** la enumeración de tools (ya las describe el API) y la lista de evidencia.

Cambios de código asociados (`agent.py`):
- `MAX_ITERS = 20 → 30` (espacio para las lecturas adicionales que el prompt v4 fuerza).
- `MAX_FILES = 15 → 30` (cubre Habitica sin chocar con el cap).

### Run final (prompt v4, caps 30/30) — `out-habitica/` v4

- Discovery: **14 iteraciones, 10 archivos seleccionados** (vs 4 del v3). Cubre user/{schema, index, methods, hooks} + task + group + challenge + **message, tag, webhook**. Las tres últimas son entidades nuevas que el v3 perdía.
- DDL: **33 tablas** (vs 30). Aparecen `Tag`, `Webhook`, `Chat`, `Inbox`, `SubscriptionPlan` + mejor descomposición del User (`UserAuth`, `UserStats`, `UserChallenge`, `UserGuild`, `UserTag`).
- RPM: tocado 13-14/15 en ambos runs (v3 y v4). Sin saturar, pero rozando — confirmación empírica del punto 23 de CLAUDE.md sobre el RPM como nuevo cuello en repos realistas.

**Pero el techo del modelo persiste.** El summary del agente v4 sigue diciendo *"priorizando los archivos de modelo en `website/server/models/`"*. Sigue sin recuperar `coupon.js`, `transaction.js`, `blocker.js`, `iapPurchaseReceipt.js`, `newsPost.js`, `emailUnsubscription.js`, `userHistory.js`, `userNotification.js`, `pushDevice.js`. La regla "cubre el dir entero" no se honra del todo — el modelo aplica la heurística "principal/secundario" silenciosamente incluso cuando el prompt prohíbe explícitamente esa distinción.

Mejora real: **2.5× la cobertura del dir de models/** (4/17 → 10/17) y +3 tablas en el DDL final con entidades del dominio que antes se perdían. Pero también confirmación de que el prompt es **necesario, no suficiente** — alineado con el punto 17 histórico de CLAUDE.md (Llama 4 también ignoraba la regla de vecindad estructural).

---

## 4. Aprendizajes para la memoria

1. **El free tier de Google no estaba tan colapsado como parecía** — el dashboard expone modelos `3.*` que la página pública omite. Lección de método: comprobar el dashboard, no solo la doc.

2. **Habitica es el primer repo donde se ve el techo de Gemini 3.1 Flash Lite.** Spruce era saturado en el mejor modelo (no había margen). Habitica es el primer caso donde el techo no es la arquitectura, es el modelo razonando bajo restricciones reales.

3. **El prompt tiene rendimientos decrecientes.** v1 → v3 fue una mejora grande. v3 → v4 sobre Habitica es +6 archivos (4→10), real pero no completo. v5 con más reglas probablemente daría menos. La pista de qué probar después no es "más reglas" sino **cambiar el sustrato**: enriquecer el árbol inicial con heads de archivos (idea del usuario), o hacer nudge dinámico tras cada `read_file` con la lista de hermanos pendientes.

4. **Acoplamiento prompt ↔ caps.** Endurecer la cobertura en el prompt es inútil si el cap de selecciones lo rechaza. Cualquier futura iteración del prompt debe mirar `MAX_FILES`/`MAX_ITERS` en el mismo movimiento.

5. **Gemma 4 31B tiene inestabilidad transitoria.** Tres-cuatro 500/503 ya esta semana, todas resueltas en el siguiente reintento. El `_call_with_retry` actual solo cubre 429; ampliar a 5xx es ~5 líneas.

---

## 5. Estado al cerrar la sesión

- Default del agente Google: `gemini-3.1-flash-lite`.
- `MAX_ITERS = 30`, `MAX_FILES = 30`.
- Prompt `discovery_system.md` en v4 (41 líneas).
- Punto 24 añadido a CLAUDE.md con el run comparativo.
- Cerebras pasa a back-burner.
- Próximos candidatos identificados (CLAUDE.md "Siguiente"):
  1. Manifiesto enriquecido del árbol inicial (ataque del techo de cobertura).
  2. Retry de 5xx en `GoogleProvider` (independiente).
  3. RPM cap como cuello latente en repos mayores que Habitica.

---

## 6. Addendum (misma sesión, sub-iteración) — Trace, prompt v5 y árbol incompleto

Tras cerrar el v4, dos preguntas del usuario abrieron tres mejoras encadenadas:

### 6.1 Trace turno a turno

*"¿Lanzó un read_file por cada uno consumiendo 1 petición? ¿Un select_evidence por cada uno?"* — no había forma de saberlo desde `discovery.md`, que solo registra la lista final. Cambio: `DiscoveryState.turns: list[TurnTrace]` con `iter` y `calls` (formateados compactos), renderizado al final de `discovery.md` como tabla `| Iter | Tool calls |`. Reveló inmediatamente que la afirmación de `proceso-agentico-explicado.md` de "casi siempre 1 por turno" era falsa: la varianza entre runs es enorme.

### 6.2 Prompt v5 (41 → 63 líneas)

*"El agente hizo un grep declarativo y no fue más allá — ¿no debería preguntarse qué archivos restantes podrían tener evidencia implícita?"*. Tres cambios:

- **"Checklist, no menú"** sobre la lista de cinco tipos de evidencia. En proyectos sin schemas declarados la evidencia vive en categorías 2-5; encontrar la primera no termina la búsqueda.
- **Dos pasadas obligatorias antes de `done`**: declarativa (grep de schemas) e implícita (mirar el árbol restante y preguntarse qué podría contener escrituras/accesos/seeds). La condición se refuerza en la regla 2 pidiendo confirmación explícita en el `summary`.
- **Nudge de batching**: emite varios `select_evidence` en el mismo turno cuando las decisiones son firmes. Un turno = 1 RPM.

### 6.3 Logging del árbol y descubrimiento del árbol incompleto

*"¿Puede ser que el árbol que tiene el agente sea incompleto?"*. Se loggea ahora a `out/00_discovery/tree.txt`. Inspección sobre Habitica: el árbol corta a 600 entradas con DFS alfabético, y `website/` (donde vive `server/models/` y todo el backend) **no entra en el árbol**. El agente ve 11 de 12 top-level dirs. La única razón por la que encuentra los models es que `grep` recorre el filesystem real. Esto explica por qué la "pasada implícita" del prompt v5 no se ejecuta de verdad — el agente no puede preguntarse "qué archivos restantes podrían tener evidencia" porque literalmente no los ve.

### 6.4 Cuatro runs sobre Habitica con varianza enorme

Mismo modelo (`gemini-3.1-flash-lite`), mismo repo, prompts v4 y v5:

| Run | Prompt | Iter | Archivos | Estrategia |
|---|---|---|---|---|
| A | v4 | 14 | 10 | `list_dir`-heavy: explora, lee, selecciona |
| B | v4 | 7 | 5 | `grep` amplio + selects directos sin `read_file` |
| C | v5 | 2 | 6 | `grep` + **batching** (6 selects + done en 1 turno) |
| D | v5 | 23 | **20** | `grep` + selects 1-a-1, sin batching |

Run D es el primero donde la cobertura del dir de modelos se acerca al máximo: aparecen por fin `Coupon`, `Transaction`, `Blocker`, `IapPurchaseReceipt`, `NewsPost`, `EmailUnsubscription`, `PushDevice`, `SubscriptionPlan`, `UserHistory`, `UserNotification`. Pero la pasada implícita SIGUE sin hacerse — el agente lo afirma en el summary y el trace lo desmiente (cero grep/read fuera del dir de models).

### 6.5 Aprendizaje añadido

**El prompt es necesario pero la varianza del modelo lo sobrescribe.** Dos runs con el mismo prompt v5 dieron 2 iter / 6 archivos / batched vs 23 iter / 20 archivos / sin batchear. La cobertura efectiva del prototipo NO está determinada solo por el código, el prompt y el modelo — también por la estrategia exploratoria que el modelo improvisa en cada run. Para defender el TFG: presentar los rangos observados, no un único número.

### 6.6 Estado real al cerrar la sesión (intermedio)

- `DiscoveryState.turns` + render en `discovery.md`.
- `out/00_discovery/tree.txt` con el árbol exacto que recibió el agente.
- Prompt `discovery_system.md` en v5 (63 líneas).
- Punto 25 añadido a CLAUDE.md con los 4 runs comparados y el descubrimiento del árbol truncado.
- Próximo candidato más prometedor: **BFS en `build_tree_summary`** para garantizar visibilidad de todos los top-level dirs (bloquea la pasada implícita en repos grandes).

---

## 7. Addendum (misma sesión, sub-iteración final) — BFS + cap 2000 + skip tests + batching como regla dura

Tras commitear lo de §6, el usuario preguntó dos cosas: *"¿por qué limitar a 600 el tree? hay muchas líneas de test que nos podríamos ahorrar"* y *"hay que mantener la calidad del batching, ahorra muchas peticiones"*. Ambas en un commit:

### 7.1 `build_tree_summary` reescrito

- **DFS → BFS**: BFS garantiza que todos los top-level dirs aparezcan antes de profundizar. Con DFS alfabético, en Habitica el cap se consumía dentro de `test/api/v3/...` antes de llegar a `website/`.
- **`max_entries` 600 → 2000**: ~30K tokens, sigue muy por debajo del cap TPM de 250K. Los 600 originales eran conservadores sin medir.
- **`TREE_SKIP_SUFFIXES`**: `.test.js`, `.test.ts`, `.spec.js`, `.spec.ts` etc. se omiten del dump del árbol. NO del filtro global: si el agente da con un test por otra vía (grep da hit en un fixture, p. ej.) puede leerlo. La lista de evidencia del prompt sigue mencionando "fixtures, tests" — la asimetría es deliberada (no acaparar el cap del árbol, pero no negar acceso).

Verificación con el repo cacheado de Habitica:
- Antes: 11 de 12 top-level dirs visibles, 0 entradas bajo `website/`.
- Ahora: 12/12 top-level dirs, 1516 entradas bajo `website/`, 26 entradas en `website/server/models/`, dirs candidatos a evidencia implícita visibles (`website/server/{controllers,libs,middlewares}/`).

### 7.2 Batching promovido a regla dura

El nudge en la sección de estrategia se reescribió como **Regla 1** del bloque de reglas duras, con framing operativo sobre RPM en vez de "tip":

> **Una respuesta = una petición. Batchea las decisiones firmes.** Cada respuesta tuya cuesta una unidad de cuota RPM. Tu respuesta puede contener N tool_calls que se ejecutan localmente y se te devuelven todos los resultados juntos en el siguiente turno. (...) Tras un grep, si identificaste 5 archivos como evidencia directa, los 5 select_evidence van en una sola respuesta, no en 5 turnos separados. La única excepción legítima es cuando una decisión depende del resultado de otra acción.

### 7.3 Dos runs adicionales mostraron el efecto

| Run | Prompt + sistema | Iter | Tool calls | Archivos | /iter |
|---|---|---|---|---|---|
| F | v5.1 + BFS | 10 | 10 | 8 | 1.0 |
| **G** | v5.1 + BFS | **5** | **25** | **22** | **5.0** |

Run G es el mejor sobre Habitica hasta ahora: 22 archivos cubriendo TODOS los modelos top-level + el subdir `user/` completo + el subdir `analytics/` completo (que nunca apareció en runs previos). El agente emitió 19 selects en un solo turno (iter 2). Pero Run F con la misma config solo dio 8 archivos sin batchear — **la regla dura sube el techo del mejor run sin eliminar la varianza**.

### 7.4 Aprendizaje añadido (refuerza el del v3→v4→v5)

El comportamiento de batching parece ser una característica latente del modelo en cada corrida, **poco influenciable por el prompt aunque sea regla dura**. Para forzar batching realmente, la vía es a nivel código: añadir una tool `select_evidence_batch(items=[...])` o agrupar `select_evidence` consecutivos en `dispatch()`. Queda pendiente como "Siguiente" #3 en CLAUDE.md.

Sobre la pasada implícita: Run F seleccionó `website/server/libs/baseModel.js` — un archivo fuera del dir de models que **con el árbol DFS anterior no era visible**. Pequeña señal de que la pasada implícita empieza a ser posible cuando el árbol cubre los dirs candidatos. Sigue sin ser determinista.

### 7.5 Estado final al cerrar la sesión

- `build_tree_summary` en BFS, cap 2000, skip de tests del dump del árbol.
- Prompt `discovery_system.md` en v5.1 (batching como regla 1).
- Punto 26 añadido a CLAUDE.md.
- "Siguiente" actualizado: #1 retry 5xx Google, #2 validar pasada implícita en repo Mongo-sin-Mongoose, #3 batching a nivel código si la varianza se confirma bloqueante.
