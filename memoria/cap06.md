# Capítulo 6. Implementación

Este capítulo documenta la implementación de la herramienta, partiendo del diseño descrito en el capítulo 5. Se centra en la estructura organizativa del código y en la implementación del plan de pruebas, sin sustituir al propio código fuente, que se entrega como anexo conforme a la recomendación de la plantilla.

## 6.1 Estructura de la aplicación

### 6.1.1 Organización del repositorio

El repositorio del proyecto se organiza alrededor de un único paquete Python (`normalizer`) más los directorios auxiliares de datos, documentación y configuración. Las responsabilidades de cada módulo se detallaron en §5.2.1; aquí se enumera la disposición física para situar al lector frente al árbol real.

```
normalizer/
├── __init__.py
├── __main__.py             # python -m normalizer → cli.main
├── _log.py                 # log(msg) por stderr con sello [mm:ss]
├── cli.py                  # CLI Click: --provider, --model, --agent-model, --out-dir
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
│       ├── markdown_view.py  # Renderizado de Markdown con tags
│       └── sql_view.py       # Resaltado de SQL con pygments
├── pipeline.py             # run_pipeline + _read_input
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
    ├── base.py             # Protocol LLMProvider + dataclasses neutras
    ├── google.py           # GoogleProvider + _call_with_retry (429+5xx)
    └── groq.py             # GroqProvider + _call_with_retry (429)

data/
├── spruce/                 # 4 schemas Mongoose (caso de control)
└── spruce-difuso/          # 8 archivos sin schemas declarativos (caso realista)
```

Junto al paquete y los datos conviven directorios auxiliares: `.cache/repos/` donde el agente almacena los repositorios clonados; `out-*/` con los artefactos de cada ejecución (ignorados por Git); `memoria/` con los borradores y el documento de memoria; y `notes/` con los documentos vivos y los registros de sesión que sirven de soporte a este capítulo y al capítulo 2.

### 6.1.2 Dependencias del proyecto

El archivo `pyproject.toml` declara las dependencias mínimas del paquete. Se ha optado por un conjunto deliberadamente reducido, alineado con el principio de "*no magic*" defendido en §3.3.2: cada dependencia tiene una justificación clara y se utiliza una única biblioteca por responsabilidad.

| Dependencia | Versión mínima | Responsabilidad |
|---|---|---|
| `google-genai` | ≥ 1.0.0 | SDK oficial del proveedor Google Gemini. Utilizada únicamente por `providers/google.py`. |
| `groq` | ≥ 0.11.0 | SDK oficial de Groq (API OpenAI-compatible). Utilizada únicamente por `providers/groq.py`. |
| `click` | ≥ 8.1.0 | *Framework* de CLI. Provee el *parser* de argumentos y la generación de ayuda (`--help`). |
| `python-dotenv` | ≥ 1.0.0 | Carga del fichero `.env` para las credenciales (`GOOGLE_API_KEY`, `GROQ_API_KEY`). |
| `customtkinter` | ≥ 5.2.0 | *Toolkit* gráfico de la GUI (§5.2.7). Dependencia opcional, agrupada en el extra `[gui]`. |
| `pygments` | ≥ 2.0 | Tokenización de SQL para el resaltado de sintaxis en la pestaña DDL del resultado. Dependencia opcional `[gui]`. |
| `graphviz` | ≥ 0.20 | *Wrapper* Python sobre el binario Graphviz. Genera el diagrama ER auto-derivado del DDL final. Dependencia opcional `[gui]`; requiere además el binario Graphviz instalado en el sistema (`winget install Graphviz.Graphviz` / `brew install graphviz` / `apt install graphviz`). Si falta, la pestaña ER muestra instrucciones de instalación sin afectar al resto de pestañas. |
| `Pillow` | ≥ 10.0 | Carga del PNG del diagrama ER para mostrarlo en la GUI. Dependencia opcional `[gui]`. |

Las dependencias del extra `[gui]` se instalan con `pip install -e .[gui]`. El CLI (`python -m normalizer`) funciona sin ellas, lo que permite a un usuario que solo quiera usar la herramienta desde la línea de comandos evitar la instalación del *toolkit* gráfico y de las librerías de visualización.

El requisito de versión de Python (`requires-python = ">=3.11"`) responde a dos necesidades: (i) la disponibilidad de las funcionalidades modernas del lenguaje que utilizan los SDKs (tipos `dict[str, …]` parametrizados sin importación, *match statements*) y (ii) la compatibilidad con las versiones mínimas que cada SDK declara como soportadas.

### 6.1.3 Distribución y ejecución

El paquete se distribuye como un proyecto editable instalable con `pip`. La invocación habitual del CLI es:

```
pip install -e .
python -m normalizer <entrada> [--provider …] [--model …] [--agent-model …] [--out-dir …]
```

El *script* `normalizer` también queda registrado como punto de entrada del *console_script* (`[project.scripts] normalizer = "normalizer.cli:main"`), de modo que el usuario puede invocar `normalizer <entrada>` directamente desde la terminal. Para la GUI, el punto de entrada es:

```
python -m normalizer.gui
```

### 6.1.4 Aspectos destacables de la implementación

A continuación se subrayan cuatro aspectos cuya implementación encierra decisiones técnicas no obvias y que conviene resaltar en este capítulo conforme a la recomendación de la plantilla de no copiar el código pero sí destacar lo relevante. El código completo se entrega como anexo.

#### Reintentos en `GoogleProvider._call_with_retry`

`providers/google.py` define `_RETRYABLE_CODES = {429, 500, 502, 503, 504}` y un máximo de cuatro reintentos. El motivo de incluir los códigos 5xx, no estrictamente *rate limits*, es empírico: la familia Gemma del *free tier* devuelve códigos 500 y 503 transitorios con cierta frecuencia. La función respeta, cuando lo proporciona, el `retryDelay` que el SDK incluye en la respuesta del 429; en su ausencia utiliza una espera por defecto (`_FALLBACK_RETRY_DELAY_S = 15.0` s) más un *back-off* exponencial. Esta política está alineada con RNF-2.2 y se valida durante las pruebas unitarias del adaptador con respuestas sintéticas.

`GroqProvider._call_with_retry` aplica la misma estructura, pero limitada a `RateLimitError` (HTTP 429), respetando la cabecera `retry-after` cuando está presente. Groq no presenta el patrón de 5xx transitorios observado en Google, lo que justifica la asimetría en la política de reintentos.

#### Construcción del árbol del repositorio en `build_tree_summary`

`discovery/filesystem.py` materializa el árbol que se entrega al agente en su primer mensaje. Tres decisiones se destacan:

- **Recorrido BFS por niveles, no DFS.** Garantiza que, si el corte de entradas se agota, todos los directorios de primer nivel ya han aparecido completos. Una primera implementación DFS hacía invisible directorios *top-level* enteros en repositorios grandes (Habitica con `website/` sin entrar en el árbol).
- **Corte a 2 000 entradas** (~30 K *tokens* en *prompt*). Compromiso entre cobertura del árbol y consumo de contexto. La elección del valor es empírica: con 600 entradas (el valor original) varios *top-level* de Habitica no aparecían; con 4 000 se desbordaba el TPM de los modelos *free* de Groq.
- **Omisión local de sufijos de pruebas** (`.test.js`, `.spec.ts`, etc.) del *dump* del árbol, **no** de la accesibilidad: el agente sigue pudiendo leerlos vía `read_file` o `grep` si los encuentra por otra vía. La omisión sirve únicamente para evitar que las baterías de tests acaparen el corte de entradas.

#### Confinamiento de las herramientas en `resolve_within`

La función `resolve_within(repo_root, rel_path)` resuelve cualquier ruta relativa proporcionada por el agente contra el directorio raíz del repositorio clonado y rechaza con `ValueError` cualquier ruta que escape de ese ámbito. Esta función es el único punto en el que el agente toca el sistema de archivos: todas las herramientas (`list_dir`, `read_file`, `grep`, `select_evidence`) la atraviesan antes de actuar. Concentrar el control en una sola función simplifica la auditoría del cumplimiento de RF-4.2 y RNF-4.2.

#### Despacho de tools en `dispatch`

`discovery/tools.py:dispatch(call, state, max_files)` ramifica por `call.name` hacia los manejadores `_do_list_dir`, `_do_read_file`, `_do_grep` y `_do_select`, mientras que el caso `done` se resuelve directamente dentro de `dispatch` marcando `state.is_done = True` y guardando el `summary` en el estado. Esta uniformidad permite que el bucle del agente (`discover_from_url`) sea agnóstico a las herramientas concretas: se materializa el patrón Command (§5.2.5) con un *Invoker* único y *Concrete­Commands* aislados.

### 6.1.5 Implementación de la interfaz gráfica

La GUI se implementa en `normalizer/gui/`. La capa de presentación (`gui/windows/`) instancia las tres pantallas guiadas descritas en §4.1.3: configuración (entrada + proveedor + credenciales), ejecución con progreso por fases + tabla del agente, y resultado con diagrama ER + artefactos en pestañas. La capa de aplicación (`gui/controller.py`, clase `GuiController`) recibe los eventos de la presentación, valida los argumentos y lanza la ejecución del núcleo en un hilo trabajador independiente del hilo de la interfaz, evitando el bloqueo de la ventana durante las llamadas al LLM.

El **progreso en tiempo real** se materializa mediante el sistema de *callbacks* de `normalizer/_log.py` (descrito en §5.2.7): la GUI registra una función con `register_callback()` antes de arrancar el hilo trabajador, y el hilo de la interfaz consume la cola del `GuiController` con `app.after(...)` (Tkinter no es *thread-safe*, por lo que ningún *widget* puede tocarse desde el hilo trabajador). El `RunScreen` parsea las líneas para enriquecer la barra de progreso por fases (`Pipeline: ANÁLISIS …` → fase activa) y la tabla del agente (`[iter NN] -> tool_calls`).

La **cancelación** se propaga al núcleo mediante un `threading.Event` que se pasa como argumento opcional `cancel_event` a `run_pipeline` y `discover_from_url`. El núcleo lo comprueba entre fases y entre iteraciones del bucle del agente; si está señalizado, levanta `PipelineCancelled` y la GUI captura la excepción para mostrar el estado parcial en la pantalla de resultado.

La **persistencia de credenciales** se delega en `dotenv.set_key`: cuando el usuario introduce una clave nueva en el campo enmascarado de la pantalla de configuración, la aplicación la inyecta en `os.environ` para la sesión actual y la escribe en el `.env` del directorio de trabajo (creándolo si no existe). El fichero `.env` está excluido del control de versiones por `.gitignore`.

La **visualización del modelo** en la pestaña por defecto del resultado se implementa en `gui/ddl_graph.py`. Un parser por *regex* extrae del DDL final las tablas (con sus columnas y claves primarias) y las claves foráneas, monta un grafo Graphviz con un nodo por tabla (estructura HTML interna con encabezado coloreado y filas alineadas a la izquierda) y delega el render a PNG al binario `dot`. Si el binario no está en el `PATH`, la función devuelve `None` y la pestaña ER muestra instrucciones de instalación; el resto de pestañas funciona con normalidad.

La GUI no implementa ninguna lógica de transformación; solamente invoca `run_pipeline(input_path, provider, out_dir, cancel_event)` y `discover_from_url(url, agent_provider, out_dir, cancel_event)`. Cualquier modificación del *pipeline* o del agente queda automáticamente accesible desde la GUI sin tocar la capa de presentación, lo que materializa el requisito de paridad funcional RF-6.3.

## 6.2 Implementación de las pruebas

### 6.2.1 Estado de la validación efectivamente ejecutada

La validación del prototipo se ha materializado fundamentalmente en el nivel de **aceptación cualitativa** descrito en §5.3.3, sobre los *datasets* de referencia identificados en §5.3.4. Las pruebas de los niveles unitario, integración y sistema responden a la planificación del sistema completo y se incluyen en el plan futuro (§8.2, Ampliación C); a la fecha de entrega de este TFG, la herramienta no dispone de una suite de pruebas automatizadas con `pytest`. La razón principal del descope es la misma documentada en el capítulo 2: la inversión de horas exigida por el desarrollo del agente y por la implementación de la GUI ha desplazado la suite automatizada al cierre del proyecto, no al hito de este TFG.

Esto no significa que el sistema no se haya verificado: el banco de pruebas cualitativas se ha ejecutado de forma sistemática sobre los tres *datasets* de cobertura y, de forma adicional, sobre Habitica. Los resultados se resumen en la tabla siguiente.

### 6.2.2 Resultados de la validación cualitativa

La tabla siguiente resume las ejecuciones realizadas para validar el sistema. La métrica de cobertura es entidad-a-entidad contra el modelo UML manual; las celdas vacías indican combinaciones que el *free tier* no permite (por ejemplo, agente Groq sobre Habitica por la frontera de TPM documentada en R-02).

| Dataset | Modo | Proveedor *pipeline* | Modelo *pipeline* | Proveedor agente | Modelo agente | Iter. agente | Archivos sel. | DDL tablas | Cobertura UML |
|---|---|---|---|---|---|---:|---:|---:|---|
| `data/spruce/` | Directorio | Google | gemma-4-31b-it | — | — | — | — | 11 | 11 / 11 |
| `data/spruce/` | Directorio | Groq | llama-3.3-70b-versatile | — | — | — | — | ≈11 | 10 / 11 |
| `data/spruce-difuso/` | Directorio | Google | gemma-4-31b-it | — | — | — | — | 11 | 11 / 11 |
| `data/spruce-difuso/` | Directorio | Groq | llama-3.3-70b-versatile | — | — | — | — | 9 | 7 / 11 |
| Spruce URL pública | URL | Google | gemma-4-31b-it | Google | gemini-3.1-flash-lite | 5 | 4 | 11 | 11 / 11 |
| Habitica URL pública | URL | Google | gemma-4-31b-it | Google | gemini-3.1-flash-lite | 13 | 11 | 31 | cualitativa adicional |
| Habitica URL pública | URL | Groq | llama-3.3-70b-versatile | Groq | qwen/qwen3-32b | — | — | — | no completada — 413 TPM |

Las dos primeras filas muestran que la cobertura del *pipeline* sobre el dataset de control no depende fuertemente del proveedor (Spruce con *schemas* explícitos cae bien para ambos), mientras que la cuarta fila evidencia el *trade-off* identificado como riesgo R-06 (diferencia de cobertura inter-proveedor): sobre el dataset difuso, Groq pierde las familias `keys` / `key_stats` y `analytics` / `analytics_stats`, las menos representadas en el corpus. La quinta fila confirma RU-5.1: el agente recupera los cuatro *schemas* declarativos de Spruce sin intervención manual. La sexta fila documenta el caso end-to-end más rico ejecutado durante el proyecto; la séptima refleja la materialización de R-02.

Tres ejecuciones independientes del agente sobre Habitica con Google (el mismo *prompt*, el mismo modelo) produjeron 5, 11 y 22 archivos seleccionados respectivamente. Este rango se reporta de forma intencional para alinearse con la lección L7 del capítulo 2 (honestidad estadística).

### 6.2.3 Reproducibilidad de los resultados reportados

Los artefactos de las ejecuciones reportadas en §6.2.2 se conservan en el repositorio bajo `out-*` por dataset (`out-spruce/`, `out-difuso/`, `out-spruce-url/`, `out-habitica-2026-06-01/`). La marca temporal y el modelo concreto utilizado en cada ejecución se identifican por la cabecera del propio directorio y por la traza `[mm:ss]` de `_log.py`. Las invocaciones exactas reproducibles son:

```
python -m normalizer data/spruce/ --out-dir out-spruce/
python -m normalizer data/spruce-difuso/ --provider groq --out-dir out-difuso-groq/
python -m normalizer https://github.com/dan-divy/spruce --out-dir out-spruce-url/
python -m normalizer https://github.com/HabitRPG/habitica --out-dir out-habitica/
```

Esta política de reproducibilidad responde a RNF-2.1: los artefactos quedan disponibles para inspección por la dirección académica y por el tribunal, y constituyen la evidencia empírica que sustenta las afirmaciones del capítulo 8 (Conclusiones).
