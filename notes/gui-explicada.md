# GUI explicada

Documento vivo para defender la interfaz gráfica (RU-7.2) ante el tribunal del TFG. Resume el porqué de cada decisión técnica y arquitectónica, mapea archivos a responsabilidades y anticipa preguntas habituales.

---

## 1. Aspecto visual

CustomTkinter es un *toolkit* moderno construido sobre Tkinter que reemplaza los widgets nativos por widgets propios con esquinas redondeadas, *hover effects*, soporte de tema oscuro/claro automático según el sistema operativo y tipografías limpias (Segoe UI en Windows, Helvetica en macOS). Visualmente está más cerca de Discord o de los paneles de configuración modernos que del Tkinter clásico.

Las decisiones de estilo concretas siguen una **paleta surface tonal inspirada en Material Design 3** con seed azul (ver §5 Mecánica 6):

- Familia surface azul tenido en light, surface oscuro neutro en dark.
- Cards `surface-container` con esquinas redondeadas de 12 px, jerarquía tonal por elevación (header más alto, bloques medios, visores más bajos).
- Botones azules (rol *primary*) para acciones; rojos M3 (`#ba1a1a / #93000a`, rol *error*) para Cancelar.
- Transiciones suaves al pulsar (*hover state* automático).
- Banner de estado en la pantalla de resultado con paleta M3: **primary-container** (azul, éxito), **tertiary-container** (teal, cancelado), **error-container** (rosado, error). Sin amarillos sueltos.

Esta descripción está alineada con la justificación de la elección en cap03 §3.3.1 de la memoria ("aspecto moderno y consistente entre plataformas").

---

## 2. Justificación del framework

### CustomTkinter (seleccionado)
- Curva mínima (es Tkinter por debajo).
- Empaquetado trivial con PyInstaller en un binario monolítico.
- Aspecto moderno sin dependencias web ni servidor local.
- Modelo de *polling* con `after(...)` adecuado para drenar la cola del hilo trabajador.

### Streamlit (descartado)
Su modelo "re-ejecutar el script entero en cada interacción" rompe el seguimiento en *streaming* del agente: cuando el agente emite `[iter 03] -> grep(...)`, Streamlit re-renderiza el script y el flujo se entrecorta. Además requiere servidor local + navegador externo, lo que rompe el modelo "ejecutable monolítico".

### PyQt6 / PySide6 (descartado)
Curva de aprendizaje notable (modelo *signals/slots*, gestión de hilos con `QThread`), tamaño del ejecutable empaquetado (≈80 MB con PyInstaller) y decisión de licencia LGPL/GPL que añade fricción innecesaria en contexto académico.

---

## 3. Arquitectura: tres capas estrictas

### Capa de presentación (`normalizer/gui/windows/` + `components/`)
Solo widgets. No importa `GoogleProvider`, `LLMProvider` ni el agente. Solo importa los puntos de entrada del núcleo (`run_pipeline`, `discover_from_url`) y los catálogos de configuración (`DEFAULT_MODELS`, `DEFAULT_AGENT_MODELS`, `available_providers()`), que son tipos elementales (`dict[str, str]`, `list[str]`).

### Capa de aplicación (`normalizer/gui/controller.py`, `GuiController`)
Traduce eventos de la UI a invocaciones del núcleo. Lanza el hilo trabajador, gestiona la cola de eventos, captura excepciones y empaqueta el resultado para la UI.

### Capa de núcleo (`normalizer/pipeline.py` + `normalizer/discovery/`)
Exactamente la misma que utiliza la CLI. No se reimplementa nada.

**Implicación para la defensa:** cualquier mejora futura del *pipeline* o del agente queda accesible desde ambas interfaces sin tocar la GUI. Eso es la **paridad funcional CLI/GUI** (RF-6.3). Si se añade Z.ai como tercer proveedor, la GUI lo recoge automáticamente sin modificar ninguna pantalla.

---

## 4. Pantalla por pantalla

### Pantalla 1 — Configuración (`gui/windows/config.py`)

Tres bloques verticales en un único formulario.

**Bloque 1 — Entrada.** `CTkSegmentedButton` con tres opciones (Archivo / Directorio / URL). Según la opción, el botón "Examinar..." abre el selector nativo del SO (`filedialog.askopenfilename` o `askdirectory`) o se deshabilita (URL). La validación de existencia y formato URL es inmediata vía `trace_add("write", ...)`. Si la validación falla, el botón "Ejecutar" queda gris y un texto explica el motivo.

Sobre el bloque hay un **enlace discreto "Abrir resultados existentes..."** que dispara `_open_existing()`: pide un directorio `out-*/`, valida que tenga al menos `04_ddl.sql`, detecta si tuvo descubrimiento (presencia de `00_discovery/`) y salta directamente a la pantalla de resultado sin re-ejecutar el pipeline. Útil para revisar diagramas ER o exportar a ZIP corridas antiguas sin gastar cuota.

**Bloque 2 — LLM y salida.** `CTkOptionMenu` para el proveedor (poblado dinámicamente con `available_providers()`). Al cambiar el proveedor, la pantalla consulta `LLMProvider.list_models(for_agent=False/True)` y popula los dos `CTkComboBox` con el catálogo dinámico del proveedor (`client.models.list()` del SDK correspondiente, gratuito y rápido). El modelo por defecto queda pre-seleccionado. Si la API key no está configurada o el listado falla, los combos caen al *default* y un texto auxiliar gris invita al usuario a introducir la clave. El combo del agente filtra por una *whitelist* corta de modelos verificados con *function-calling* dentro del propio *provider* — ningún SDK expone hoy ese metadato. Solo se habilita si el modo de entrada es URL. El directorio de salida por defecto es `out-gui-YYYYMMDD-HHMMSS/` para que cada corrida tenga su propio *sandbox*.

**Bloque 3 — Credenciales.** Detecta si `GOOGLE_API_KEY` o `GROQ_API_KEY` están en `os.environ`. Si sí, muestra `••••••••` deshabilitado + botón "Cambiar". Si no, campo editable con `show="*"`. Cuando el usuario introduce una clave y pulsa "Ejecutar", `persist_api_key()` (en `controller.py`) la inyecta en `os.environ` y la persiste en `.env` con `dotenv.set_key()`, que añade o reemplaza la línea correspondiente sin tocar el resto del fichero. Como `.env` está en `.gitignore`, no hay riesgo de *leak* al repositorio.

### Pantalla 2 — Ejecución (`gui/windows/run.py`)

Cuatro bloques verticales con el **bloque del pipeline como protagonista** (la primera versión los daba apilados sin jerarquía; ahora el pipeline ocupa el espacio dominante).

**Header (`surface-container-high`).** Card con título "Ejecución" + chip con el modo de entrada (archivo / directorio / URL) + botón Cancelar a la derecha. Debajo, una fila de metadatos con iconos unicode (`◆ proveedor`, `▸ modelo pipeline`, `▸ modelo agente` si URL, `▸ out_dir/`).

**Bloque "Progreso del pipeline" (`surface-container`).** Una fila por fase (no más chips horizontales): cada fila tiene icono de estado (`○` pendiente, `●` activa, `✓` completada, `✗` error, `⏸` cancelling), nombre de la fase y duración en vivo (`en curso · 0:42`, `completada · 2:14`). La fase activa tiene fondo destacado (rol *primary-container*) y su contador refresca cada segundo. Footer del bloque con `Fase X de Y · MM:SS transcurridos`. En modo URL hay 4 fases (Descubrimiento, Análisis, Diseño, DDL); en archivo/directorio, 3 (sin Descubrimiento).

**Bloque "Iteraciones del agente"** (solo modo URL). `CTkScrollableFrame` con dos columnas (`Iter | Tool calls`). Se rellena en vivo cada vez que llega un evento `[iter NN] -> ...` por el *callback*.

**Bloque "Log" (`surface-container`, altura fija).** `CTkTextbox` compacto con `wrap="none"` y auto-*scroll* al final. Recibe todas las líneas `[mm:ss]` — el mismo flujo que se ve por *stderr* en la CLI. Pequeño porque ya no es protagonista: las fases del pipeline llevan ese papel.

**Botón Cancelar.** Llama a `controller.cancel_and_abandon()` y salta inmediatamente a la pantalla de resultado (ver §5 Mecánica 3) — no espera a que termine la llamada al LLM en curso.

### Pantalla 3 — Resultado (`gui/windows/result.py`)

Tres componentes.

**Banner superior.** Cambia de color según el estado siguiendo roles M3 de container: **primary-container** (`#d6e4f3 / #1f3a52`, éxito, "DDL generado en …"), **tertiary-container** (`#d2e6ee / #244c5f`, cancelado, con texto explicativo de que la última llamada al LLM puede seguir terminando en background), **error-container** (`#ffdad6 / #5a1a18`, error con la fase y el mensaje).

**`CTkTabview` con artefactos.** Hasta cinco pestañas:
1. **Diagrama ER** (pestaña por defecto): generación bajo demanda (detalle en §5).
2. **Diseño**: `03_design.md` renderizado por `MarkdownView`. **Tablas embebidas como widgets reales** (no más texto monospace que se rompía con `wrap="word"`): cada tabla markdown es un `tk.Frame` con grid de `tk.Label`, header en bold, cuerpo con filas alternas, bordes finos. Si la tabla excede el ancho del visor, aparece scrollbar horizontal **solo para esa tabla**, no para el documento entero.
3. **DDL**: `04_ddl.sql` con resaltado de sintaxis SQL vía `pygments`. Paleta tema-aware: keywords y números en *primary*, strings en *tertiary*, builtins en *secondary*, comentarios en *on-surface-variant*.
4. **Análisis**: `02_analysis.md` renderizado por `MarkdownView`.
5. **Descubrimiento**: `00_discovery/discovery.md` (solo en modo URL).

**Barra de acciones inferior.** Tres botones:
- "Abrir directorio": `os.startfile` (Windows) / `open` (mac) / `xdg-open` (linux).
- "Exportar como ZIP": `shutil.make_archive`, comprime el `out_dir` entero.
- "Nueva ejecución": vuelve a pantalla 1 reseteando el estado.

---

## 5. Las seis mecánicas técnicas clave

### Mecánica 1 — Captura de progreso vía *callback* (no redirección de *stderr*)

**Problema.** La CLI muestra `[00:14] Pipeline: ANÁLISIS ok (28s)` por *stderr*. La GUI necesita ver lo mismo en vivo en su panel.

**Opciones consideradas.**
- Redirigir `sys.stderr` a un *buffer*: captura todo (incluidos *tracebacks* y *warnings* de los SDKs), obliga a parsear texto.
- ***Callback* estructurado**: seleccionada.

**Implementación.** En `normalizer/_log.py` hay una lista `_callbacks: list[Callable[[str], None]]`. Cuando el código llama `log("Pipeline: ANÁLISIS ...")`, esa línea sale por *stderr* y se reenvía a todos los *callbacks* registrados. La GUI registra uno con `register_callback(self._on_log_line)` antes de lanzar el hilo trabajador y hace `unregister_callback` al terminar. El *callback* solo mete la línea en una `queue.Queue`. **No toca *widgets*** — Tkinter no es *thread-safe*.

**Reset del reloj relativo.** Justo antes de `register_callback`, `GuiController.start()` invoca `_log.reset_clock()`. Sin esto, el `_START = time.monotonic()` calculado al **importar** el módulo arrastraría todo el tiempo de configuración (en la GUI puede ser de minutos entre el arranque de la app y la primera ejecución), y la primera marca aparecería como `[02:34]` en lugar de `[00:00]`. La CLI no necesita reset porque el import y la primera línea de log son simultáneas.

### Mecánica 2 — Hilo trabajador + cola + `after()`

**Problema.** Si llamamos a `run_pipeline()` desde el hilo principal de la GUI, la ventana se congela durante minutos. Si lo llamamos desde otro hilo y ese hilo toca *widgets*, Tkinter falla.

**Patrón productor-consumidor.**
1. El hilo principal lanza `threading.Thread(target=self._run, daemon=True)`. Ese hilo ejecuta `discover_from_url()` y `run_pipeline()`.
2. El hilo trabajador encola eventos en una `queue.Queue` compartida.
3. El hilo principal usa `app.after(100, self._poll)` para drenar la cola cada 100 ms con `queue.get_nowait()` y actualizar *widgets*.

`_poll` detecta cuándo termina el hilo (`thread.is_alive() == False`), drena lo que queda y transiciona a la pantalla 3 con `app.after(600, self._finish_transition)` — los 600 ms permiten al usuario ver el último estado antes del cambio de pantalla.

### Mecánica 3 — Cancelación cooperativa **en el núcleo** + UI responsiva con *abandonment*

**Problema.** Si el usuario pulsa "Cancelar" durante una llamada a `provider.generate()`, no se puede matar la conexión HTTP a mitad — los SDKs de Google y Groq son síncronos y bloqueantes. Sí se puede abortar **entre** llamadas. Pero hacer que la UI espere ~1 min a que termine la llamada actual da la sensación de cuelgue, aunque técnicamente esté esperando.

**Implementación en dos planos.**

**Plano A — Cancelación cooperativa del núcleo (RF-7.3):**
1. `GuiController` tiene `self._cancel = threading.Event()` que pasa como `cancel_event` a `run_pipeline()` y `discover_from_url()`.
2. El núcleo lo comprueba en **tres puntos**:
   - Entre fases del pipeline (`pipeline.py`: tras `01_input.txt`, tras `02_analysis.md`, tras `03_design.md`).
   - Al inicio de cada iteración del bucle del agente (`agent.py`).
   - **Entre llamadas a *tools* dentro de un mismo turno del agente**: cuando el agente batchea 4-5 `read_file`/`select_evidence` en una sola respuesta, sin este chequeo la cancelación esperaría a despachar todas.
3. Si el evento está señalizado, se levanta `PipelineCancelled` (definida en `pipeline.py`).

**Plano B — UI responsiva con `cancel_and_abandon()`:**
1. Al pulsar Cancelar, `RunScreen._on_cancel()` llama a `controller.cancel_and_abandon()`.
2. Ese método señaliza el `cancel_event`, marca el controlador como `_abandoned = True` y **desregistra el *callback* del log inmediatamente**. Cualquier evento posterior del hilo trabajador (`LogLineEvent`, `DoneEvent`, etc.) se descarta en `_on_log_line` y `_run` mediante chequeos `if self._abandoned: return`.
3. La pantalla **transita a `ResultScreen` sin esperar al hilo**. El usuario ya está revisando los artefactos parciales en disco mientras el hilo huérfano —`daemon=True`— termina la llamada al LLM en background y muere solo.

**Garantía.** Los artefactos ya escritos a disco se preservan (la cancelación cooperativa garantiza que `_read_input`, `02_analysis.md` o `03_design.md` quedan completos si ya estaban). El hilo huérfano no contamina futuras corridas (los eventos quedan descartados; la siguiente `GuiController.start()` resetea `_abandoned = False` y registra un *callback* nuevo).

**Por qué no `ctypes.PyThreadState_SetAsyncExc`** (la única forma de "matar" un hilo Python real). Es frágil, mal documentada y no aborta la llamada HTTP, que sigue en una capa C nativa. La política de *abandonment* es más limpia y suficiente para el caso de demo: el coste del hilo huérfano es despreciable (1 thread daemon que muere en ≤1 min).

### Mecánica 4 — Diagrama ER auto-generado

**Cadena.** `04_ddl.sql` → `parse_ddl()` → `(tables, fks)` → `build_dot()` → `(DOT, engine)` → `graphviz.Source(dot, engine=engine).render()` → PNG → `PIL.Image.open()` → `tk.Canvas` con `ImageTk.PhotoImage` + *scrollbars* XY + controles de zoom.

**Parser** (`ddl_graph.py`): *regex* sobre `CREATE TABLE name (...)`, división del cuerpo por comas a profundidad 0, distinción entre columnas y *constraints*, extracción de claves primarias y foráneas. Validado sobre Spruce: 11 tablas y 11 FKs correctas; sobre Habitica: 31 tablas y 38 FKs.

**Selección de *layout*** (`_pick_layout`). Heurística según la topología del grafo: si existe una tabla con más de 10 FKs entrantes (un *hub* — caso típico de `Users` en aplicaciones reales) o el grafo tiene más de 20 tablas, se usa el *engine* `sfdp` (*force-directed*), que coloca el *hub* en el centro y distribuye los demás nodos alrededor. Si no, se usa `dot` (*hierarchical*) con `rankdir=LR`, `splines=spline` y `concentrate=true`, que es lo más limpio para grafos modestos. La razón es que `dot` apila aristas paralelas en líneas adyacentes y, cuando un nodo recibe 20+ FKs, el resultado es ilegible.

**Render**: la lib Python `graphviz` delega al binario `dot` del sistema. En Windows, `_ensure_graphviz_in_path()` localiza el binario en rutas estándar (instalador oficial / winget) y lo añade al PATH del proceso si no estaba — esto evita el caso "lo acabo de instalar pero el proceso ya corriendo no lo ve". Si aun así no está disponible, `render_to_png()` devuelve `None` y la pestaña ER muestra instrucciones de instalación con un botón **Reintentar**; el resto de pestañas siguen funcionando.

**Visor.** La pantalla 3 muestra el PNG dentro de un `tk.Canvas` con *scrollbars* horizontal y vertical (Tkinter nativo, porque `CTkScrollableFrame` solo soporta una orientación) y una barra superior con controles de zoom (−, +, 100%, Ajustar a ventana). `Ctrl + rueda` también hace zoom. Un botón adicional "Abrir en visor externo" delega el PNG al visor del SO para usos que requieran zoom/pan más rápidos.

**Rendimiento del zoom.** Sobre el diagrama de Habitica (2896×2578 px) el `LANCZOS` original tardaba 2-3 s por *resize*, lo que hacía cada click `+/−` lento. Dos optimizaciones:
- **`Image.BILINEAR` en lugar de `LANCZOS`**: ~10× más rápido y la pérdida de calidad es imperceptible para un grafo con líneas y texto.
- **Debounce de 80 ms con `after_cancel`**: clicks rápidos consecutivos descartan los *redraws* intermedios y solo el último ejecuta. La etiqueta de zoom sí se actualiza inmediatamente para feedback, aunque el render esté *debounced*.

**Estilo del diagrama.** Cada tabla es un nodo con cabecera en *primary-container* claro y filas con columnas alineadas a la izquierda. Las PKs llevan el prefijo `[PK]`. Las aristas son las FKs con `xlabel="col_origen → col_destino"` (`xlabel` y no `label` porque algunas combinaciones de *engine* + *splines* descartan las etiquetas pegadas a la arista; `xlabel` las flota cerca sin perderlas).

### Mecánica 5 — Catálogo dinámico de modelos

**Problema.** En la primera iteración los modelos disponibles por proveedor estaban hardcoded en `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`. El catálogo de los proveedores cambia mensualmente; cerrarlo dentro del provider no tiene sentido cuando los SDKs ya exponen `client.models.list()`.

**Implementación.**
1. El protocolo `LLMProvider` define `list_models(for_agent: bool = False) -> list[str]`.
2. `GoogleProvider` y `GroqProvider` consultan `client.models.list()` (gratis, ~100 ms). Filtran por capacidades del SDK (`generateContent` en Google, `active=True` en Groq).
3. Para `for_agent=True`, intersección con una **whitelist mínima por proveedor** de modelos verificados con *function-calling* (Gemini family en Google; `qwen/qwen3-32b` y `llama-4-scout` en Groq). Ningún SDK expone hoy el metadato "soporta tools".
4. Caché por instancia: las llamadas repetidas no vuelven a la red.
5. La pantalla de configuración llama `_fetch_models(provider)` al cambiar de proveedor. Si la API key no está o el listado falla, los combos caen al *default* y un texto auxiliar gris invita al usuario a introducir la clave para ver el catálogo completo.

**Defaults preservados.** `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS` siguen siendo necesarios para la CLI (cuando no se pasa `--model`/`--agent-model`) y para pre-seleccionar el modelo en la GUI tras listar.

### Mecánica 6 — Paleta surface tonal M3

**Problema.** CustomTkinter trae el *theme* "blue" por defecto, que mezcla grises neutrales en los contenedores con beige cálido en los inputs (`CTkEntry`, `CTkComboBox`). Convivían con las cards azules que añadí, dando sensación de "fondos sin armonía" y tonos amarillentos.

**Solución.** Aplicar una **paleta surface tonal derivada del seed primary azul (`#1f6aa5`)** a todos los contenedores y inputs, siguiendo los roles M3 (consultados con la skill `material-3` instalada en `~/.claude/skills/material-3`). El sistema:

| Rol M3 | Light | Dark | Uso |
|---|---|---|---|
| `surface` | `#eaf0f8` | `#101418` | Root, canvas ER |
| `surface-container-low` | `#dfe7f2` | `#181c20` | Visores `MarkdownView`/`SqlView`, inputs, code blocks |
| `surface-container` | `#dfe7f2` | `#1c2024` | Cards de bloque (pipeline, agente, log, bloques pantalla 1) |
| `surface-container-high` | `#cedaee` | `#26292d` | Header pantalla 2, header de tablas markdown, tag `code` inline |
| `surface-container-highest` | `#bdcee5` | `#30343a` | Chip de modo |
| `outline-variant` | `#a8bcd9` | `#3a4456` | Bordes de inputs, separadores |

Los **estados** siguen roles container del sistema: *primary-container* (activo, éxito), *tertiary-container* (cancelado), *error-container* (error). **Sin amarillos sueltos** — antes había varios (`#a06800` strings SQL, `#7c3aed` builtin, `#fff4d6` warning cancelado, default beige de CTkEntry). Reemplazos:

- Strings SQL → *tertiary* (`#3c6477 / #a4c8d6`).
- Builtin SQL → *secondary* (`#516a86 / #b8c5d5`).
- Botón Cancelar → rol *error* M3 (`#ba1a1a / #93000a` con `on-error` blanco).
- Banner cancelado → *tertiary-container*.

**Detalle técnico.** El `fg_color` del root `CTk` se pasa en `super().__init__(fg_color=…)`. `self.configure(fg_color=...)` post-init no actualiza siempre el background de la ventana raíz — quirk conocido de CTk.

**Honestidad para defensa.** La skill `material-3` está orientada a Jetpack Compose y web. Aporta **principios y tokens** (escala 4/8/12/16/20/24, jerarquía surface, pairs `on-X`), no componentes M3 en CustomTkinter. El techo del *toolkit* sigue siendo CTk: no hay sombras reales, animaciones complejas ni `MaterialTheme`. La paleta unificada da coherencia visual; saltar a Material 3 nativo requeriría cambiar de framework (Flet o equivalente).

---

## 6. Mapa de archivos

```
normalizer/gui/
├── __init__.py             — expone main() para conveniencia de importación
├── __main__.py             — punto de entrada: `python -m normalizer.gui`
├── app.py                  — NormalizerApp (CTk root) + navegación entre pantallas
├── state.py                — dataclass GuiState + PhaseInfo (timestamps por fase)
├── controller.py           — GuiController + eventos (Log/Done/Cancelled/Error) + ENV_KEY_BY_PROVIDER + resolve_default_out_dir + persist_api_key
├── ddl_graph.py            — parse_ddl + _pick_layout (dot vs sfdp) + _ensure_graphviz_in_path + render_to_png
├── windows/
│   ├── config.py           — ConfigScreen (pantalla 1) con _open_existing + tokens de paleta de inputs
│   ├── run.py              — RunScreen (pantalla 2)
│   └── result.py           — ResultScreen (pantalla 3) con visor ER (zoom + scroll XY + debounce)
└── components/
    ├── markdown_view.py    — MarkdownView (tags Tkinter + tablas como widgets reales embebidos)
    └── sql_view.py         — SqlView sobre pygments con paleta tema-aware
```

**Sobre la separación `windows/` vs `components/`:** `windows/` contiene contenedores de pantalla completa con lógica de orquestación (lanzan el *controller*, gestionan navegación). `components/` contiene *widgets* reutilizables que solo saben renderizar un *input*.

**Sobre los *helpers* en `controller.py`** (`ENV_KEY_BY_PROVIDER`, `resolve_default_out_dir`, `persist_api_key`): son utilidades de la capa de aplicación que la pantalla 1 necesita. Quedan en `controller.py` para evitar un módulo aparte con 3 funciones cortas. Aparecen al principio del archivo, antes de `GuiController`, para que se vean al abrir el fichero.

---

## 7. Cambios mínimos al núcleo

| Archivo | Qué añade | Por qué |
|---|---|---|
| `normalizer/_log.py` | `register_callback` / `unregister_callback` + `reset_clock`. | La GUI consume el flujo de log; `reset_clock()` reinicia el `_START` para que cada corrida arranque en `[00:00]` (sin él, la GUI arrastraba el tiempo desde el import del módulo). CLI no llama `reset_clock`, su comportamiento es idéntico. |
| `normalizer/pipeline.py` | `PipelineCancelled` + `_check_cancel()` + parámetro opcional `cancel_event` en `run_pipeline`. | Cancelación cooperativa entre fases. |
| `normalizer/discovery/agent.py` | Importa `PipelineCancelled`, añade `cancel_event` opcional, comprueba al inicio de la iteración y **entre tools del mismo turno**. | Granularidad fina del *cancel* en el bucle del agente. |
| `normalizer/discovery/tools.py` | `_do_read_file` evita relectura de archivos ya seleccionados con `select_evidence`. | Ahorra cuota: releer un archivo ya marcado como evidencia duplica tokens en el historial. |
| `normalizer/providers/base.py` | `list_models(for_agent: bool = False) -> list[str]` en el `Protocol`. | API uniforme para que la GUI liste catálogos dinámicamente. |
| `normalizer/providers/google.py` y `groq.py` | Implementación de `list_models()` con caché por instancia + whitelist mínima de modelos *agent-capable*. | Catálogo dinámico desde el SDK + filtro de capacidad cuando el SDK no lo expone. |

**El CLI no se tocó.** `cli.py` está exactamente como antes. Añadir la GUI no rompe el camino CLI existente — punto que probablemente el tribunal comprobará.

---

## 8. Verificación realizada y pendiente

### Verificado programáticamente (sin LLM real)
- Todas las pantallas se construyen sin error en `app.update()`.
- El *callback* de `_log.py` recibe líneas y la cola del *controller* las acumula.
- Las *regex* de *parsing* de iteraciones del agente funcionan sobre líneas reales.
- El parser DDL extrae correctamente 11 tablas y 11 FKs de `out-facil/04_ddl.sql`.
- El render PNG devuelve `None` si Graphviz no está (fallback funciona).
- El CLI `python -m normalizer --help` sigue funcionando idéntico.

### Pendiente de verificación interactiva (manual con LLM real)
1. **Archivo único**: `data/spruce/keys.js` con `google` → DDL en pantalla 3 con la tabla `API_KEYS` visible en el diagrama.
2. **Directorio**: `data/spruce-difuso/` → 7-11 entidades según el modelo.
3. **URL**: `https://github.com/dan-divy/spruce` → tabla del agente actualizándose en vivo en pantalla 2.
4. **Cancelación**: durante el caso URL, pulsar Cancelar en mitad del descubrimiento. Verificar que `00_discovery/evidence/` está en disco y que el panel termina con "Cancelado".
5. **Key inválida**: invalidar temporalmente `GOOGLE_API_KEY` en `.env`. Esperar la transición a la pantalla de resultado con un banner en *error-container* que indica la fase de origen y el mensaje del proveedor.
6. **Graphviz ausente**: sin instalarlo, la pestaña ER muestra las instrucciones. Para activarlo: `winget install Graphviz.Graphviz` (Windows), `brew install graphviz` (macOS), `apt install graphviz` (Linux).

---

## 9. Preguntas anticipadas del tribunal

**"¿Por qué no Streamlit?"** El "*rerun on interaction*" rompe el *streaming* de eventos del agente. Un TFG de demo necesita mostrar visualmente cómo el agente toma decisiones en vivo, y Streamlit lo entrecorta.

**"¿Por qué un hilo y no `async`?"** Los SDKs de Google y Groq son síncronos. Los *wrappers async* (`asyncio.to_thread`) acaban usando un hilo bajo el capó. El hilo explícito es más legible y elimina una capa.

**"¿Qué pasa si el usuario cierra la ventana durante la ejecución?"** El hilo es `daemon=True`, así que muere con el proceso. Los artefactos ya escritos se preservan en disco.

**"¿Es seguro guardar las API keys en `.env`?"** `.env` está en `.gitignore` desde la creación del proyecto. La GUI muestra un aviso explícito antes de guardarlas. La alternativa sería un *keyring* del sistema operativo, pero añade complejidad multiplataforma sin beneficio claro en contexto académico.

**"¿Por qué Graphviz y no algo web (D3, vis.js)?"** Rompería el modelo de "ejecutable monolítico" — requeriría servidor HTTP + navegador. Graphviz es un binario local que produce PNG, y CustomTkinter los muestra directamente.

**"¿Cómo se reconcilia que la GUI dependa de `customtkinter` pero el CLI no?"** Mediante el extra opcional `[gui]` en `pyproject.toml`. `pip install -e .` instala solo lo necesario para el CLI; `pip install -e .[gui]` añade `customtkinter`, `pygments`, `graphviz` (lib Python) y `Pillow`. La capa de núcleo (`pipeline.py`, `discovery/`, `providers/`) no importa ninguno de los paquetes de la GUI.

**"¿Qué garantiza la paridad funcional CLI / GUI (RF-6.3)?"** Que la GUI no reimplementa lógica: importa `run_pipeline`, `discover_from_url` y los catálogos de `providers` exactamente igual que la CLI. Las pruebas de sistema descritas en cap05 §5.3.3 ejercitan la GUI a través de `GuiController` sin interfaz visual, validando que el flujo es el mismo.

**"Dijiste que la cancelación es cooperativa pero ahora la GUI se salta a la pantalla de resultado inmediatamente, ¿no es contradictorio?"** No: la cancelación del **núcleo** sigue siendo cooperativa (RF-7.3) y necesaria para que los artefactos parciales se preserven correctamente en disco. La GUI usa `cancel_and_abandon()` para **desacoplar la UI del hilo trabajador** — el hilo sigue cancelándose ordenadamente, pero la UI no espera a que termine la llamada HTTP en curso. El hilo huérfano es `daemon=True` y muere solo. El usuario ve el resultado inmediatamente, los artefactos están bien y el coste técnico es despreciable.

**"¿Por qué aplicar Material Design 3 si CustomTkinter no es Material?"** La skill `material-3` aporta **tokens y principios** (escala tipográfica, sistema surface tonal, *pairs* `on-X`/`X`, jerarquía de elevación por color en lugar de sombras), no componentes M3. Aplicarlos a CTk da coherencia visual (paleta unificada, espaciado en escala 4/8/12/16/20/24) sin pretender que CTk renderice como Flutter Material. El techo del *toolkit* sigue siendo CTk; la decisión de no cambiar de framework está documentada en cap03 §3.3.1.

**"¿Cómo está poblado el combo de modelos? ¿Y si el catálogo del proveedor cambia?"** Dinámicamente: la pantalla 1 invoca `LLMProvider.list_models()` al cambiar de proveedor, que internamente llama a `client.models.list()` del SDK (gratis, ~100 ms). Los catálogos `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS` se mantienen únicamente como defaults pre-seleccionados, no como listas cerradas. La whitelist `_AGENT_CAPABLE` por *provider* filtra los modelos con *function-calling* verificado para el combo del agente — esta sí es manual porque ningún SDK expone hoy ese metadato.
