# Capítulo 6. Diseño

Este capítulo describe el diseño del sistema a partir de los requisitos enunciados en el capítulo 5. Se organiza en tres apartados: la **arquitectura general** (6.1) describe los componentes lógicos del sistema y su despliegue; el **diseño de detalle** (6.2) explica la estructura interna del código, el flujo de ejecución y los patrones de diseño empleados; y el **diseño de pruebas** (6.3) define qué se prueba en cada subsistema, sobre la base del plan de pruebas presentado en §5.3.

## 6.1 Diseño de la arquitectura

### 6.1.1 Visión general

El sistema es una **aplicación de escritorio mono-proceso y local**: cada ejecución es autocontenida, se ejecuta en la máquina del usuario y no expone ningún servicio remoto.

Su núcleo es el ***pipeline***, una **cadena de cuatro fases** —lectura, análisis del modelo documental, diseño relacional y generación de DDL— que transforma la evidencia documental de partida en un esquema relacional normalizado en SQL de Oracle. Cada fase consume el artefacto que produjo la anterior y escribe el suyo en disco: la entrada del *pipeline* es la evidencia agregada (`01_input.txt`), su salida es el DDL final (`04_ddl.sql`), y entre ambas quedan los artefactos intermedios de análisis y diseño.

El sistema admite **tres modos de entrada** que convergen en ese mismo *pipeline*:

- **Fichero único** o **directorio preparado por el usuario**: la evidencia ya está seleccionada de antemano; el sistema la lee directamente (en el modo directorio, todos los ficheros de su primer nivel) y no interviene ningún agente.
- **URL de un repositorio Git público**: la evidencia no está seleccionada. El sistema delega esa selección en un **agente de descubrimiento**, que clona el repositorio y, mediante un conjunto acotado de herramientas (*function calling*), elige los archivos relevantes y se los entrega al *pipeline*.

La interacción con el modelo de lenguaje se canaliza siempre a través de la **abstracción `LLMProvider`**, que aísla al resto del sistema del SDK concreto del proveedor y permite alternar de proveedor (Google, Groq y, en el futuro, otros) sin modificar el núcleo.

Por último, el sistema ofrece **dos interfaces equivalentes** —una de línea de comandos y una gráfica— que comparten el mismo núcleo, con paridad funcional garantizada por diseño.

### 6.1.2 Diagrama de bloques general

La **Figura 6.1** descompone el sistema en cuatro capas. Las flechas continuas son invocaciones en tiempo de ejecución; las punteadas, dependencias transversales (carga de configuración o emisión de traza).

![Figura 6.1. Diagrama de bloques general del sistema](assets/diagramas/bloques.png)

- **Interfaces de usuario.** La CLI (uso desde terminal e integración en *scripts*) y la GUI (uso guiado sin línea de comandos). Solo recogen la entrada e invocan al núcleo; no contienen lógica de transformación.
- **Núcleo de transformación.** El *pipeline* de cuatro fases y el agente de descubrimiento (activo solo en el modo URL).
- **Servicios de soporte:**
  - **`LLMProvider`**: acceso uniforme al modelo de lenguaje (`generate`, `chat` y `list_models`; véase §6.2.2).
  - **Prompts**: un fichero Markdown por fase del *pipeline* y por agente, editables sin tocar el código.
  - **Persistencia**: un directorio de salida por ejecución donde se escriben todos los artefactos.
  - **Observabilidad**: traza por la salida de error con sello `[mm:ss]`, que la GUI también consume.
- **Sistemas externos.** Las APIs de los proveedores de LLM (vía HTTPS, siempre a través de `LLMProvider`) y los repositorios Git públicos (clonado superficial, únicamente desde el agente).

El traspaso de la evidencia que el agente selecciona al *pipeline* se aprecia en la figura de proceso de §6.2.3.

### 6.1.3 Diagrama de despliegue

![Figura 6.2. Diagrama de despliegue](assets/diagramas/despliegue.png)

Todo el cómputo se concentra en la **máquina del usuario**, donde se instala el paquete `normalizer` sobre Python 3.11 o superior. El estado persistente vive en dos directorios: la **caché de repositorios** (`.cache/repos/`), que evita reclonar entre ejecuciones, y el **directorio de salida** (`out-dir/`) de cada ejecución, con sus artefactos. Las credenciales se inyectan por **variables de entorno**, opcionalmente desde un fichero `.env` no versionado.

El sistema solo se comunica con dos servicios externos, ambos por HTTPS y sin modificarlos: el **proveedor de LLM** (Google o Groq; se usa uno por ejecución, que atiende tanto al *pipeline* como al agente) y el **repositorio Git remoto** del que el agente clona el código.

### 6.1.4 Decisiones arquitectónicas

Las decisiones de diseño principales se resumen a continuación; para cada una se indica la alternativa que se consideró y el motivo de la elección. Su traza a los requisitos se recoge en la matriz de §6.1.5.

- **Aplicación mono-proceso y local**, no un servicio multiusuario. *Alternativa considerada:* un servicio web con *backend* compartido; se descartó porque multiplicaría la complejidad (autenticación, sesiones, concurrencia) sin aportar valor a una herramienta de apoyo individual y obligaría a sacar los datos del usuario de su máquina.

- **Estilo *pipes & filters* en el *pipeline*, con un artefacto persistente por fase.** Cada fase consume el fichero que produjo la anterior y escribe el suyo. *Alternativa considerada:* encadenar las fases en memoria en una sola llamada; se descartó porque persistir cada artefacto es lo que permite inspeccionar los resultados intermedios y reanudar tras un fallo.

- **Agente con *function calling* nativo del SDK.** *Alternativa considerada:* un bucle propio que parsee JSON emitido por el modelo, o un *framework* de agentes externo; se descartó el primero por frágil ante desviaciones de formato y el segundo por introducir una dependencia pesada para una funcionalidad acotada.

- **Abstracción de proveedor mediante una interfaz por tipado estructural**, no una jerarquía de herencia. *Alternativa considerada:* una clase base abstracta común; se descartó porque acoplaría cada proveedor a esa jerarquía, mientras que la interfaz permite añadirlos sin tocar el núcleo.

- **Dos modelos por proveedor**, uno para el *pipeline* y otro para el agente. *Alternativa considerada:* un único modelo para todo; se descartó porque el *pipeline* solo necesita generación de texto mientras que el agente exige *function calling*, y separarlos permite combinar un modelo barato para uno y otro más capaz para el otro.

- ***Prompts* externalizados** como ficheros Markdown. *Alternativa considerada:* incrustarlos en el código; se descartó porque iterar sobre los *prompts* es frecuente y así no obliga a modificar Python.

- **Confinamiento del agente** al repositorio clonado y al directorio de salida. *Alternativa considerada:* acceso libre al sistema de archivos; se descartó porque un fallo del modelo podría acceder a información ajena a la tarea.

- **Credenciales fuera del código**, vía variables de entorno o `.env`. *Alternativa considerada:* un fichero de configuración versionado; se descartó por el riesgo de filtrar secretos al repositorio.

- **Aislamiento por directorio de salida** distinto en cada ejecución. *Alternativa considerada:* un directorio fijo reutilizado; se descartó porque haría que ejecuciones distintas interfirieran entre sí.

### 6.1.5 Trazabilidad arquitectura ↔ requisitos

La tabla siguiente resume cómo cada componente o decisión arquitectónica responde a los requisitos enunciados en los capítulos 4 y 5.

| Componente o decisión | Requisitos asociados |
|---|---|
| Interfaces CLI y GUI | RU-6, RF-6 |
| *Pipeline* lineal con artefactos persistentes | RU-2, RU-3, RU-7, RF-2 |
| Agente de descubrimiento | RU-1.3, RU-5, RF-3 |
| Herramientas confinadas del agente | RF-4, RNF-4.2 |
| Abstracción `LLMProvider` | RU-4, RF-5 |
| Subsistema de *prompts* externalizado | RF-2.7 |
| Configuración de credenciales | RU-4.3, RNF-4.1 |
| Aislamiento por directorio de salida | RU-7.2, RF-2.6 |
| Reintentos sobre errores transitorios del proveedor | RNF-2.2 |
| Validación de la entrada y filtrado de archivos no procesables | RF-1.4, RF-1.5, RNF-1.2 |

---

## 6.2 Diseño de detalle

### 6.2.1 Estructura del código

El sistema se implementa como un único **paquete Python llamado `normalizer`** (el nombre del proyecto). La tabla siguiente enumera sus módulos y la responsabilidad de cada uno.

| Módulo o subpaquete | Responsabilidad |
|---|---|
| `normalizer.cli` | Punto de entrada del programa por línea de comandos: parseo de argumentos, validación de la entrada, detección del modo (archivo, directorio o URL), instanciación del proveedor e invocación del agente de descubrimiento o del *pipeline* según el modo. |
| `normalizer.gui` | Punto de entrada gráfico: presentación de las tres pantallas guiadas (configuración, ejecución con progreso, resultado con diagrama ER). Invoca los mismos puntos de entrada del núcleo (`run_pipeline`, `discover_from_url`) que el CLI, sin re-implementar lógica. |
| `normalizer.pipeline` | Implementación de las cuatro fases del *pipeline*. Carga los *prompts*, invoca al proveedor de LLM para análisis, diseño y generación de DDL, y persiste cada artefacto en el directorio de salida. |
| `normalizer.prompts` | Almacén de los *prompts* del sistema en formato Markdown (un fichero por *prompt*) y rutinas de carga. |
| `normalizer.discovery` | Agente de descubrimiento sobre repositorios remotos: bucle de `chat`, gestión del estado (`DiscoveryState`), definición y despacho de las herramientas (`ALL_TOOLS`, `dispatch`), clonado del repositorio y construcción del árbol filtrado. |
| `normalizer.providers` | Abstracción del proveedor de LLM (`LLMProvider`) e implementaciones concretas (`GoogleProvider`, `GroqProvider`), junto con las estructuras de datos neutras (`Message`, `ToolSpec`, `ToolCall`, `ChatResponse`) y la *factory* de instanciación dinámica (`build_provider`). |
| `normalizer._log` | Utilidad de registro estructurado: emite eventos por la salida de error estándar con un sello de tiempo relativo al arranque del proceso (`[mm:ss]`). Expone además un registro de *callbacks* (`register_callback`, `unregister_callback`) que la GUI consume para reinyectar cada línea como evento de su cola, y `reset_clock` para reiniciar el sello al inicio de cada corrida de la GUI sin afectar a la CLI. |

Esta organización refleja las capas de la arquitectura: `cli` y `gui` son la presentación; `pipeline` y `discovery`, el núcleo; y `providers`, `prompts` y `_log`, los servicios de soporte. Los apartados siguientes detallan los aspectos de diseño que la tabla no recoge: el modelo de objetos del proveedor (§6.2.2), el flujo de ejecución (§6.2.3), el bucle del agente (§6.2.4), el diseño de los *prompts* (§6.2.5) y los patrones empleados (§6.2.6).

La **Figura 6.3** representa esa organización como **diagrama de paquetes**: cada paquete agrupado por capa y sus dependencias `«import»` (flechas discontinuas, del cliente al proveedor). El grafo es **acíclico** y estrictamente **descendente** —presentación → núcleo → soporte—; la única arista intra-capa, `discovery → pipeline`, se limita a reutilizar la excepción `PipelineCancelled` y no introduce ciclo. El módulo `_log` (observabilidad) es una **dependencia transversal** de todas las capas: se marca como tal y sus aristas se omiten para no recargar el diagrama. Por el mismo motivo no se dibujan las dependencias externas —los SDK de LLM en `providers`, `git` en `discovery` y los *toolkits* gráficos en `gui`—; conviene destacar que `providers` es el **único** paquete que conoce esos SDK, lo que constituye la evidencia estructural de que la abstracción del proveedor (§6.2.2) cumple su cometido.

![Figura 6.3. Diagrama de paquetes del sistema](assets/diagramas/paquetes.png)

### 6.2.2 Modelo de objetos del subsistema de proveedor

El *pipeline* y el agente interactúan con el LLM a través de un conjunto reducido de tipos neutros, comunes a todos los proveedores, definidos en `providers/base.py`. La **Figura 6.4** muestra su relación.

![Figura 6.4. Diagrama de clases del subsistema de proveedor](assets/diagramas/clases-proveedor.png)

`LLMProvider` es una **interfaz** con tres operaciones: `generate` (texto a texto, para el *pipeline*), `chat` (diálogo con *function calling*, para el agente) y `list_models` (catálogo de modelos, para la GUI). `Message`, `ToolSpec`, `ToolCall` y `ChatResponse` son las estructuras neutras con las que el resto del sistema describe la interacción; cada implementación concreta (`GoogleProvider`, `GroqProvider`) traduce entre ellas y el formato de su SDK (véase el patrón *Adapter* en §6.2.6).

### 6.2.3 Flujo de ejecución según el modo de entrada

Los tres modos de entrada comparten el *pipeline* pero difieren en la fase previa. La **Figura 6.5** muestra el flujo de datos completo: las tres entradas y el artefacto que produce cada fase.

![Figura 6.5. Flujo de datos del proceso completo](assets/diagramas/proceso-general.png)

- **Fichero único / directorio:** la evidencia ya está preparada; el sistema la concatena en `01_input.txt` (anteponiendo a cada fichero una marca con su ruta) y arranca el *pipeline*.
- **URL de repositorio:** el agente de descubrimiento (§6.2.4) selecciona la evidencia y la entrega como un directorio, que el *pipeline* trata igual que en el modo directorio.

La **Figura 6.6** detalla, como diagrama de secuencia, el modo URL —el más completo por incluir el descubrimiento.

![Figura 6.6. Secuencia de una ejecución en modo URL](assets/diagramas/secuencia-url.png)

### 6.2.4 El bucle del agente

El agente de descubrimiento se organiza como un **bucle de turnos** sobre un historial de mensajes: en cada turno envía al proveedor de LLM ese historial junto con las herramientas disponibles; si el modelo responde con invocaciones de herramienta, el sistema las ejecuta y le reinyecta sus resultados; el bucle continúa hasta que el modelo da por terminado el descubrimiento (herramienta `done`) o se agota un presupuesto de iteraciones. La **Figura 6.7** recoge esta lógica y sus salidas.

![Figura 6.7. Bucle del agente de descubrimiento](assets/diagramas/agente-bucle.png)

Dos rasgos de diseño merecen destacarse:

- **Dos representaciones del estado.** El historial de mensajes es la *memoria conversacional* que el modelo necesita para no contradecirse entre turnos; en paralelo, un objeto `DiscoveryState` mantiene la *memoria estructurada* del lado Python (archivos seleccionados, resumen y trazas).
- **Presupuesto acotado.** El límite de iteraciones no es opcional: garantiza que un fallo del modelo —por ejemplo, un bucle de exploración estéril— no derive en un consumo indefinido de cuota.

Las llamadas al proveedor se protegen con reintentos ante fallos transitorios del servicio; el detalle de esa política se describe en el capítulo de implementación (§7.1.4).

### 6.2.5 Diseño del subsistema de *prompts*

Como el sistema delega en el modelo de lenguaje las tres transformaciones del *pipeline* y la selección de evidencia del agente, los *prompts* no son un detalle de implementación sino la pieza de diseño que fija el comportamiento esperado de cada fase. Por eso se externalizan como ficheros Markdown independientes (decisión arquitectónica de §6.1.4, requisito RF-2.7): iterar sobre un *prompt* no obliga a tocar el código, y cada uno puede versionarse y reutilizarse entre proveedores.

El sistema define cuatro *prompts* —tres para el *pipeline* y uno para el agente—. La tabla siguiente resume, para cada uno, el componente que lo consume, la entrada que recibe y el artefacto a cuya producción contribuye.

| *Prompt* | Consumidor | Entrada | Salida |
|---|---|---|---|
| `analyze` | Fase de análisis | Evidencia agregada (`{evidence}`) | `02_analysis.md` |
| `design` | Fase de diseño | Análisis del modelo documental (`{analysis}`) | `03_design.md` |
| `ddl` | Fase de generación | Diseño relacional (`{design}`) | `04_ddl.sql` |
| `discovery_system` | Agente de descubrimiento | — (instrucción de sistema) | Evidencia seleccionada |

Los tres *prompts* del *pipeline* se parametrizan por **sustitución textual**: cada uno declara un hueco (`{evidence}`, `{analysis}`, `{design}`) que el *pipeline* rellena con el artefacto de la fase anterior antes de enviarlo al proveedor. Es la concreción del acoplamiento por ficheros del patrón *Pipes and Filters* (§6.2.6): el contrato entre fases es el texto del artefacto, no una estructura en memoria.

Tres decisiones de diseño gobiernan los *prompts* del *pipeline*:

- **No asumen *schemas* explícitos.** El *prompt* de análisis se redacta en términos de *evidencia heterogénea* —*schemas*, consultas, operaciones de escritura, ejemplos de documento, accesos a campos o comentarios— y no de un formato concreto como Mongoose. Esto es lo que permite que el mismo *pipeline* sirva tanto al caso con *schemas* declarados como al caso difuso, donde el modelo solo se infiere cruzando el código de la aplicación.
- **Reconciliación de redundancias en el diseño.** El *prompt* de diseño incorpora una regla explícita: cuando dos atributos de una misma entidad referencian el mismo registro de otra (por ejemplo, uno guarda el identificador y otro un campo denormalizado del mismo destino), debe conservarse una sola clave foránea canónica. Sin esa regla, la evidencia difusa —donde un mismo dato aparece copiado en varias colecciones— produce tablas con referencias duplicadas.
- **Contrato de salida estricto en el DDL.** El *prompt* de generación exige tipos de Oracle, definición explícita de claves y restricciones, un orden de creación que respete las dependencias de clave foránea y una salida limpia, sin envoltorios Markdown, de modo que el artefacto final sea directamente utilizable.

El *prompt* del agente (`discovery_system`) es de naturaleza distinta: no se parametriza —su contenido incluye fragmentos de código con llaves literales, como `new Schema({...})`, que romperían la sustitución textual— y actúa como instrucción de sistema que rige el bucle de §6.2.4. Su diseño responde a un sesgo observado en los modelos menos capaces, que tienden a cerrar el descubrimiento tras inspeccionar los primeros archivos de un directorio de modelos y a descartar el resto como secundarios. Para contrarrestarlo, el *prompt* fija tres reglas: una **doble pasada** obligatoria —declarativa, buscando *schemas* explícitos con patrones de varias tecnologías; e implícita, revisando el resto del árbol en busca de escrituras o accesos que revelen entidades no declaradas—; el **principio del hermano**, según el cual hallar un modelo en un directorio obliga a examinar los archivos hermanos antes de cerrar; y el **agrupamiento de decisiones** (*batching*), que pide emitir en una sola respuesta las selecciones ya firmes para no malgastar cuota. El filtrado entre evidencia principal y secundaria se delega deliberadamente en el *pipeline* posterior, no en el agente.

### 6.2.6 Patrones de diseño

El diseño se apoya en cinco patrones clásicos: uno arquitectónico (*Pipes and Filters*) y cuatro de diseño de objetos (*Strategy*, *Factory Method*, *Adapter* y *Command*). Cada uno se presenta con la misma estructura: para qué se usa, qué piezas del sistema asumen cada rol y qué se gana con él.

#### Pipes and Filters

Organiza la transformación principal —de la evidencia agregada al DDL Oracle— como una secuencia lineal de fases que se comunican por ficheros en disco, no por memoria compartida.

- **Filter (filtro)** — cada una de las cuatro fases de `normalizer.pipeline`, en orden: lectura de la evidencia (produce `01_input.txt`), análisis del modelo documental (`02_analysis.md`), diseño relacional (`03_design.md`) y generación de DDL Oracle (`04_ddl.sql`).
- **Pipe (tubería)** — los ficheros del directorio de salida: el canal por el que el artefacto de cada fase llega a la siguiente.
- **Data Source** — la lectura de la entrada (en `normalizer.cli` o `normalizer.gui`), que crea el primer artefacto a partir del fichero único, del directorio curado o de la evidencia que entrega el agente.
- **Data Sink** — el artefacto final `04_ddl.sql`, que la interfaz lee para presentárselo al usuario.

Que el canal sea persistente, y no un *buffer* en memoria, es una decisión deliberada (§6.1.4): permite al usuario inspeccionar cada resultado intermedio y reanudar una ejecución interrumpida desde la última fase completada. Y como cada filtro solo conoce el formato de su entrada y su salida, el *prompt* de una fase puede cambiarse sin alterar las demás y cada filtro puede probarse en aislamiento con un doble del proveedor de LLM.

#### Strategy

Aísla la dependencia del proveedor de LLM concreto tras una interfaz uniforme, de modo que ni el *pipeline* ni el agente conocen nunca el SDK que hay debajo. La interfaz es única; la consumen dos contextos, cada uno por una operación distinta de esa misma interfaz.

- **Strategy** — la interfaz `LLMProvider` (`providers/base.py`).
- **ConcreteStrategy** — `GoogleProvider`, `GroqProvider` y cualquier implementación futura.
- **Context (*pipeline*)** — `run_pipeline(...)` (`normalizer/pipeline/pipeline.py`): invoca `generate` en las fases de análisis, diseño y DDL.
- **Context (agente)** — `discover_from_url(...)` (`normalizer/discovery/agent.py`): invoca `chat` en cada turno del bucle.

Un único punto de extensión —la interfaz— da servicio a los dos consumidores: cambiar de proveedor no toca ni el *pipeline* ni el agente.

#### Factory Method con Registry

Resuelve qué proveedor instanciar a partir de su nombre simbólico —el que el usuario indica por línea de comandos o en la GUI—, eligiendo la clase y el modelo por defecto según el rol, *pipeline* o agente, en que vaya a usarse.

- **Creator** — la *factory* `build_provider(name, model, for_agent)` (`providers/__init__.py`).
- **Registry** — el diccionario `_REGISTRY`, que asocia cada nombre simbólico a su clase.
- **Tablas de modelos por defecto** — `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`, que aportan el modelo cuando el usuario no lo fija.
- **Product** — la instancia de la subclase de `LLMProvider`, ya configurada con su modelo.

Añadir un proveedor se reduce a tres pasos —declarar una clase que implemente la interfaz `LLMProvider`, registrarla en `_REGISTRY` y darle sus modelos por defecto— sin tocar el *pipeline*, el agente ni la CLI.

#### Adapter

Traduce entre las estructuras neutras del sistema —`Message`, `ToolSpec`, `ToolCall`, `ChatResponse`, definidas en `providers/base.py` (rol *Target*)— y los tipos propios del SDK de cada proveedor (rol *Adaptee*). La capa neutra es invariante; cada adaptador es privado a su proveedor.

- **Adapter (Google)** — convierte en ambos sentidos contra los tipos de `google-genai` (`Content`, `Part`, `FunctionCall`, `FunctionDeclaration`); reside en `_to_gemini_tools`, `_to_gemini_contents` y la conversión inversa de `GoogleProvider.chat()`.
- **Adapter (Groq)** — convierte en ambos sentidos contra los tipos del SDK `groq`, de formato OpenAI (mensajes con `tool_calls`, identificador por invocación y argumentos como cadena JSON); reside en `_to_groq_messages`, `_to_groq_tools` y la conversión inversa de `GroqProvider.chat()`.

`Message` lleva a la vez los campos `tool_call_id` y `tool_name` porque Google empareja invocación y resultado por nombre de función y el resto de proveedores por identificador; cada adaptador rellena el que su SDK necesita y deja el otro vacío.

#### Command

Representa cada decisión del agente —una invocación de herramienta— como un objeto uniforme que una función de despacho recibe, identifica y ejecuta.

- **Command** — la estructura `ToolCall`: nombre de la herramienta y argumentos ya deserializados.
- **ConcreteCommand** — los manejadores `_do_list_dir`, `_do_read_file`, `_do_grep` y `_do_select`; el caso `done` se resuelve dentro del propio `dispatch`, marcando la finalización en `DiscoveryState`.
- **Invoker** — la función `dispatch(call, state, max_files)`, que enruta cada invocación según `call.name`.
- **Receiver** — el estado `DiscoveryState` y el sistema de archivos confinado al repositorio clonado y al directorio de salida.

Así, las herramientas se añaden o cambian sin tocar el bucle del agente: este ignora qué hace cada manejador y solo gestiona la circulación de invocaciones y resultados.

### 6.2.7 Modelo de datos del dominio

El modelo conceptual sobre el que el sistema razona no es el de las estructuras internas del código, sino el del **modelo entidad-relación** que la herramienta produce: entidades con sus atributos y tipos, claves primarias y claves foráneas, y relaciones entre entidades clasificadas según su cardinalidad y según se hubieran expresado en el modelo documental como referencias por identificador, documentos embebidos o arrays anidados. Este metamodelo conceptual es el lenguaje común entre el análisis del modelo documental (artefacto `02_analysis`), el diseño relacional (artefacto `03_design`) y la generación de DDL (artefacto `04_ddl`). El sistema no representa este metamodelo como estructuras Python persistentes —el LLM lo manipula directamente en formato Markdown / SQL—, lo que mantiene el código del *pipeline* deliberadamente delgado: la única responsabilidad del *pipeline* es orquestar las invocaciones y persistir los artefactos.

### 6.2.8 Arquitectura de la interfaz gráfica

La interfaz gráfica se construye sobre **CustomTkinter** (la justificación de la elección está en §4.3.1) y sigue una separación estricta en tres capas:

- **Presentación** (`normalizer/gui/`): las ventanas y *widgets*; solo conocen los puntos de entrada del núcleo y tipos elementales, sin importar clases del proveedor ni del agente.
- **Aplicación** (`GuiController`): recibe los eventos de la presentación, valida los argumentos, decide el modo de ejecución e invoca el núcleo en un hilo trabajador independiente del de la interfaz.
- **Núcleo:** el mismo que usa la CLI (`run_pipeline`, `discover_from_url`); la GUI no reimplementa lógica de transformación.

De esta separación se siguen tres propiedades —el **progreso en tiempo real** (la GUI consume la misma traza de observabilidad que la CLI), la **cancelación cooperativa** de una ejecución en curso y un **catálogo de modelos dinámico** por proveedor—, cuya mecánica se detalla en el capítulo de implementación (§7.1.5). La consecuencia de fondo es la **paridad funcional CLI / GUI**: cualquier ampliación del núcleo queda disponible en ambas interfaces sin tocar la presentación.

---

## 6.3 Diseño de pruebas

### 6.3.1 Encuadre

La estrategia general de pruebas se define en el plan presentado en §5.3. Esta sección detalla, para cada subsistema identificado en la arquitectura, **qué se prueba** y en qué nivel se prueba, sin descender al detalle de los casos de prueba concretos, que pertenecen al capítulo de implementación.

El diseño contempla los dos ejes anunciados en el plan: la **verificación funcional** mediante una pirámide clásica de pruebas automatizables y la **validación cualitativa** del resultado mediante comparación con un modelo de referencia humano. El primer eje se aplica a la parte determinista del sistema; el segundo, a la parte probabilística introducida por las decisiones del LLM.

### 6.3.2 Objetos de la prueba

La tabla siguiente recoge, para cada subsistema, las propiedades que la verificación debe cubrir.

| Subsistema | Propiedades verificadas |
|---|---|
| Lectura de la entrada | Lectura correcta del fichero único; concatenación correcta del directorio con marcas de origen; descarte silencioso de binarios y de ficheros que excedan el umbral configurado; manejo de entrada inexistente o inaccesible con mensaje claro. |
| *Pipeline* | Generación de los cuatro artefactos esperados en el directorio de salida; carga correcta de los *prompts* desde el subsistema correspondiente; propagación ordenada de errores producidos en cada fase con identificación de la fase fallida. |
| Agente de descubrimiento | Cumplimiento del presupuesto de iteraciones; clonado y reutilización correctos de la caché de repositorios; construcción del árbol filtrado con BFS y *cap* de entradas; despacho correcto de cada herramienta; producción de la traza (`discovery.md`) con la lista de archivos seleccionados y sus justificaciones; salida limpia tanto en el caso normal como en los dos casos anómalos. |
| Herramientas confinadas | Rechazo de rutas que escapen del directorio del repositorio clonado o del directorio de salida; validación de los argumentos recibidos del LLM con mensajes de error estructurados; comportamiento determinista en lecturas, listados y búsquedas. |
| Abstracción del proveedor | Traducción correcta entre el formato neutro y el formato del SDK en ambos sentidos; reintentos con espera exponencial sobre los códigos transitorios definidos; selección correcta de la clase y del modelo por la *factory* en función de los parámetros. |
| Interfaces (CLI y GUI) | Paridad funcional entre ambas; emisión de mensajes de progreso por cada fase; presentación al usuario de los errores del proveedor con indicación de la fase de origen. |

### 6.3.3 Diseño por niveles

Para cada nivel se describe **qué se prueba**; el grado en que cada uno está hoy ejecutado o planificado se detalla en §6.3.5.

#### Pruebas unitarias

Se aplican sobre las piezas deterministas del sistema, en aislamiento. El conjunto incluye, entre otras: la lectura y normalización de la entrada, la construcción del árbol filtrado del repositorio con sus reglas de exclusión, el despacho individual de cada herramienta del agente, el confinamiento del acceso al sistema de archivos (`resolve_within`), la rutina de reintentos sobre códigos sintéticos cubriendo tanto los casos exitosos como los de agotamiento, y los adaptadores de cada proveedor sobre *fixtures* JSON capturadas de respuestas reales del SDK.

#### Pruebas de integración

Comprueban la cooperación de varios subsistemas sustituyendo el LLM por un doble de prueba (`MockProvider`) que cumple la interfaz `LLMProvider` y devuelve respuestas grabadas previamente. Se identifican dos conjuntos relevantes:

- ***Pipeline* end-to-end con doble del LLM*: ejecuta las cuatro fases sobre una entrada conocida y verifica la existencia, el formato y el contenido estructural de cada artefacto.
- *Agente de descubrimiento sobre un repositorio sintético*: el repositorio incluye un *schema* explícito, un *schema* implícito en código de aplicación y un fichero de ruido; la prueba verifica que el agente selecciona los dos primeros y descarta el tercero.

#### Pruebas de sistema

Invocan la CLI sobre los *datasets* de prueba y verifican la estructura externa de los artefactos producidos (existencia, no vacuidad, validez sintáctica del DDL con `sqlparse`) y los códigos de retorno. La GUI se ejercita en este nivel mediante una versión sin interfaz visual de su capa de aplicación (`GuiController`), que invoca exactamente el mismo flujo que la presentación. La evaluación semántica del modelo relacional generado pertenece al nivel siguiente.

#### Pruebas de aceptación cualitativa

Se ejecutan sobre los *datasets* de referencia, cada uno con un modelo de referencia elaborado manualmente por un experto (un diagrama UML del autor del repositorio o del autor del TFG). Para cada *dataset* y modelo de LLM, la prueba calcula y registra:

- **Cobertura de entidades**: cociente entre el número de entidades del modelo de referencia recuperadas en el DDL generado y el número total de entidades del modelo de referencia.
- **Entidades extra**: clasificadas en *legítimas* (sobre-normalización razonable, como la separación en tablas independientes de arrays embebidos) y *ruido* (entidades sin justificación en la entrada).
- **Invariantes estructurales**: toda tabla declara una clave primaria; toda clave foránea referencia una tabla y columna existentes; los atributos reconciliados por la regla de reconciliación de atributos redundantes no producen duplicidades.
- **Reproducibilidad inter-runs**: estabilidad de la cobertura a lo largo de varias ejecuciones con la misma entrada, el mismo proveedor y el mismo modelo, como concreción de RNF-2.1.
- **Cobertura cruzada modelo × dataset**: una tabla que cruza los modelos de LLM disponibles con los *datasets* de referencia y registra la cobertura observada. Esta tabla constituye la evidencia empírica del comportamiento del sistema bajo distintos modelos y permite documentar, sin ocultarlo, que la capacidad del modelo elegido es un factor determinante en la calidad del resultado.

### 6.3.4 Datasets de prueba

El banco de pruebas se compone de los siguientes *datasets*, agrupados según su grado de formalización.

**Datasets de cobertura con *checklist* de referencia:**

- **`data/spruce/`**: caso de control con cuatro *schemas* Mongoose explícitos. El modelo documental está declarado de forma íntegra y la prueba ejercita el *pipeline* aislado del agente de descubrimiento.
- **`data/spruce-difuso/`**: el mismo modelo documental que el anterior pero distribuido implícitamente en código de aplicación (rutas Express, manejadores de socket) sin *schemas* declarados. Ejercita la capacidad del *prompt* de análisis para inferir el modelo a partir de evidencia heterogénea.
- **URL pública del repositorio de Spruce**: el repositorio completo, suministrado únicamente como URL, ejercita el agente de descubrimiento sobre un proyecto pequeño con *schemas* explícitos.

**Datasets de validación cualitativa adicional:**

- **URL pública del repositorio de Habitica**: una aplicación real de tamaño realista, con muchos directorios irrelevantes para el modelo documental. Se utiliza para observar la varianza del agente frente a repositorios grandes y para detectar las fronteras de cuota de los proveedores en condiciones reales. No dispone de un *checklist* formal: la comparación es cualitativa contra una lista no exhaustiva de entidades esperadas elaborada por inspección del código fuente del repositorio.

### 6.3.5 Grado de automatización y herramientas

El diseño contempla dos regímenes de ejecución muy distintos. Las pruebas de **aceptación cualitativa** se realizan de forma **manual asistida** y son las que se han ejecutado efectivamente para validar el prototipo (§7.2): un procedimiento auxiliar lanza la herramienta sobre cada *dataset* con cada modelo de LLM disponible, recoge los artefactos producidos, los compara contra la lista de entidades de referencia del *dataset* y registra el informe cruzado modelo × *dataset*. Los niveles **unitario, integración y sistema** descritos en §6.3.3 están diseñados para una ejecución plenamente automatizada y desacoplada del LLM mediante el doble de prueba; su materialización como suite ejecutable constituye la **Ampliación C** del capítulo 9 —y su integración continua, la Ampliación D—, no una capacidad ya disponible a la fecha de entrega de este TFG (§5.3.4, §7.2.1).

El instrumental **previsto** para esos niveles automatizados es el enunciado en el plan de pruebas (§5.3.5): `pytest` como armazón; un doble de prueba `MockProvider` que cumple la interfaz `LLMProvider` y devuelve respuestas grabadas; *fixtures* JSON con respuestas reales del SDK para las pruebas de los adaptadores; `sqlparse` para la verificación sintáctica del DDL; *checklists* en YAML bajo `tests/baseline/<dataset>.yaml` como especificación operativa del modelo de referencia de cada *dataset*; y, opcionalmente, un contenedor con Oracle Database Express Edition para una verificación por ejecución real del DDL. La evidencia efectivamente conservada de la validación realizada son los artefactos de las ejecuciones en los directorios `out-*` (§7.2.3).
