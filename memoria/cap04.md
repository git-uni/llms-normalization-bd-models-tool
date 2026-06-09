# Capítulo 4. Requisitos del Sistema

Este capítulo proporciona una representación técnica del producto requerido que indica lo que el sistema debe realizar para cumplir los requisitos de usuario del capítulo 3. Su contenido se alinea con el resultado del proceso de *Requirements Analysis Process* descrito en ISO/IEC/IEEE 15288 [3] y se especifica de acuerdo con la norma ISO/IEC/IEEE 29148:2018 [1], aplicando la **ficha esencial completa** a cada requisito atómico, con los atributos exigidos por 29148 §5.2.4 ("Characteristics of individual requirements") y §5.2.5 ("Characteristics of a set of requirements"): identificador único, descripción no ambigua y verificable, fuente trazable al RU del que deriva, prioridad y necesidad declaradas, mecanismo de verificación y dependencias con otros requisitos.

## 4.1 Requisitos funcionales

### 4.1.1 Funciones del sistema

Los requisitos funcionales se han agrupado en siete áreas: gestión de la entrada, *pipeline* de transformación, agente de descubrimiento, herramientas operativas del agente, gestión del proveedor de LLM, interfaces de usuario y gestión de errores y diagnóstico. Cada RF de primer nivel se descompone en sub-requisitos atómicos que detallan la capacidad correspondiente, especificados con la ficha completa.

#### RF-1. Gestión de la entrada (traza: RU-1)

El sistema debe aceptar tres modos de entrada y unificarlos internamente en una representación común antes de invocar al LLM.

##### RF-1.1 Lectura de archivo único

El sistema debe aceptar como entrada la ruta a un único archivo de texto y leer su contenido íntegro como evidencia del modelo documental, anteponiendo a su contenido una marca que identifique su ruta original.

| Atributo | Valor |
|---|---|
| Fuente | RU-1.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución de `python -m normalizer data/spruce/keys.js`; el artefacto `01_input.txt` reproduce el contenido del archivo con la marca de origen. |
| Dependencias | RF-2.1. |

##### RF-1.2 Lectura de directorio curado

El sistema debe aceptar como entrada la ruta a un directorio, leer todos los archivos de texto contenidos en su primer nivel (no recursivo) y concatenarlos en un único documento de evidencia, anteponiendo a cada archivo una marca que identifique su ruta original.

| Atributo | Valor |
|---|---|
| Fuente | RU-1.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución de `python -m normalizer data/spruce-difuso/`; el artefacto `01_input.txt` contiene los ocho archivos concatenados con sus marcas de origen. |
| Dependencias | RF-1.4, RF-1.5, RF-2.1. |

##### RF-1.3 Lectura desde repositorio remoto

El sistema debe aceptar como entrada la URL de un repositorio Git público, clonarlo en un directorio de caché local y delegar en el subsistema de agentes (RF-3) la selección de los archivos relevantes.

| Atributo | Valor |
|---|---|
| Fuente | RU-1.3. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución sobre la URL pública del repositorio Spruce; el directorio `.cache/repos/<hash>/` contiene el repositorio clonado y `00_discovery/evidence/` la selección del agente. |
| Dependencias | RF-3, RF-4.1. |

##### RF-1.4 Validación de la entrada

El sistema debe verificar que la entrada existe y es accesible antes de invocar al *pipeline*, y debe informar al usuario con un mensaje claro en caso contrario, sin lanzar excepciones no controladas.

| Atributo | Valor |
|---|---|
| Fuente | RU-1, RNF-3.2 (usabilidad de mensajes de error). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Invocación de la CLI con una ruta inexistente; comprobación de un código de salida distinto de cero y un mensaje legible por la salida de error estándar. |
| Dependencias | — |

##### RF-1.5 Filtrado de archivos no textuales

El sistema debe descartar los archivos no textuales contenidos en el directorio de entrada (imágenes, binarios compilados, etc.) y los archivos cuyo tamaño supere un umbral configurable, para evitar saturar el contexto del LLM. El descarte se registra en la salida de error estándar como entrada de *log* informativa, con el nombre del archivo descartado y el motivo.

| Atributo | Valor |
|---|---|
| Fuente | RU-1.2, RNF-1.2 (consumo del contexto del LLM). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Inclusión en el directorio de prueba de un fichero binario y un fichero de gran tamaño; comprobación de que ambos se omiten del artefacto `01_input.txt` y de que aparece la traza correspondiente. |
| Dependencias | RNF-1.2. |

#### RF-2. *Pipeline* de transformación (traza: RU-2, RU-3, RU-7, RU-8)

El sistema debe estructurar la transformación en una secuencia de fases independientes, cada una con una entrada y una salida bien definidas, y persistir las salidas intermedias en disco.

##### RF-2.1 Fase de lectura

El sistema debe producir un artefacto de entrada agregada (`01_input.txt`) que contenga todos los fragmentos de evidencia que se pasarán al LLM, normalizados y marcados por su origen.

| Atributo | Valor |
|---|---|
| Fuente | RU-7.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución end-to-end; presencia del artefacto `01_input.txt` en el directorio de salida. |
| Dependencias | RF-1. |

##### RF-2.2 Fase de análisis del modelo documental

El sistema debe invocar al LLM con la entrada agregada y un *prompt* de análisis, y producir un artefacto en formato Markdown (`02_analysis.md`) que describa las entidades, atributos y relaciones detectadas, así como una traza de las evidencias en que se apoya cada decisión.

| Atributo | Valor |
|---|---|
| Fuente | RU-2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución end-to-end sobre `data/spruce/`; el artefacto `02_analysis.md` recoge las cuatro entidades de referencia con citas explícitas de evidencia. |
| Dependencias | RF-2.1, RF-2.7. |

##### RF-2.3 Fase de diseño relacional

El sistema debe invocar al LLM con el análisis previo y un *prompt* de diseño que solicite la propuesta de un modelo relacional normalizado. El *prompt* debe incluir la regla de reconciliación de atributos redundantes para evitar duplicidades de claves foráneas en el resultado.

| Atributo | Valor |
|---|---|
| Fuente | RU-3.1, RU-3.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución sobre `data/spruce-difuso/`; el artefacto `03_design.md` no contiene dos columnas en la misma tabla que referencien al mismo registro de otra tabla. |
| Dependencias | RF-2.2. |

##### RF-2.4 Fase de generación de DDL Oracle

El sistema debe invocar al LLM con el diseño relacional previo y un *prompt* de generación que produzca sentencias DDL compatibles con Oracle (`CREATE TABLE`, restricciones de clave primaria y foránea, tipos de datos Oracle).

| Atributo | Valor |
|---|---|
| Fuente | RU-3.3. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección del artefacto `04_ddl.sql`: parseo correcto con un analizador SQL; presencia de `CREATE TABLE`, `PRIMARY KEY` y `FOREIGN KEY` en las cantidades esperadas. |
| Dependencias | RF-2.3. |

##### RF-2.5 Persistencia de artefactos intermedios

El sistema debe escribir cada uno de los cuatro artefactos (`01_input`, `02_analysis`, `03_design`, `04_ddl`) en un directorio de salida configurable, de modo que el usuario pueda inspeccionarlos y compararlos posteriormente.

| Atributo | Valor |
|---|---|
| Fuente | RU-7.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución end-to-end; los cuatro artefactos están presentes en el directorio `--out-dir`. |
| Dependencias | — |

##### RF-2.6 Aislamiento entre ejecuciones

El sistema debe permitir especificar un directorio de salida distinto en cada invocación, y por defecto no debe asumir que un mismo directorio se reutiliza entre ejecuciones distintas.

| Atributo | Valor |
|---|---|
| Fuente | RU-7.2. |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Dos ejecuciones consecutivas sobre datasets distintos con `--out-dir` distintos no comparten ni colisionan artefactos. |
| Dependencias | — |

##### RF-2.7 Externalización de *prompts*

Los *prompts* utilizados en cada fase del *pipeline* deben residir en archivos independientes (formato Markdown), no en cadenas literales dentro del código fuente, para facilitar su edición, versionado y reutilización entre proveedores.

| Atributo | Valor |
|---|---|
| Fuente | Decisión arquitectónica del capítulo 5 (§5.1.4). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Inspección de `normalizer/prompts/`: existencia de los archivos `analyze.md`, `design.md`, `ddl.md` y `discovery_system.md`, cargados por el código sin contenido *prompt* embebido. |
| Dependencias | — |

#### RF-3. Agente de descubrimiento sobre repositorio (traza: RU-1.3, RU-5)

Cuando la entrada sea la URL de un repositorio, el sistema debe utilizar un agente para reconstruir el conjunto de archivos relevantes antes de invocar el *pipeline*.

##### RF-3.1 Exploración de la estructura del repositorio

El agente debe ser capaz de listar archivos y directorios del repositorio clonado, así como de abrir y leer aquellos que considere candidatos a contener evidencia del modelo documental.

| Atributo | Valor |
|---|---|
| Fuente | RU-5.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de la traza `00_discovery/discovery.md`: presencia de invocaciones a las herramientas `list_dir` y `read_file`. |
| Dependencias | RF-4. |

##### RF-3.2 Selección de archivos relevantes

El agente debe seleccionar el subconjunto de archivos cuya evidencia sea suficiente para reconstruir el modelo documental, priorizando *schemas* explícitos cuando existan y, en su defecto, archivos donde se realicen operaciones de lectura / escritura contra la base de datos.

| Atributo | Valor |
|---|---|
| Fuente | RU-5.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Ejecución sobre la URL pública de Spruce; el agente selecciona los cuatro *schemas* declarativos. |
| Dependencias | RF-4. |

##### RF-3.3 Generación de evidencia agregada

El agente debe entregar al *pipeline* (RF-2) una entrada agregada equivalente a la que produciría la lectura de un directorio curado por un humano (RF-1.2).

| Atributo | Valor |
|---|---|
| Fuente | RU-1.3, RU-5.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Tras el agente, el directorio `00_discovery/evidence/` contiene los archivos seleccionados con sus rutas aplanadas; el *pipeline* arranca sobre ese directorio. |
| Dependencias | RF-1.2. |

##### RF-3.4 Traza de las decisiones del agente

El agente debe registrar, en un artefacto adicional dentro del directorio de salida (`00_discovery/discovery.md`), qué archivos ha examinado, cuáles ha seleccionado y por qué.

| Atributo | Valor |
|---|---|
| Fuente | RU-5.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección del artefacto: tabla `Iter | Tool calls` con las invocaciones y lista de archivos seleccionados con sus justificaciones. |
| Dependencias | — |

##### RF-3.5 Límites operativos del agente

La ejecución del agente debe estar acotada por límites configurables de número de pasos (`max_iters`) y número de archivos seleccionados (`max_files`), abortando la operación con un mensaje claro si se exceden y registrando la causa en la traza.

| Atributo | Valor |
|---|---|
| Fuente | RNF-1.3 (coste). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Configuración artificial de `max_iters=2` sobre un repositorio mediano; comprobación de que la ejecución termina con la marca de "presupuesto agotado" en la traza. |
| Dependencias | RNF-1.3. |

#### RF-4. Herramientas operativas del agente (traza: RU-5)

El agente definido en RF-3 debe disponer de un conjunto acotado de herramientas para interactuar con el repositorio clonado y el directorio de salida. Estas herramientas se exponen al LLM mediante el mecanismo nativo de *function calling* del proveedor.

##### RF-4.1 Herramientas de exploración del repositorio

El sistema debe poner a disposición del agente herramientas para: listar el contenido de un directorio del repositorio clonado; leer el contenido de un archivo concreto; realizar búsquedas textuales por patrón sobre el conjunto de archivos; marcar un archivo como evidencia relevante; y declarar el cierre de la sesión de descubrimiento.

| Atributo | Valor |
|---|---|
| Fuente | RU-5.1, RU-5.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de la traza `00_discovery/discovery.md`: aparición de las cinco herramientas (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`) al menos en uno de los datasets de validación. |
| Dependencias | RF-4.2, RF-4.3, RF-4.4. |

##### RF-4.2 Confinamiento de las herramientas

Las herramientas de acceso al sistema de archivos deben operar exclusivamente dentro del directorio temporal donde se ha clonado el repositorio analizado y dentro del directorio de salida de la ejecución, rechazando cualquier ruta que escape de estos ámbitos.

| Atributo | Valor |
|---|---|
| Fuente | RNF-4.2 (control de efectos de los agentes). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inyección de una invocación sintética con una ruta tipo `../../etc/passwd`; comprobación de que la herramienta devuelve un error estructurado y no accede al archivo. |
| Dependencias | RNF-4.2. |

##### RF-4.3 Validación de los argumentos

Cada herramienta debe validar los argumentos recibidos del LLM antes de ejecutarse, devolviendo al agente un mensaje de error estructurado en caso de argumentos inválidos en lugar de elevar excepciones.

| Atributo | Valor |
|---|---|
| Fuente | RNF-2.2 (fiabilidad). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Inyección de una invocación con argumentos del tipo incorrecto; la herramienta devuelve `ERROR: …` y la ejecución continúa. |
| Dependencias | — |

##### RF-4.4 Definición independiente del proveedor

La descripción de cada herramienta (nombre, parámetros, tipos, descripción para el LLM) debe definirse una sola vez en un formato común (estructura `ToolSpec`), y la abstracción de proveedor (RF-5) debe encargarse de traducirla al formato concreto que cada proveedor de LLM espera para *function calling*.

| Atributo | Valor |
|---|---|
| Fuente | Decisión arquitectónica (§5.1.4). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección del código: ausencia de definiciones de herramientas en `providers/`; presencia de `ALL_TOOLS` en `discovery/tools.py` reutilizable por cualquier proveedor. |
| Dependencias | RF-5.1. |

#### RF-5. Gestión del proveedor de LLM (traza: RU-4)

El sistema debe permitir elegir el proveedor y el modelo de LLM en cada ejecución, sin acoplar el resto del *pipeline* a un proveedor concreto.

##### RF-5.1 Abstracción de proveedor

El sistema debe definir una interfaz uniforme de proveedor de LLM con dos operaciones obligatorias del núcleo: una para generación de texto a partir de un *prompt* (`generate`) y otra para diálogo con herramientas (`chat`). El *pipeline* y el agente deben usar exclusivamente esta interfaz, sin importar SDKs específicos de proveedor. La interfaz expone adicionalmente una operación auxiliar (`list_models`) que la GUI consume para mantener el selector de modelos sincronizado con el catálogo actual del proveedor sin requerir intervención en el código.

| Atributo | Valor |
|---|---|
| Fuente | RU-4.1, RU-4.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `normalizer/pipeline.py` y `normalizer/discovery/agent.py`: ausencia de *imports* de los SDKs `google.genai` o `groq`; uso únicamente del *Protocol* `LLMProvider`. |
| Dependencias | — |

##### RF-5.2 Registro extensible de proveedores

El sistema debe disponer de un registro de proveedores soportados, ampliable mediante el alta de una nueva clase de proveedor sin necesidad de modificar el código del *pipeline*, del agente o de la CLI.

| Atributo | Valor |
|---|---|
| Fuente | RU-4.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `normalizer/providers/__init__.py`: presencia de un diccionario `_REGISTRY` y de una función `build_provider`; comprobación de que añadir un proveedor nuevo requiere solo modificar `providers/`. |
| Dependencias | RF-5.1. |

##### RF-5.3 Selección de proveedor y modelo

El usuario debe poder indicar, en el momento de la invocación, qué proveedor y qué modelo concreto se utilizarán para cada uno de los dos roles (*pipeline* y agente). En ausencia de elección, el sistema debe usar valores por defecto definidos para cada proveedor.

| Atributo | Valor |
|---|---|
| Fuente | RU-4.1, RU-4.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Invocación con `--provider`, `--model` y `--agent-model` arbitrarios; comprobación de que la traza refleja los valores empleados. |
| Dependencias | RF-5.1, RF-5.2. |

##### RF-5.4 Soporte mínimo multiproveedor

El sistema debe incluir, en su versión final, al menos dos implementaciones reales de proveedores (en este trabajo, Google y Groq) para validar la independencia del proveedor.

| Atributo | Valor |
|---|---|
| Fuente | RU-4.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `normalizer/providers/`: presencia de `google.py` y `groq.py`, ambos registrados en `_REGISTRY` y ambos validados sobre al menos un dataset. |
| Dependencias | RF-5.1, RF-5.2. |

##### RF-5.5 Configuración de credenciales

Las credenciales (API keys) de cada proveedor deben leerse de variables de entorno o de un archivo de configuración local no versionado, nunca quedar embebidas (*hardcoded*) en el código fuente.

| Atributo | Valor |
|---|---|
| Fuente | RU-4.3, RNF-4.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Auditoría del repositorio: `grep -r "AIza\|gsk_" .` no devuelve resultados; `.env.example` documenta los nombres de variable; `.env` está en `.gitignore`. |
| Dependencias | RNF-4.1. |

#### RF-6. Interfaces de usuario (traza: RU-6)

El sistema debe ofrecer dos modos de uso adaptados a perfiles distintos.

##### RF-6.1 Interfaz de línea de comandos (CLI)

El sistema debe ofrecer un punto de entrada CLI que acepte, como mínimo, los siguientes parámetros: ruta o URL de entrada, directorio de salida, proveedor de LLM, modelo del *pipeline*, modelo del agente. La CLI debe mostrar al usuario el avance del *pipeline* (qué fase está ejecutándose y cuándo termina cada una) mediante eventos por la salida de error estándar con sello de tiempo relativo.

| Atributo | Valor |
|---|---|
| Fuente | RU-6.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Invocación `python -m normalizer --help` muestra las opciones; ejecución de extremo a extremo emite mensajes `[mm:ss]` por cada fase. |
| Dependencias | — |

##### RF-6.2 Interfaz gráfica de usuario (GUI)

El sistema debe ofrecer una GUI que permita, sin uso de la línea de comandos: seleccionar la fuente de entrada (archivo, directorio o URL); configurar el proveedor, el modelo del *pipeline* y el modelo del agente; lanzar la ejecución y seguir su progreso en tiempo real; visualizar los artefactos intermedios; y exportar el resultado final a un directorio elegido por el usuario.

| Atributo | Valor |
|---|---|
| Fuente | RU-6.2. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Reproducción manual desde la GUI de un caso completo (`data/spruce/`) por un usuario sin conocimiento previo del CLI; comprobación de la presencia de los cuatro artefactos. |
| Dependencias | RF-6.3, RF-6.1. |

##### RF-6.3 Paridad funcional CLI / GUI

Toda funcionalidad expuesta por la GUI debe poder ejecutarse también desde la CLI, para no quedar atada al modo gráfico de uso. En la práctica, la GUI invoca el mismo punto de entrada del núcleo (`run_pipeline` y `discover_from_url`) que utiliza el CLI, sin duplicar lógica.

| Atributo | Valor |
|---|---|
| Fuente | RU-6 (interfaz adecuada al perfil). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección del código: la GUI no implementa lógica de pipeline ni de agente. Comparación de los DDL resultantes para un mismo dataset desde CLI y GUI. |
| Dependencias | RF-6.1, RF-6.2. |

#### RF-7. Gestión de errores y diagnóstico

El sistema debe informar de forma comprensible de cualquier condición de error y permitir el diagnóstico de fallos en el *pipeline*.

##### RF-7.1 Errores del proveedor

Los errores devueltos por el proveedor de LLM (autenticación, cuota agotada, modelo no disponible, salida malformada) deben capturarse y presentarse al usuario con un mensaje que indique la fase del *pipeline* en que se produjeron.

| Atributo | Valor |
|---|---|
| Fuente | RNF-3.2 (usabilidad de mensajes de error). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Invocación con una API key inválida; el mensaje de error identifica la fase ("análisis", "diseño", "DDL", "agente") y la causa. |
| Dependencias | RF-5.5. |

##### RF-7.2 Observabilidad por fases

El sistema debe emitir, por la salida de error estándar, eventos breves con sello de tiempo relativo al arranque del proceso (`[mm:ss]`) en los puntos clave de la ejecución: inicio del CLI, inicio y fin de cada fase del *pipeline*, clonado del repositorio, cada iteración del agente con un resumen compacto de las invocaciones, y los reintentos del proveedor.

| Atributo | Valor |
|---|---|
| Fuente | Necesidad práctica observada durante el desarrollo (depuración de bucles del agente). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Ejecución sobre un dataset; aparición de los eventos `[mm:ss]` esperados en `2> log.txt`. |
| Dependencias | — |

##### RF-7.3 Reanudación parcial

Cuando la ejecución falle en una fase distinta de la primera, el sistema debe conservar los artefactos intermedios producidos hasta ese punto, de modo que un usuario avanzado pueda retomar la ejecución desde el último artefacto válido.

| Atributo | Valor |
|---|---|
| Fuente | RNF-2.2 (fiabilidad). |
| Prioridad | Baja. |
| Necesidad | Should. |
| Verificación | Inducción artificial de un fallo en la fase de DDL (clave inválida); comprobación de que `02_analysis.md` y `03_design.md` siguen presentes en el directorio de salida. |
| Dependencias | RF-2.5. |

### 4.1.2 Modelo de datos del dominio

El sistema razona simultáneamente sobre dos modelos de datos distintos: por una parte, el **modelo conceptual del dominio** —entidades, atributos, claves y relaciones del modelo entidad-relación que la herramienta produce—; por otra, las **estructuras internas neutras** que materializan la interacción con cualquier proveedor de LLM (`Message`, `ToolSpec`, `ToolCall`, `ChatResponse`) y el estado del agente (`DiscoveryState`). El primero es el objeto de salida de la herramienta y se describe en detalle en §5.2.6; el segundo es el lenguaje común con el que el resto del sistema describe la interacción con el LLM y se describe en detalle en §5.2.2 mediante un diagrama de clases. Esta separación es deliberada: el dominio del problema (modelado relacional) es independiente de cómo se realiza la interacción con el LLM.

### 4.1.3 Interfaz de usuario

#### Interfaz de línea de comandos

La CLI sigue las convenciones POSIX: un argumento posicional para la entrada, opciones con doble guion para la configuración y mensaje de ayuda accesible con `--help`. La invocación típica tiene la forma:

```
python -m normalizer <entrada> [--provider NOMBRE] [--model MODELO] [--agent-model MODELO] [--out-dir DIR]
```

El argumento `<entrada>` puede ser una ruta (archivo o directorio) o una URL de repositorio; el sistema lo detecta automáticamente mediante el prefijo (`http://`, `https://`, `git@`). La CLI emite, durante la ejecución, mensajes breves con sello de tiempo relativo al arranque (`[mm:ss]`) indicando el inicio y fin de cada fase del *pipeline* y de cada iteración del agente, así como la ruta del directorio de salida resultante.

#### Interfaz gráfica de usuario

La GUI se articula en torno a una secuencia de tres pantallas guiadas, no a una lista de ventanas inconexas, lo que reduce la carga cognitiva para usuarios no técnicos:

1. **Configuración.** Un único formulario que reúne todos los parámetros de la ejecución: selector de entrada (archivo, directorio o URL) con validación inmediata; combo de proveedor y combos de modelos del *pipeline* y del agente poblados dinámicamente desde el catálogo del proveedor seleccionado (vía `LLMProvider.list_models()`), con el modelo por defecto pre-seleccionado y *fallback* a ese valor si no hay clave configurada; directorio de salida; y un campo enmascarado para la *API key* del proveedor seleccionado que solo se muestra si la variable de entorno correspondiente no está ya definida. Las claves introducidas en la GUI se persisten automáticamente en `.env` (excluido del repositorio por `.gitignore`).
2. **Ejecución y progreso.** Barra de progreso por fase del *pipeline* (Análisis, Diseño, DDL, más Descubrimiento en el modo URL); en el modo URL, tabla viva con las iteraciones del agente y las herramientas invocadas en cada una; panel de *log* con sello `[mm:ss]`; y un botón Cancelar que detiene la ejecución conservando los artefactos producidos hasta ese momento (RF-7.3).
3. **Resultado.** Pestañas independientes con los artefactos producidos: un diagrama ER auto-generado a partir del DDL final (parser por *regex* + Graphviz) como pestaña por defecto, seguido del diseño relacional (`03_design.md`) en Markdown renderizado, el DDL (`04_ddl.sql`) con resaltado de sintaxis SQL, el análisis (`02_analysis.md`) en Markdown y, en el modo URL, la traza de descubrimiento (`00_discovery/discovery.md`). Una barra de acciones inferior permite abrir el directorio de salida en el explorador del sistema, exportar todos los artefactos en un único fichero `.zip` o lanzar una nueva ejecución sin cerrar la aplicación.

La paridad funcional con la CLI se garantiza porque la GUI invoca directamente los mismos puntos de entrada del núcleo (`run_pipeline`, `discover_from_url`) que utiliza el módulo de línea de comandos.

## 4.2 Requisitos no funcionales

Los requisitos no funcionales se organizan en cinco categorías: rendimiento, fiabilidad, usabilidad, seguridad y restricciones de implementación. La categoría de seguridad se inspira en el Nivel 1 de OWASP ASVS y en las buenas prácticas recogidas en la plantilla del TFG.

### 4.2.1 RNF-1. Rendimiento

#### RNF-1.1 Tiempo de respuesta del *pipeline*

Para una entrada de hasta 20 KB de texto y los modelos de tamaño medio considerados por defecto, el *pipeline* completo debe terminar en menos de 5 minutos en condiciones normales de red. El sistema no se considera un sistema de tiempo real: este límite es orientativo y depende de la latencia del proveedor.

| Atributo | Valor |
|---|---|
| Fuente | Expectativa de uso interactivo en GUI; experiencia del autor con tiempos aceptables en entornos de defensa. |
| Prioridad | Media. |
| Necesidad | Should. |
| Verificación | Mediciones puntuales sobre los datasets `data/spruce/` y `data/spruce-difuso/` con cada uno de los dos proveedores soportados; registro en el capítulo 6. |
| Dependencias | — |

#### RNF-1.2 Consumo del contexto del LLM

El sistema debe controlar el tamaño del contexto enviado al LLM en cada fase. Si la entrada agregada o el árbol del repositorio supera un umbral configurable (por defecto, el 80 % del límite de contexto del modelo seleccionado), el sistema debe avisar al usuario antes de invocar al LLM, en lugar de fallar silenciosamente. Para el agente, el árbol filtrado del repositorio se acota explícitamente a 2 000 entradas (~30 K *tokens*) mediante recorrido por anchura (BFS).

| Atributo | Valor |
|---|---|
| Fuente | Frontera observada con Groq sobre repositorios medianos durante la validación experimental (§7). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `build_tree_summary` en `discovery/filesystem.py`: implementación BFS con corte a 2 000 entradas; ejecución sobre Habitica con Groq, comprobación de que el aviso se emite antes de la invocación. |
| Dependencias | RF-1.5. |

#### RNF-1.3 Coste de las ejecuciones con agentes

La ejecución del agente (RF-3) debe estar acotada por un número máximo de iteraciones (`max_iters`) y de archivos seleccionables (`max_files`), configurables por el usuario, para evitar consumos imprevistos de cuota.

| Atributo | Valor |
|---|---|
| Fuente | RU-4 (independencia de proveedor implica no depender de cuotas abundantes). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `discovery/agent.py`: presencia de las constantes `MAX_ITERS=30` y `MAX_FILES=30`, ambas configurables por el llamador. |
| Dependencias | RF-3.5. |

### 4.2.2 RNF-2. Fiabilidad

#### RNF-2.1 Reproducibilidad estructural de las ejecuciones

Dadas la misma entrada, el mismo proveedor, el mismo modelo y los mismos *prompts*, el sistema debe producir resultados estructuralmente equivalentes entre ejecuciones. Las pequeñas variaciones inherentes a la naturaleza estocástica de los LLMs son aceptables; las diferencias sustanciales en el modelo relacional resultante deben analizarse como un fallo del *prompt* o del modelo, no como ruido normal.

| Atributo | Valor |
|---|---|
| Fuente | Casuística observada durante el desarrollo: rango de cobertura inter-*runs* documentado en la traza experimental del proyecto. |
| Prioridad | Media. |
| Necesidad | Should. |
| Verificación | Tres ejecuciones del mismo caso con el mismo modelo; cobertura del DDL frente al diagrama de referencia dentro de una banda de ±10 %. |
| Dependencias | — |

#### RNF-2.2 Robustez ante fallos transitorios del proveedor

Los fallos transitorios del proveedor (*timeouts*, *rate limits*, errores 5xx) deben gestionarse mediante reintentos con espera exponencial respetando, cuando lo proporcione el proveedor, el tiempo de espera sugerido en la cabecera de la respuesta. Tras agotar los reintentos, el sistema debe terminar con un código de error claro y conservar los artefactos intermedios producidos hasta ese punto.

| Atributo | Valor |
|---|---|
| Fuente | Casuística observada con Gemma (códigos 500 / 503 frecuentes) y con Groq (cuota agotada). |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `_call_with_retry` en `providers/google.py` (códigos `{429, 500, 502, 503, 504}`) y en `providers/groq.py` (`RateLimitError`). Inyección de un fallo sintético en una fase intermedia; comprobación de la conservación de los artefactos anteriores. |
| Dependencias | RF-7.3. |

#### RNF-2.3 Validez sintáctica del DDL

El DDL generado en la fase final debe ser sintácticamente válido para Oracle. Si la primera respuesta del LLM no cumple esta condición, el sistema debe reintentar la fase con un *prompt* de corrección antes de devolver el resultado al usuario.

| Atributo | Valor |
|---|---|
| Fuente | RU-3.3. |
| Prioridad | Media. |
| Necesidad | Should. |
| Verificación | Parseo del artefacto `04_ddl.sql` con `sqlparse` para los datasets de referencia. |
| Dependencias | RF-2.4. |

### 4.2.3 RNF-3. Usabilidad

#### RNF-3.1 Documentación de uso

Tanto la CLI como la GUI deben venir acompañadas de documentación que permita a un usuario con conocimientos básicos de Python (CLI) o sin conocimientos técnicos (GUI) ejecutar una transformación de extremo a extremo siguiendo un manual de inicio rápido.

| Atributo | Valor |
|---|---|
| Fuente | RU-6 (interfaz adecuada al perfil). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Inspección del capítulo 7 ("Manuales") de esta memoria. |
| Dependencias | — |

#### RNF-3.2 Mensajes de error orientados al usuario

Los mensajes de error mostrados al usuario deben describir la causa probable y la acción recomendada, no limitarse a volcar la traza de excepciones.

| Atributo | Valor |
|---|---|
| Fuente | Buenas prácticas de UX. |
| Prioridad | Media. |
| Necesidad | Should. |
| Verificación | Inducción artificial de cuatro fallos representativos (entrada inexistente, API key inválida, cuota agotada, modelo no disponible) y verificación de que el mensaje resultante incluye causa + acción. |
| Dependencias | RF-7.1. |

#### RNF-3.3 Comprensibilidad de los artefactos intermedios

Los artefactos producidos por el *pipeline* deben ser legibles directamente por un humano (Markdown para análisis y diseño, SQL plano para el DDL), sin requerir herramientas adicionales para inspeccionarlos.

| Atributo | Valor |
|---|---|
| Fuente | RU-7.1. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de los artefactos producidos sobre `data/spruce/`: `02_analysis.md` y `03_design.md` se renderizan correctamente; `04_ddl.sql` se abre como texto plano. |
| Dependencias | RF-2.5. |

### 4.2.4 RNF-4. Seguridad

#### RNF-4.1 No *hardcoding* de credenciales

Ninguna API key, *token* o secreto debe aparecer en el código fuente ni en archivos versionados del repositorio. Las credenciales deben proporcionarse mediante variables de entorno o archivos `.env` locales no versionados.

| Atributo | Valor |
|---|---|
| Fuente | OWASP ASVS Nivel 1 §V2.10. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Auditoría con `git log -p | grep -i "api[_-]key"`; ausencia de coincidencias. Presencia de `.env` en `.gitignore`. |
| Dependencias | — |

#### RNF-4.2 Control de efectos del agente

El agente no debe poder ejecutar operaciones con efectos persistentes fuera del directorio de salida y del directorio temporal de clonado del repositorio sin autorización explícita del usuario. En particular, no debe poder modificar el repositorio analizado ni acceder a archivos fuera del ámbito declarado.

| Atributo | Valor |
|---|---|
| Fuente | Buenas prácticas de aislamiento de agentes LLM. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección de `resolve_within` en `discovery/filesystem.py`: rechazo activo de rutas que escapen del repositorio o del directorio de salida. |
| Dependencias | RF-4.2. |

#### RNF-4.3 Higiene del código

El código del repositorio debe poder pasar análisis automáticos de dependencias vulnerables (SCA) y de errores de seguridad (SAST), sin alertas críticas pendientes en el momento de la entrega.

| Atributo | Valor |
|---|---|
| Fuente | OWASP ASVS Nivel 1; recomendación de la plantilla. |
| Prioridad | Media. |
| Necesidad | Should. |
| Verificación | Activación del análisis automático de seguridad de GitHub sobre el repositorio público del proyecto. |
| Dependencias | — |

#### RNF-4.4 Privacidad de la entrada del usuario

El sistema debe informar al usuario de que el contenido de la entrada (archivos, fragmentos del repositorio) se envía a un proveedor de LLM externo, y por tanto no debe utilizarse con código fuente o esquemas confidenciales que el usuario no esté autorizado a compartir con dicho proveedor.

| Atributo | Valor |
|---|---|
| Fuente | RNF-4.1 (privacidad como complemento a no *hardcoding*). |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Inclusión de la advertencia correspondiente en el manual de usuario (capítulo 7). |
| Dependencias | — |

### 4.2.5 RNF-5. Restricciones de implementación

#### RNF-5.1 Lenguaje de implementación

La herramienta se implementa en Python 3.11 o superior, por razones de ecosistema (disponibilidad de los SDKs oficiales de los proveedores de LLM y de las librerías de soporte: `google-genai`, `groq`, `click`, `python-dotenv`, `customtkinter`).

| Atributo | Valor |
|---|---|
| Fuente | Disponibilidad de SDKs y experiencia del autor. |
| Prioridad | Alta. |
| Necesidad | Must. |
| Verificación | Inspección del `pyproject.toml`: `requires-python = ">=3.11"`. |
| Dependencias | — |

#### RNF-5.2 Compatibilidad de salida

El DDL generado debe ser compatible con Oracle Database. La versión mínima objetivo del DDL es Oracle 23ai, ya que el sistema emite columnas de tipo `BOOLEAN` de forma nativa. Para entornos Oracle <23 sería necesario un mapeo posterior a `NUMBER(1)` o `CHAR(1)`, que se documenta como ampliación en el capítulo 8.

| Atributo | Valor |
|---|---|
| Fuente | RU-3.3, y casuística del entorno *legacy* del autor. |
| Prioridad | Media. |
| Necesidad | Must. |
| Verificación | Parseo del DDL generado contra el dialecto Oracle 23ai con `sqlparse` o equivalente. |
| Dependencias | — |

## 4.3 Plan de pruebas

Este apartado describe la **estrategia general** de pruebas del sistema: tipos, niveles, objetos, grado de automatización y herramientas. El detalle de qué se prueba en cada caso se especifica en el capítulo 5, apartado 5.3 ("Diseño de pruebas").

### 4.3.1 Estrategia

El sistema combina dos clases de componentes con propiedades muy distintas de cara a las pruebas. Por un lado, una **parte determinista** —lectura de la entrada, persistencia de artefactos, despacho de herramientas del agente, traducción entre el formato neutro y los SDK de cada proveedor, control de presupuestos y reintentos— cuyo comportamiento puede verificarse de forma mecánica. Por otro, una **parte probabilística** —las decisiones del LLM en cada fase del *pipeline* y en cada turno del agente— cuyo resultado correcto no es objetivamente definible y, por tanto, se valida cualitativamente por comparación con un modelo de referencia elaborado por un experto humano.

La estrategia de pruebas aborda ambas clases en paralelo, **sin reducir una a la otra**:

- La parte determinista se verifica mediante una pirámide clásica de pruebas (unitarias, integración, sistema) con un alto grado de automatización.
- La parte probabilística se valida mediante un conjunto de **pruebas de aceptación cualitativas** sobre un banco de *datasets* de referencia, midiendo la cobertura del modelo relacional generado frente al modelo objetivo y observando la varianza entre ejecuciones y entre modelos.

Esta separación es deliberada: la calidad del software (lo determinista) se mide con métricas binarias (pasa / falla), mientras que la calidad del resultado (lo probabilístico) se mide con métricas continuas de cobertura y de coherencia estructural.

### 4.3.2 Tipos y niveles de prueba

| Nivel | Tipo | Caja | Objetivo |
|---|---|---|---|
| Unitario | Funcional | Blanca | Verificar cada función o clase aislada de la parte determinista. |
| Integración | Funcional | Negra (con dobles de prueba para el LLM) | Comprobar la cooperación entre subsistemas sin depender de la API real del proveedor. |
| Sistema | Funcional | Negra | Ejecutar la herramienta de extremo a extremo y comprobar la estructura de los artefactos producidos. |
| Aceptación | Cualitativa | Negra | Comparar el modelo relacional generado con el modelo de referencia para cada *dataset*. |

Quedan **fuera del alcance** las pruebas de carga y de rendimiento sostenido: el sistema no se concibe como un servicio de producción multiusuario, por lo que sus requisitos de rendimiento (RNF-1) se cubren con mediciones puntuales durante la validación de sistema.

### 4.3.3 Objetos de la prueba

La estrategia se aplica a los siguientes subsistemas, identificables a partir de la arquitectura descrita en el capítulo 5:

- **Lectura y normalización de la entrada** (modos archivo, directorio y URL).
- ***Pipeline* lineal** de cuatro fases (lectura, análisis, diseño relacional, generación de DDL).
- **Agente de descubrimiento** sobre repositorios remotos.
- **Herramientas operativas** invocables por el agente (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`).
- **Abstracción de proveedor LLM** y sus implementaciones concretas (Google, Groq).
- **Interfaces de usuario** (CLI y GUI), incluyendo paridad funcional entre ambas.

Para cada uno de estos subsistemas, el apartado 5.3 detalla las invariantes y los criterios de aceptación que las pruebas deben verificar.

### 4.3.4 Grado de automatización

| Categoría | Grado | Justificación |
|---|---|---|
| Unitarias e integración | Plenamente automatizadas | Ejecución desacoplada del LLM mediante dobles de prueba; coste por ejecución despreciable. |
| Sistema | Semiautomatizadas | Lanzamiento automatizado con un proveedor simulado para el flujo de integración continua; ejecuciones con proveedor real fuera de CI por motivos de cuota. |
| Aceptación cualitativa | Manuales asistidas | La comparación con el modelo de referencia requiere juicio humano; se apoya en *checklists* versionadas que reducen la subjetividad y permiten reproducir la evaluación. |

La automatización persigue dos objetivos: garantizar la regresión de la parte determinista en cada cambio del código y aislar la evaluación del modelo del proveedor de LLM concreto, de modo que el *pipeline* de integración continua no se vea afectado por cuotas, latencias ni costes externos.

### 4.3.5 Herramientas

- **`pytest`** como armazón de pruebas unitarias, de integración y de sistema.
- **Dobles de prueba (`MockProvider`)** que implementan la interfaz `LLMProvider` y devuelven respuestas grabadas previamente, lo que permite ejercitar el *pipeline* y el agente de forma determinista.
- **Ficheros de respuesta del SDK** versionados como *fixtures* JSON, capturados a partir de invocaciones reales y reutilizados en las pruebas de los adaptadores.
- **`sqlparse`** para verificar la validez sintáctica del DDL Oracle generado (RNF-2.3).
- **Contenedor de Oracle Database (Express Edition)** opcional para una validación de ejecución del DDL más exhaustiva en un *pipeline* extendido.
- **GitHub Actions** como infraestructura de integración continua, encargada de ejecutar los niveles automatizados en cada *commit* y los niveles semiautomatizados de forma programada.
- ***Checklists* en YAML** versionadas en `tests/baseline/<dataset>.yaml` que enumeran las entidades, claves y relaciones esperadas para cada *dataset* de referencia, y un *script* auxiliar que produce el informe de cobertura por modelo y *dataset* utilizado en la sección 5.3.

Esta combinación de herramientas se traduce en un flujo de pruebas ejecutable, repetible y suficientemente independiente del proveedor de LLM utilizado en la ejecución real.
