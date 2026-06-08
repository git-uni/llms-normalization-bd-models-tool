# GUI explicada

Documento vivo para defender la interfaz gráfica (RU-7.2) ante el tribunal del TFG. Resume el porqué de cada decisión técnica y arquitectónica, mapea archivos a responsabilidades y anticipa preguntas habituales.

---

## 1. Aspecto visual

CustomTkinter es un *toolkit* moderno construido sobre Tkinter que reemplaza los widgets nativos por widgets propios con esquinas redondeadas, *hover effects*, soporte de tema oscuro/claro automático según el sistema operativo y tipografías limpias (Segoe UI en Windows, Helvetica en macOS). Visualmente está más cerca de Discord o de los paneles de configuración modernos que del Tkinter clásico.

Las decisiones de estilo concretas:
- Fondo gris oscuro o gris muy claro según el tema del SO.
- Botones azules con esquinas redondeadas; rojos para acciones destructivas (Cancelar).
- Transiciones suaves al pulsar (*hover state* automático).
- Banner de estado en la pantalla de resultado con código de colores: verde (OK), amarillo (cancelado), rojo (error).

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

**Bloque 2 — LLM y salida.** `CTkOptionMenu` para el proveedor (poblado dinámicamente con `available_providers()`). Al cambiar el proveedor, los dos `CTkComboBox` editables de modelos se prerrellenan con los *defaults* del proveedor (de `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`). El combo del modelo del agente solo se habilita si el modo de entrada es URL. El directorio de salida por defecto es `out-gui-YYYYMMDD-HHMMSS/` para que cada corrida tenga su propio *sandbox*.

**Bloque 3 — Credenciales.** Detecta si `GOOGLE_API_KEY` o `GROQ_API_KEY` están en `os.environ`. Si sí, muestra `••••••••` deshabilitado + botón "Cambiar". Si no, campo editable con `show="*"`. Cuando el usuario introduce una clave y pulsa "Ejecutar", `persist_api_key()` (en `controller.py`) la inyecta en `os.environ` y la persiste en `.env` con `dotenv.set_key()`, que añade o reemplaza la línea correspondiente sin tocar el resto del fichero. Como `.env` está en `.gitignore`, no hay riesgo de *leak* al repositorio.

### Pantalla 2 — Ejecución (`gui/windows/run.py`)

Tres áreas verticales.

**Chips de fase.** Una fila horizontal de etiquetas redondeadas. En modo URL: `Descubrimiento | Análisis | Diseño | DDL`. En modo archivo o directorio: `Análisis | Diseño | DDL`. Cada *chip* cambia de color: gris (pendiente) → azul (activa) → verde (completada). Sustituye a una barra de progreso tradicional porque las fases son discretas y de duración impredecible (una llamada al LLM puede tardar 26s o 3min).

**Tabla de iteraciones del agente** (solo modo URL). `CTkScrollableFrame` con dos columnas (`Iter | Tool calls`). Se rellena en vivo cada vez que llega un evento `[iter NN] -> ...` por el *callback*.

**Panel de *log*.** `CTkTextbox` con auto-*scroll* al final. Recibe todas las líneas `[mm:ss]` — el mismo flujo que se ve por *stderr* en la CLI.

**Botón Cancelar.** Llama a `controller.cancel()`, que señaliza el `threading.Event` que el núcleo comprueba entre fases e iteraciones.

### Pantalla 3 — Resultado (`gui/windows/result.py`)

Tres componentes.

**Banner superior.** Cambia de color según el estado: verde (`finished_ok`, "DDL generado en …"), amarillo (`cancelled`, "Cancelada por el usuario. Los artefactos parciales están disponibles abajo"), rojo (`error_message`, "Error durante {fase}: {mensaje}").

**`CTkTabview` con artefactos.** Hasta cinco pestañas:
1. **Diagrama ER** (pestaña por defecto): generación bajo demanda (detalle en §5).
2. **Diseño**: `03_design.md` renderizado por `MarkdownView`.
3. **DDL**: `04_ddl.sql` con resaltado de sintaxis SQL vía `pygments`.
4. **Análisis**: `02_analysis.md` renderizado por `MarkdownView`.
5. **Descubrimiento**: `00_discovery/discovery.md` (solo en modo URL).

**Barra de acciones inferior.** Tres botones:
- "Abrir directorio": `os.startfile` (Windows) / `open` (mac) / `xdg-open` (linux).
- "Exportar como ZIP": `shutil.make_archive`, comprime el `out_dir` entero.
- "Nueva ejecución": vuelve a pantalla 1 reseteando el estado.

---

## 5. Las cuatro mecánicas técnicas clave

### Mecánica 1 — Captura de progreso vía *callback* (no redirección de *stderr*)

**Problema.** La CLI muestra `[00:14] Pipeline: ANÁLISIS ok (28s)` por *stderr*. La GUI necesita ver lo mismo en vivo en su panel.

**Opciones consideradas.**
- Redirigir `sys.stderr` a un *buffer*: captura todo (incluidos *tracebacks* y *warnings* de los SDKs), obliga a parsear texto.
- ***Callback* estructurado**: seleccionada.

**Implementación.** En `normalizer/_log.py` hay una lista `_callbacks: list[Callable[[str], None]]`. Cuando el código llama `log("Pipeline: ANÁLISIS ...")`, esa línea sale por *stderr* y se reenvía a todos los *callbacks* registrados. La GUI registra uno con `register_callback(self._on_log_line)` antes de lanzar el hilo trabajador y hace `unregister_callback` al terminar. El *callback* solo mete la línea en una `queue.Queue`. **No toca *widgets*** — Tkinter no es *thread-safe*.

### Mecánica 2 — Hilo trabajador + cola + `after()`

**Problema.** Si llamamos a `run_pipeline()` desde el hilo principal de la GUI, la ventana se congela durante minutos. Si lo llamamos desde otro hilo y ese hilo toca *widgets*, Tkinter falla.

**Patrón productor-consumidor.**
1. El hilo principal lanza `threading.Thread(target=self._run, daemon=True)`. Ese hilo ejecuta `discover_from_url()` y `run_pipeline()`.
2. El hilo trabajador encola eventos en una `queue.Queue` compartida.
3. El hilo principal usa `app.after(100, self._poll)` para drenar la cola cada 100 ms con `queue.get_nowait()` y actualizar *widgets*.

`_poll` detecta cuándo termina el hilo (`thread.is_alive() == False`), drena lo que queda y transiciona a la pantalla 3 con `app.after(600, self._finish_transition)` — los 600 ms permiten al usuario ver el último estado antes del cambio de pantalla.

### Mecánica 3 — Cancelación cooperativa

**Problema.** Si el usuario pulsa "Cancelar" durante una llamada a `provider.generate()`, no se puede matar la conexión HTTP a mitad — el SDK no lo soporta. Sí se puede abortar entre fases.

**Implementación.**
1. `GuiController` tiene `self._cancel = threading.Event()`.
2. Lo pasa como argumento opcional `cancel_event` a `run_pipeline()` y `discover_from_url()`.
3. El núcleo lo comprueba entre fases (`pipeline.py`: tras `01_input.txt`, tras `02_analysis.md`, tras `03_design.md`) y entre iteraciones del bucle del agente (`agent.py`).
4. Si el evento está señalizado, se levanta `PipelineCancelled` (definida en `pipeline.py`).
5. `GuiController` captura esa excepción y emite un `CancelledEvent` en la cola.

**Garantía.** Los artefactos ya escritos a disco se preservan. Si se cancela durante el diseño, en disco quedan `01_input.txt` y `02_analysis.md` listos para inspección. Esto materializa el RF-7.3.

### Mecánica 4 — Diagrama ER auto-generado

**Cadena.** `04_ddl.sql` → `parse_ddl()` → `(tables, fks)` → `build_dot()` → cadena DOT → `graphviz.Source(dot).render()` → PNG → `PIL.Image.open()` → `CTkImage` → `CTkLabel`.

**Parser** (`ddl_graph.py`): *regex* sobre `CREATE TABLE name (...)`, división del cuerpo por comas a profundidad 0, distinción entre columnas y *constraints*, extracción de claves primarias y foráneas. Validado sobre Spruce-fácil: 11 tablas y 11 FKs correctas.

**Render**: la lib Python `graphviz` delega al binario `dot` del sistema. Si Graphviz no está instalado, `render_to_png()` devuelve `None` y la pestaña ER muestra instrucciones de instalación por SO. Las demás pestañas siguen funcionando — **fallback gracioso**, no crash.

**Estilo del diagrama.** Cada tabla es un nodo con cabecera azul claro (`#e8f0fe`) y filas con columnas alineadas a la izquierda. Las PKs llevan el prefijo `[PK]`. Las aristas son las FKs con etiqueta `col_origen → col_destino`. Layout `rankdir=LR` con `splines=ortho` (líneas en ángulos rectos).

---

## 6. Mapa de archivos

```
normalizer/gui/
├── __init__.py             — expone main() para conveniencia de importación
├── __main__.py             — punto de entrada: `python -m normalizer.gui`
├── app.py                  — NormalizerApp (CTk root) + navegación entre pantallas
├── state.py                — dataclass GuiState con toda la sesión
├── controller.py           — GuiController + ENV_KEY_BY_PROVIDER + persist_api_key
├── ddl_graph.py            — parser DDL → DOT + render PNG con fallback
├── windows/
│   ├── config.py           — ConfigScreen (pantalla 1)
│   ├── run.py              — RunScreen (pantalla 2)
│   └── result.py           — ResultScreen (pantalla 3)
└── components/
    ├── markdown_view.py    — MarkdownView sobre CTkTextbox con tags Tkinter
    └── sql_view.py         — SqlView sobre CTkTextbox con pygments
```

**Sobre la separación `windows/` vs `components/`:** `windows/` contiene contenedores de pantalla completa con lógica de orquestación (lanzan el *controller*, gestionan navegación). `components/` contiene *widgets* reutilizables que solo saben renderizar un *input*.

**Sobre los *helpers* en `controller.py`** (`ENV_KEY_BY_PROVIDER`, `resolve_default_out_dir`, `persist_api_key`): son utilidades de la capa de aplicación que la pantalla 1 necesita. Quedan en `controller.py` para evitar un módulo aparte con 3 funciones cortas. Aparecen al principio del archivo, antes de `GuiController`, para que se vean al abrir el fichero.

---

## 7. Cambios mínimos al núcleo

| Archivo | Líneas añadidas | Por qué |
|---|---|---|
| `normalizer/_log.py` | ~15 | `register_callback` / `unregister_callback`. CLI sigue idéntica. |
| `normalizer/pipeline.py` | ~12 | `PipelineCancelled` + `_check_cancel()` + parámetro opcional `cancel_event` en `run_pipeline`. |
| `normalizer/discovery/agent.py` | ~10 | Importa `PipelineCancelled`, añade `cancel_event` opcional, comprueba antes de cada iteración del bucle. |

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
5. **Key inválida**: invalidar temporalmente `GOOGLE_API_KEY` en `.env`. Esperar `CTkMessagebox` rojo con la fase y el mensaje.
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
