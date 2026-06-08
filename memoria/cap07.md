# Capítulo 7. Manuales

Este capítulo contiene los manuales necesarios para instalar la herramienta, utilizarla desde sus dos interfaces (CLI y GUI) y extenderla con nuevos proveedores o nuevos *prompts*. Sigue la recomendación de la plantilla de diferenciar claramente el destinatario en cada caso: los manuales 7.1 y 7.4 se dirigen a un perfil técnico (instalación y extensión), mientras que 7.2 y 7.3 se dirigen a usuarios finales con conocimientos básicos de Python (CLI) o sin conocimientos técnicos (GUI).

## 7.1 Manual de instalación

### 7.1.1 Prerrequisitos

Para instalar y ejecutar la herramienta es necesario disponer del siguiente *software* en el sistema operativo del usuario (Windows, macOS o Linux):

- **Python 3.11 o superior**. Se recomienda comprobar la versión con `python --version`.
- **Git**, disponible en el `PATH` del usuario. Necesario para el modo URL: el agente clona el repositorio analizado en una caché local. Se comprueba con `git --version`.
- **Conexión a Internet**. La herramienta envía las solicitudes a los proveedores de LLM por HTTPS y, en el modo URL, descarga el repositorio analizado por el mismo protocolo.

Adicionalmente, el usuario debe disponer de al menos una clave de API válida para uno de los dos proveedores soportados: Google (`GOOGLE_API_KEY`) o Groq (`GROQ_API_KEY`). Ambas se pueden obtener gratuitamente en los portales de los proveedores; el sistema utiliza únicamente las cuotas del *free tier* en su configuración por defecto.

### 7.1.2 Procedimiento de instalación

La instalación se realiza en cuatro pasos, desde una terminal abierta en el directorio donde se desee clonar el proyecto:

1. **Clonar el repositorio del proyecto:**

   ```
   git clone <URL-del-repositorio-del-TFG>
   cd llms-usage-normalization-bd-models
   ```

2. **Crear un entorno virtual** (recomendado) e instalar el paquete en modo editable:

   ```
   python -m venv .venv
   source .venv/bin/activate          # macOS / Linux
   .venv\Scripts\activate.bat         # Windows
   pip install -e .
   ```

3. **Crear el fichero `.env`** en la raíz del proyecto, con al menos una de las dos claves de API:

   ```
   GOOGLE_API_KEY=AIza...
   GROQ_API_KEY=gsk_...
   ```

   El fichero `.env` no debe versionarse: la entrada `.env` está incluida en `.gitignore` desde el inicio del proyecto.

4. **Verificar la instalación:**

   ```
   python -m normalizer --help
   ```

   El comando debe mostrar la ayuda del CLI con los cuatro argumentos opcionales (`--provider`, `--model`, `--agent-model`, `--out-dir`) y el argumento posicional `INPUT_PATH`.

### 7.1.3 Diagnóstico de problemas habituales

| Síntoma | Causa probable | Acción recomendada |
|---|---|---|
| `RuntimeError: Falta GOOGLE_API_KEY` | La variable de entorno no está cargada, el `.env` no se está leyendo o la clave no se ha pegado correctamente. | Verificar que el `.env` está en la raíz del proyecto, no contiene espacios alrededor del `=` y la clave es válida en el portal del proveedor. |
| `git: command not found` | Git no está instalado o no está en el `PATH`. | Instalar Git desde [https://git-scm.com](https://git-scm.com) y reabrir la terminal. |
| `pip install -e .` falla con error de versión | Versión de Python anterior a 3.11. | Instalar Python ≥ 3.11 desde [https://python.org](https://python.org). |
| `customtkinter` no se instala (al arrancar la GUI) | Falta la dependencia opcional para la GUI. | Ejecutar `pip install customtkinter`. |

## 7.2 Manual de usuario CLI

### 7.2.1 Sintaxis básica

La invocación general del CLI es:

```
python -m normalizer <entrada> [--provider NOMBRE] [--model MODELO] [--agent-model MODELO] [--out-dir DIR]
```

| Argumento | Tipo | Valor por defecto | Descripción |
|---|---|---|---|
| `<entrada>` | ruta o URL | — (obligatorio) | Ruta a un archivo, ruta a un directorio o URL pública de un repositorio Git. |
| `--provider` | `google` \| `groq` | `google` | Proveedor de LLM a utilizar. |
| `--model` | texto libre | Por proveedor | Modelo concreto del *pipeline* (texto a texto). |
| `--agent-model` | texto libre | Por proveedor | Modelo concreto del agente. Solo aplica si la entrada es una URL. |
| `--out-dir` | ruta | `out` | Directorio de salida para los artefactos. |

Los valores por defecto para cada proveedor son:

- **Google**: `gemma-4-31b-it` para el *pipeline*, `gemini-3.1-flash-lite` para el agente.
- **Groq**: `llama-3.3-70b-versatile` para el *pipeline*, `qwen/qwen3-32b` para el agente.

### 7.2.2 Tres casos de uso típicos

#### Caso A. Archivo único con *schemas* explícitos

Adecuado cuando el usuario dispone de un único fichero con los *schemas* declarativos del modelo documental (por ejemplo, un *bundle* exportado).

```
python -m normalizer data/spruce/keys.js --out-dir out-keys/
```

Tras la ejecución, el directorio `out-keys/` contiene:

```
out-keys/
├── 01_input.txt           # entrada agregada
├── 02_analysis.md         # análisis del modelo documental
├── 03_design.md           # diseño relacional
└── 04_ddl.sql             # DDL Oracle generado
```

#### Caso B. Directorio con evidencia heterogénea

Adecuado cuando el usuario ha curado manualmente un conjunto de archivos del proyecto que considera suficientes para reconstruir el modelo documental.

```
python -m normalizer data/spruce-difuso/ --provider google --out-dir out-difuso/
```

#### Caso C. URL de un repositorio público

Adecuado cuando el usuario solo dispone de la URL del repositorio y delega en el agente la selección de los archivos relevantes.

```
python -m normalizer https://github.com/dan-divy/spruce --out-dir out-spruce-url/
```

Adicionalmente al *pipeline*, esta invocación genera el directorio `00_discovery/`:

```
out-spruce-url/
├── 00_discovery/
│   ├── tree.txt           # árbol del repo entregado al agente
│   ├── discovery.md       # traza de las iteraciones del agente
│   └── evidence/          # archivos seleccionados por el agente
├── 01_input.txt
├── 02_analysis.md
├── 03_design.md
└── 04_ddl.sql
```

### 7.2.3 Lectura de la salida

Durante la ejecución, la CLI emite por la salida de error estándar (`stderr`) una traza con sello de tiempo relativo al arranque:

```
[00:00] Provider: google | pipeline=gemma-4-31b-it | agent=gemini-3.1-flash-lite | out=out-spruce-url/
[00:00] Descubriendo evidencia desde https://github.com/dan-divy/spruce ...
[00:01] Agente arrancado (max_iters=30, max_files=30, árbol=187 entradas)
[00:14] [iter 01] -> grep('Schema|model'), list_dir(utils/models)
[00:28] [iter 02] -> read_file(utils/models/user.js), read_file(utils/models/room.js)
...
[02:34] Agente done — 4 archivos seleccionados en 5 iter.
[02:34] Evidencia en out-spruce-url/00_discovery/evidence (traza en out-spruce-url/00_discovery/discovery.md)
[02:35] Pipeline: ANÁLISIS ...
[03:01] Pipeline: ANÁLISIS ok (26s)
[03:01] Pipeline: DISEÑO ...
[03:27] Pipeline: DISEÑO ok (26s)
[03:27] Pipeline: DDL ...
[03:48] Pipeline: DDL ok (21s)
[03:48] DDL generado en out-spruce-url/04_ddl.sql
```

### 7.2.4 Solución de problemas frecuentes

| Síntoma | Causa probable | Acción recomendada |
|---|---|---|
| Ejecuciones con cuota agotada (HTTP 429) | Excede el *free tier* del proveedor. | El sistema reintenta automáticamente respetando el `retry-after`. Si persiste, esperar a la recarga de cuota o cambiar de proveedor (`--provider groq` / `--provider google`). |
| El agente devuelve "presupuesto agotado" | Repositorio demasiado grande o *prompt* mal sintonizado. | Inspeccionar `00_discovery/discovery.md` y `00_discovery/tree.txt`. Considerar invocar con un valor mayor de `max_iters` (requiere modificación del código). |
| Cobertura del DDL inferior a la esperada | Varianza del agente (riesgo R-04). | Repetir la ejecución; comparar con la traza turno-a-turno; si la varianza es sistemática, probar otro modelo del agente. |
| HTTP 413 sobre el primer mensaje al LLM | Frontera Groq × tamaño del árbol (riesgo R-02). | Usar `--provider google` para el modo URL sobre repositorios medianos+. |

## 7.3 Manual de usuario GUI

### 7.3.1 Acceso a la interfaz gráfica

Tras la instalación con el extra `[gui]` (`pip install -e .[gui]`), la interfaz gráfica se lanza con:

```
python -m normalizer.gui
```

La ventana principal de la aplicación se organiza en torno a una **secuencia de tres pantallas guiadas**: configuración, ejecución con seguimiento del progreso y resultado.

### 7.3.2 Pantalla 1 — Configuración

La primera pantalla presenta un único formulario con tres bloques:

**Bloque 1 — Entrada.** Un selector segmentado escoge el modo (`Archivo`, `Directorio`, `URL`). Bajo el selector, un campo y un botón "Examinar..." adaptan su comportamiento al modo:

- **Archivo**: el botón abre un selector de archivos del sistema operativo.
- **Directorio**: el botón abre un selector de carpetas del sistema operativo.
- **URL**: el botón se deshabilita y el campo acepta la URL pública del repositorio (`https://…`, `http://…` o `git@…`).

La aplicación valida inmediatamente: el archivo o directorio debe existir, y la URL debe tener uno de los prefijos aceptados. Mientras la validación no pase, el botón "Ejecutar" permanece deshabilitado y un texto explicativo indica el motivo.

**Bloque 2 — LLM y directorio de salida.** Tres controles desplegables más un selector de directorio:

- **Proveedor**: combo con los valores `google` y `groq`. Al cambiar la selección, los dos combos siguientes se prerrellenan automáticamente con los modelos por defecto del proveedor elegido y el bloque de credenciales se ajusta a la nueva variable de entorno relevante.
- **Modelo del *pipeline***: combo editable. Acepta cualquier identificador de modelo válido para el proveedor seleccionado.
- **Modelo del agente**: combo editable. Solo se habilita si la entrada es una URL.
- **Directorio de salida**: por defecto, `out-gui-YYYYMMDD-HHMMSS/` en el directorio de trabajo; se puede cambiar con el botón "Examinar...".

**Bloque 3 — Credenciales del proveedor.** Para el proveedor seleccionado, el formulario muestra un campo de texto enmascarado (`••••`) con la clave de API correspondiente:

- Si la variable de entorno asociada (`GOOGLE_API_KEY` o `GROQ_API_KEY`) ya está definida —ya sea exportada en el *shell* o cargada del fichero `.env`—, el campo aparece relleno con un marcador opaco y deshabilitado. Un botón "Cambiar" lo desbloquea por si el usuario quiere sustituir la clave.
- Si la variable no está definida, el campo aparece vacío y editable. Cuando el usuario introduce una clave y pulsa "Ejecutar", la aplicación la inyecta en el entorno del proceso y la persiste automáticamente en el fichero `.env` del directorio de trabajo (creándolo si no existe) mediante `dotenv.set_key`. El fichero `.env` está excluido del control de versiones por `.gitignore` (véase 7.1.2).

Un botón "Ejecutar" en la esquina inferior derecha pasa a la siguiente pantalla cuando todos los campos obligatorios están completos.

### 7.3.3 Pantalla 2 — Ejecución y progreso

La segunda pantalla muestra el avance del proceso en tiempo real:

- **Barra de progreso por fase**: una secuencia de "*chips*" que se iluminan al arrancar cada fase y se marcan como completados al terminar. En modo URL, las fases son Descubrimiento, Análisis, Diseño y DDL; en modo archivo o directorio, las fases son Análisis, Diseño y DDL.
- **Tabla de iteraciones del agente** (solo en modo URL): tabla viva con dos columnas (`Iter`, `Tool calls`) que se actualiza conforme el agente completa cada iteración del bucle.
- **Panel de *log***: muestra las líneas `[mm:ss] …` emitidas por el núcleo durante la ejecución, con auto-*scroll* al final.
- **Botón "Cancelar"**: señaliza la cancelación cooperativa al núcleo, que aborta entre fases o iteraciones, escribe la traza de descubrimiento con la evidencia parcial y entrega el control a la pantalla de resultado. Los artefactos ya escritos a disco se preservan (RF-7.3).

Al terminar (con éxito, cancelación o error), la pantalla transita automáticamente a la pantalla de resultado.

### 7.3.4 Pantalla 3 — Resultado

La pantalla final muestra un banner con el estado de la ejecución (éxito, cancelación o error con la fase de origen y el mensaje) y un panel con pestañas que presentan los artefactos producidos:

- **Diagrama ER** (pestaña por defecto): diagrama entidad-relación auto-generado a partir del DDL final. El parser interno extrae las tablas (con sus columnas y claves primarias marcadas) y las claves foráneas, construye un grafo Graphviz y lo renderiza como PNG. Si el binario Graphviz no está disponible en el sistema, la pestaña muestra instrucciones de instalación específicas para cada sistema operativo, sin afectar al resto de pestañas.
- **Diseño** (`03_design.md`): Markdown renderizado con encabezados, listas, tablas y resaltado en línea (bold, código, énfasis).
- **DDL** (`04_ddl.sql`): texto con resaltado de sintaxis SQL (palabras clave, literales, comentarios, operadores) gracias a `pygments`.
- **Análisis** (`02_analysis.md`): Markdown renderizado.
- **Descubrimiento** (`00_discovery/discovery.md`, solo en modo URL): Markdown renderizado.

En la barra inferior, tres acciones cierran el ciclo: "Abrir directorio" lanza el explorador del sistema en `out-dir`, "Exportar como ZIP" comprime todos los artefactos en un único fichero seleccionado por el usuario y "Nueva ejecución" vuelve a la pantalla 1 reseteando el estado.

### 7.3.5 Recomendaciones de uso para usuarios no técnicos

- Comenzar con el ejemplo `data/spruce/` para familiarizarse con el flujo antes de aplicar la herramienta a un proyecto propio.
- En el modo URL, repositorios grandes pueden tardar varios minutos: la barra de progreso del agente y la traza turno-a-turno permiten seguir el avance.
- Aunque las credenciales se pueden introducir directamente en la pantalla 1, también se pueden colocar en el fichero `.env` antes de arrancar la herramienta; la aplicación las carga al inicio en ambos casos.
- La privacidad del contenido enviado al proveedor de LLM es responsabilidad del usuario: no utilizar la herramienta con código fuente confidencial sin autorización del titular (RNF-4.4).

## 7.4 Manual técnico

Este apartado describe los puntos de extensión más habituales para usuarios técnicos que deseen ampliar o adaptar la herramienta sin reescribir su núcleo.

### 7.4.1 Añadir un nuevo proveedor de LLM

El procedimiento es directo gracias a la abstracción `LLMProvider` (§5.2.5, patrón *Strategy*):

1. Crear un nuevo módulo `normalizer/providers/<nombre>.py` que defina una clase `<Nombre>Provider` implementando el protocolo `LLMProvider`: las operaciones `generate(prompt) -> str` y `chat(messages, tools) -> ChatResponse`.
2. Implementar los adaptadores privados que traduzcan los tipos neutros (`Message`, `ToolSpec`) al formato del SDK del proveedor, y la conversión inversa de la respuesta a `ChatResponse`.
3. Registrar el nuevo proveedor en `normalizer/providers/__init__.py`:

   ```python
   from normalizer.providers.<nombre> import <Nombre>Provider

   _REGISTRY["<nombre>"] = <Nombre>Provider
   DEFAULT_MODELS["<nombre>"] = "<modelo-por-defecto-pipeline>"
   DEFAULT_AGENT_MODELS["<nombre>"] = "<modelo-por-defecto-agente>"
   ```

4. Recordar definir la variable de entorno de la API key correspondiente y documentarla en el `.env.example`.

`providers/google.py` y `providers/groq.py` son ejemplos completos del procedimiento.

### 7.4.2 Modificar un *prompt*

Los *prompts* del sistema residen en `normalizer/prompts/`, uno por fichero (`analyze.md`, `design.md`, `ddl.md`, `discovery_system.md`). Para modificarlos:

- Los *prompts* de las fases del *pipeline* (`analyze.md`, `design.md`, `ddl.md`) contienen un único *placeholder* (`{evidence}`, `{analysis}`, `{design}` respectivamente). El sistema los formatea con `str.format`, lo que implica que cualquier llave literal (`{`, `}`) que se introduzca en el cuerpo del *prompt* debe duplicarse (`{{`, `}}`).
- El *prompt* de sistema del agente (`discovery_system.md`) **no se formatea**: contiene ejemplos en JavaScript con llaves literales (`new Schema({...})`) que romperían `str.format`.

### 7.4.3 Cambiar los límites del agente

Los presupuestos del agente se controlan mediante constantes en módulos específicos:

- `normalizer/discovery/agent.py`: `MAX_ITERS = 30` (iteraciones máximas por sesión), `MAX_FILES = 30` (archivos seleccionables máximos). También configurables al invocar `discover_from_url` con los *keyword* `max_iters` y `max_files`.
- `normalizer/discovery/tools.py`: `READ_FILE_CAP = 50_000` *bytes* (tamaño máximo de un archivo leído por `read_file`), `GREP_MAX_HITS = 50` (número máximo de coincidencias devueltas por `grep`).
- `normalizer/discovery/filesystem.py`: `MAX_FILE_BYTES` (tamaño máximo de un archivo aceptado en el árbol), `max_entries` por defecto en `build_tree_summary` (`2000`).

Modificar estos valores tiene efectos directos en el consumo del *free tier* de los proveedores: por ejemplo, subir `MAX_ITERS` a 50 puede duplicar el número de peticiones al LLM por sesión, agotando antes la cuota diaria.

### 7.4.4 Añadir un nuevo *dataset*

Los *datasets* de control viven en `data/`. Para añadir uno nuevo:

1. Crear un directorio `data/<nombre>/` con los archivos curados.
2. Documentar el modelo de referencia esperado (por ejemplo, un diagrama UML manual o una lista de entidades) para poder comparar la cobertura cualitativa.
3. Si se planea integrar el *dataset* en la suite de aceptación cualitativa (§5.3.3), añadir un *checklist* en `tests/baseline/<nombre>.yaml` con las entidades, claves y relaciones esperadas.
