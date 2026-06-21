# Capítulo 7. Implementación

Este capítulo documenta la implementación de la herramienta, partiendo del diseño descrito en el capítulo 6. Se centra en la estructura organizativa del código y en los aspectos de implementación más relevantes, sin sustituir al propio código fuente, que se entrega como anexo conforme a la recomendación de la plantilla.

## 7.1 Estructura de la aplicación

Esta sección adopta el enfoque de _vista de bloques de construcción_ (_Building Block View_) de ARC42: muestra cómo el diseño lógico del capítulo 6 se materializa en una organización concreta de código, dependencias y artefactos desplegables. La descomposición en módulos y la responsabilidad de cada uno ya se presentó en §6.2.1 y no se repite aquí; este apartado se centra en la disposición física del repositorio (§7.1.1), las dependencias del proyecto (§7.1.2), su distribución y ejecución (§7.1.3) y los aspectos de implementación que encierran decisiones no triviales (§7.1.4 y §7.1.5). La vista de despliegue —máquina del usuario, servicios externos y directorios de estado— corresponde a §6.1.3 y tampoco se reproduce.

### 7.1.1 Organización del repositorio

El repositorio del proyecto se organiza alrededor de un único paquete Python (`normalizer`) y su fichero de configuración (`pyproject.toml`), junto a un directorio `data/` con los _datasets_ de prueba. Las responsabilidades de cada módulo se detallaron en §6.2.1; aquí se enumera la disposición física para situar al lector frente al árbol real.

```
pyproject.toml              # metadatos del paquete, dependencias y console_scripts
.env.example                # plantilla de credenciales; el .env real queda fuera de Git
.gitignore                  # excluye .env, out-*/ y .cache/ del control de versiones
normalizer/
├── __init__.py
├── __main__.py             # python -m normalizer → cli.main
├── _log.py                 # log(msg) por stderr con sello [mm:ss] + callbacks + reset_clock
├── cli/                    # CLI Click: --provider, --model, --agent-model, --out-dir
│   ├── __init__.py         # re-exporta main
│   └── cli.py              # código del CLI (main)
├── gui/                    # Interfaz gráfica CustomTkinter (capa de presentación)
│   ├── __init__.py
│   ├── __main__.py         # punto de entrada: python -m normalizer.gui
│   ├── app.py              # NormalizerApp: ventana raíz + navegación entre pantallas
│   ├── state.py            # GuiState: estado de la sesión (configuración + run)
│   ├── controller.py       # GuiController: orquesta el núcleo en hilo trabajador
│   ├── ddl_graph.py        # parser DDL → DOT y render del diagrama ER con Graphviz
│   ├── windows/            # Las tres pantallas guiadas
│   │   ├── config.py       # ConfigScreen: entrada + proveedor + API key
│   │   ├── run.py          # RunScreen: progreso por fases + iteraciones del agente
│   │   └── result.py       # ResultScreen: artefactos + diagrama ER + exportación
│   └── components/         # Visores reutilizables sobre CTkTextbox
│       ├── markdown_view.py  # Renderizado de Markdown con tags + tablas como widgets reales embebidos
│       └── sql_view.py       # Resaltado de SQL con pygments (paleta tema-aware)
├── pipeline/               # paquete del pipeline
│   ├── __init__.py         # re-exporta run_pipeline, PipelineCancelled
│   └── pipeline.py         # 4 fases: run_pipeline + _read_input
├── prompts/                # ANALYZE, DESIGN, DDL, DISCOVERY_SYSTEM
│   ├── __init__.py
│   ├── analyze.md
│   ├── design.md
│   ├── ddl.md
│   └── discovery_system.md
├── discovery/              # Agente de descubrimiento
│   ├── __init__.py
│   ├── agent.py            # discover_from_url + bucle del agente
│   ├── tools.py            # ALL_TOOLS + dispatch + DiscoveryState
│   ├── filesystem.py       # build_tree_summary (BFS), resolve_within
│   └── repo.py             # clone_repo + cache .cache/repos/
└── providers/
    ├── __init__.py         # _REGISTRY, DEFAULT_MODELS, DEFAULT_AGENT_MODELS, build_provider
    ├── base.py             # Interfaz LLMProvider + dataclasses neutras
    ├── google.py           # GoogleProvider + _call_with_retry (429+5xx)
    └── groq.py             # GroqProvider + _call_with_retry (429)

data/
├── spruce/                 # 4 schemas Mongoose (caso de control)
└── spruce-difuso/          # 8 archivos sin schemas declarativos (caso realista)
```

Junto al paquete y los datos conviven directorios auxiliares: `.cache/repos/` donde el agente almacena los repositorios clonados; `out-*/` con los artefactos de cada ejecución (ignorados por Git); `memoria/` con los borradores y el documento de memoria; y `notes/` con los documentos vivos y los registros de sesión que sirven de soporte a este capítulo y al capítulo 3.

### 7.1.2 Dependencias del proyecto

El archivo `pyproject.toml` declara las dependencias mínimas del paquete. Se ha optado por un conjunto deliberadamente reducido, alineado con el principio de "_no magic_" defendido en §4.3.2: cada dependencia tiene una justificación clara y se utiliza una única biblioteca por responsabilidad.

| Dependencia     | Versión mínima | Responsabilidad                                                                                                                                                                                                                                                                                                                                                                  |
| --------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `google-genai`  | ≥ 1.0.0        | SDK oficial del proveedor Google Gemini. Utilizada únicamente por `providers/google.py`.                                                                                                                                                                                                                                                                                         |
| `groq`          | ≥ 0.11.0       | SDK oficial de Groq (API OpenAI-compatible). Utilizada únicamente por `providers/groq.py`.                                                                                                                                                                                                                                                                                       |
| `click`         | ≥ 8.1.0        | _Framework_ de CLI. Provee el _parser_ de argumentos y la generación de ayuda (`--help`).                                                                                                                                                                                                                                                                                        |
| `python-dotenv` | ≥ 1.0.0        | Carga del fichero `.env` para las credenciales (`GOOGLE_API_KEY`, `GROQ_API_KEY`).                                                                                                                                                                                                                                                                                               |
| `customtkinter` | ≥ 5.2.0        | _Toolkit_ gráfico de la GUI (§6.2.8). Dependencia opcional, agrupada en el extra `[gui]`.                                                                                                                                                                                                                                                                                        |
| `pygments`      | ≥ 2.0          | Tokenización de SQL para el resaltado de sintaxis en la pestaña DDL del resultado. Dependencia opcional `[gui]`.                                                                                                                                                                                                                                                                 |
| `graphviz`      | ≥ 0.20         | _Wrapper_ Python sobre el binario Graphviz. Genera el diagrama ER auto-derivado del DDL final. Dependencia opcional `[gui]`; requiere además el binario Graphviz instalado en el sistema (`winget install Graphviz.Graphviz` / `brew install graphviz` / `apt install graphviz`). Si falta, la pestaña ER muestra instrucciones de instalación sin afectar al resto de pestañas. |
| `Pillow`        | ≥ 10.0         | Carga del PNG del diagrama ER para mostrarlo en la GUI. Dependencia opcional `[gui]`.                                                                                                                                                                                                                                                                                            |

Las dependencias del extra `[gui]` se instalan con `pip install -e .[gui]`. El CLI (`python -m normalizer`) funciona sin ellas, lo que permite a un usuario que solo quiera usar la herramienta desde la línea de comandos evitar la instalación del _toolkit_ gráfico y de las librerías de visualización.

El requisito de versión de Python (`requires-python = ">=3.11"`) responde a dos necesidades: (i) la disponibilidad de las funcionalidades modernas del lenguaje que utilizan los SDKs (tipos `dict[str, …]` parametrizados sin importación, _match statements_) y (ii) la compatibilidad con las versiones mínimas que cada SDK declara como soportadas.

### 7.1.3 Distribución y ejecución

El paquete se distribuye como un proyecto editable instalable con `pip`. La invocación habitual del CLI es:

```
pip install -e .
python -m normalizer <entrada> [--provider …] [--model …] [--agent-model …] [--out-dir …]
```

El _script_ `normalizer` también queda registrado como punto de entrada del _console_script_ (`[project.scripts] normalizer = "normalizer.cli:main"`), de modo que el usuario puede invocar `normalizer <entrada>` directamente desde la terminal. Para la GUI, el punto de entrada es:

```
python -m normalizer.gui
```

Equivalentemente, el extra `[gui]` registra un segundo _console_script_ (`normalizer-gui = "normalizer.gui.app:main"`) que permite invocar la GUI como `normalizer-gui` desde cualquier shell tras `pip install -e .[gui]`.

### 7.1.4 Aspectos destacables de la implementación

A continuación se subrayan cuatro aspectos cuya implementación encierra decisiones técnicas no obvias y que conviene resaltar en este capítulo conforme a la recomendación de la plantilla de no copiar el código pero sí destacar lo relevante. El código completo se entrega como anexo.

#### Reintentos en `GoogleProvider._call_with_retry`

`providers/google.py` define `_RETRYABLE_CODES = {429, 500, 502, 503, 504}` y un máximo de cuatro reintentos. El motivo de incluir los códigos 5xx, no estrictamente _rate limits_, es empírico: la familia Gemma del _free tier_ devuelve códigos 500 y 503 transitorios con cierta frecuencia. La función respeta, cuando lo proporciona, el `retryDelay` que el SDK incluye en la respuesta del 429; en su ausencia utiliza una espera por defecto (`_FALLBACK_RETRY_DELAY_S = 15.0` s) más un _back-off_ exponencial. Esta política está alineada con RNF-2.2 y se valida durante las pruebas unitarias del adaptador con respuestas sintéticas.

`GroqProvider._call_with_retry` aplica la misma estructura, pero limitada a `RateLimitError` (HTTP 429), respetando la cabecera `retry-after` cuando está presente. Groq no presenta el patrón de 5xx transitorios observado en Google, lo que justifica la asimetría en la política de reintentos.

#### Construcción del árbol del repositorio en `build_tree_summary`

`discovery/filesystem.py` materializa el árbol que se entrega al agente en su primer mensaje. Tres decisiones se destacan:

- **Recorrido BFS por niveles, no DFS.** Garantiza que, si el corte de entradas se agota, todos los directorios de primer nivel ya han aparecido completos. Una primera implementación DFS hacía invisible directorios _top-level_ enteros en repositorios grandes (Habitica con `website/` sin entrar en el árbol).
- **Corte de entradas configurable, por defecto 2 000** (~30 K _tokens_ en _prompt_). El valor por defecto (constante `MAX_TREE_ENTRIES`) es un compromiso empírico entre cobertura del árbol y consumo de contexto: con 600 entradas (el valor original) varios _top-level_ de Habitica no aparecían; con 4 000 se desbordaba el TPM de los modelos _free_ de Groq. El usuario puede ajustarlo por ejecución con la opción `--max-tree-entries` (CLI) o el campo equivalente de la GUI —`discover_from_url` lo recibe como `max_tree_entries` y lo propaga a `build_tree_summary`—, de modo que repositorios grandes contra proveedores con cuota estrecha puedan reducirlo sin tocar código.
- **Omisión local de sufijos de pruebas** (`.test.js`, `.spec.ts`, etc.) del _dump_ del árbol, **no** de la accesibilidad: el agente sigue pudiendo leerlos vía `read_file` o `grep` si los encuentra por otra vía. La omisión sirve únicamente para evitar que las baterías de tests acaparen el corte de entradas.

#### Confinamiento de las herramientas en `resolve_within`

La función `resolve_within(repo_root, rel_path)` resuelve cualquier ruta relativa proporcionada por el agente contra el directorio raíz del repositorio clonado y rechaza con `ValueError` cualquier ruta que escape de ese ámbito. Esta función es el único punto en el que el agente toca el sistema de archivos: todas las herramientas (`list_dir`, `read_file`, `grep`, `select_evidence`) la atraviesan antes de actuar. Concentrar el control en una sola función simplifica la auditoría del cumplimiento de RF-4.2 y RNF-4.2.

#### Despacho de tools en `dispatch`

`discovery/tools.py:dispatch(call, state, max_files)` ramifica por `call.name` hacia los manejadores `_do_list_dir`, `_do_read_file`, `_do_grep` y `_do_select`, mientras que el caso `done` se resuelve directamente dentro de `dispatch` marcando `state.is_done = True` y guardando el `summary` en el estado. Esta uniformidad permite que el bucle del agente (`discover_from_url`) sea agnóstico a las herramientas concretas: se materializa el patrón Command (§6.2.6) con un _Invoker_ único y _Concrete­Commands_ aislados.

#### Preservación de metadatos opacos del proveedor en `Message.raw`

El historial que el agente reenvía en cada turno conserva, en el campo `Message.raw`, el objeto original devuelto por el SDK para los turnos del modelo. En el caso de Google, `_to_gemini_contents` reinyecta ese `Content` tal cual en lugar de reconstruirlo a partir de `content` y `tool_calls`: así se preservan metadatos opacos —como las firmas de razonamiento (`thought_signature`) que Gemini adjunta a sus respuestas— que, de perderse, degradarían la coherencia del modelo entre turnos. Es una decisión de implementación que no altera el modelo de objetos neutro (§6.2.2): `raw` es un campo auxiliar que cada adaptador rellena y consume según las necesidades de su SDK.

### 7.1.5 Implementación de la interfaz gráfica

La GUI se implementa en `normalizer/gui/`. La capa de presentación (`gui/windows/`) instancia las tres pantallas guiadas descritas en §5.1.3: configuración (entrada + proveedor + credenciales), ejecución con progreso por fases + tabla del agente, y resultado con diagrama ER + artefactos en pestañas. La capa de aplicación (`gui/controller.py`, clase `GuiController`) recibe los eventos de la presentación, valida los argumentos y lanza la ejecución del núcleo en un hilo trabajador independiente del hilo de la interfaz, evitando el bloqueo de la ventana durante las llamadas al LLM.

El **progreso en tiempo real** se materializa mediante el sistema de _callbacks_ de `normalizer/_log.py` (descrito en §6.2.8): la GUI registra una función con `register_callback()` antes de arrancar el hilo trabajador, y el hilo de la interfaz consume la cola del `GuiController` con `app.after(...)` (Tkinter no es _thread-safe_, por lo que ningún _widget_ puede tocarse desde el hilo trabajador). Antes de registrar el _callback_, `GuiController.start()` invoca `_log.reset_clock()` para que la primera línea de log de cada corrida marque `[00:00]`: sin ese reinicio, el reloj relativo arrastraría el tiempo transcurrido desde el arranque de la GUI (que puede ser de minutos entre que el usuario configura la entrada y pulsa Ejecutar). El `RunScreen` parsea las líneas para enriquecer la lista de fases del _pipeline_ (`Pipeline: ANÁLISIS …` → fase activa con contador de segundos en vivo, `Pipeline: ANÁLISIS ok` → fase completada con duración total) y la tabla del agente (`[iter NN] -> tool_calls`).

La **cancelación** se propaga al núcleo mediante un `threading.Event` que se pasa como argumento opcional `cancel_event` a `run_pipeline` y `discover_from_url`. El núcleo lo comprueba entre fases, al inicio de cada iteración del bucle del agente y también entre las llamadas a _tools_ dentro de un mismo turno; si está señalizado, levanta `PipelineCancelled`. La GUI usa `cancel_and_abandon()` para _desacoplar_ la pantalla del hilo trabajador: tras pulsar Cancelar, se transita inmediatamente a la pantalla de resultado mientras el hilo huérfano —`daemon`— termina en _background_ la llamada HTTP en curso (no abortable mid-flight con los SDKs síncronos actuales). Los artefactos parciales en disco quedan disponibles desde el primer instante.

La **persistencia de credenciales** se delega en `dotenv.set_key`: cuando el usuario introduce una clave nueva en el campo enmascarado de la pantalla de configuración, la aplicación la inyecta en `os.environ` para la sesión actual y la escribe en el `.env` del directorio de trabajo (creándolo si no existe). El fichero `.env` está excluido del control de versiones por `.gitignore`.

La **visualización del modelo** en la pestaña por defecto del resultado se implementa en `gui/ddl_graph.py`. Un parser por _regex_ extrae del DDL final las tablas (con sus columnas y claves primarias) y las claves foráneas. La selección del _engine_ de Graphviz es **heurística según la topología**: si existe un nodo con más de diez aristas entrantes (típico de la tabla `Users` en aplicaciones reales) o el grafo supera las veinte tablas, se utiliza `sfdp` (_force-directed_), que coloca el _hub_ en el centro y distribuye los demás nodos alrededor; en el resto de casos, `dot` con `rankdir=LR` y `splines=spline` produce un _layout_ jerárquico más limpio. La función `_ensure_graphviz_in_path` localiza el binario en las rutas estándar de Windows (instalador oficial y `winget`) y lo añade al `PATH` del proceso si la variable de entorno no se había refrescado tras la instalación. Si el binario no está disponible, `render_to_png` devuelve `None` y la pestaña ER muestra instrucciones de instalación con un botón "Reintentar" que vuelve a probar sin necesidad de cerrar la GUI; el resto de pestañas funciona con normalidad.

El **visor** del diagrama ER en la `ResultScreen` muestra el PNG dentro de un `tk.Canvas` con _scrollbars_ horizontal y vertical y una barra superior con controles de _zoom_ (`−`, `+`, `100 %`, "Ajustar a ventana") y un botón "Abrir en visor externo" que delega el PNG al visor de imágenes del sistema. El _resize_ de la imagen utiliza `Image.BILINEAR` (no `LANCZOS`) y un _debounce_ de 80 ms para que el _zoom_ sea fluido incluso sobre diagramas grandes (sobre el ER de Habitica, 2 896 × 2 578 píxeles, `LANCZOS` tardaba dos a tres segundos por iteración; `BILINEAR` reduce el coste un orden de magnitud sin pérdida perceptible en un grafo).

La **recuperación de corridas previas** se facilita mediante un enlace discreto "Abrir resultados existentes..." en la pantalla de configuración: el usuario selecciona un directorio `out-*` antiguo, la aplicación valida que contenga al menos el artefacto `04_ddl.sql` y salta directamente a la pantalla de resultado sin re-ejecutar el _pipeline_. Útil para revisar el diagrama ER o exportar a ZIP corridas anteriores sin volver a gastar cuota.

Las **tablas dentro del visor de Markdown** se renderizan como _widgets_ reales (un `tk.Frame` con `grid` de `tk.Label` por celda, envuelto en un `tk.Canvas` con _scrollbar_ horizontal) en lugar de texto alineado. Sin esta solución, el modo `wrap="word"` del `CTkTextbox` rompía las tablas anchas al envolver el contenido de las celdas y destruir la alineación; con la nueva implementación, las tablas anchas se desplazan horizontalmente sin afectar al resto del documento.

La GUI no implementa ninguna lógica de transformación; solamente invoca `run_pipeline(input_path, provider, out_dir, cancel_event)` y `discover_from_url(url, agent_provider, out_dir, cancel_event)`. Cualquier modificación del _pipeline_ o del agente queda automáticamente accesible desde la GUI sin tocar la capa de presentación, lo que materializa el requisito de paridad funcional RF-6.3.

