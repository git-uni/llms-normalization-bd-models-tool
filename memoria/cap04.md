# Capítulo 4. Requisitos de Usuario

El propósito de este capítulo es realizar una primera definición de los requisitos del sistema, expresados desde la perspectiva del usuario y de las restantes partes interesadas, sin entrar todavía en una especificación técnica detallada. Su contenido se alinea con el resultado del proceso de *Stakeholder Requirements Definition* descrito en la norma ISO/IEC/IEEE 15288 y se especifica siguiendo las recomendaciones para requisitos individuales recogidas en la norma ISO/IEC/IEEE 29148:2018 ([1], sucesora directa de IEEE 830-1998 [2]). En particular, cada requisito de usuario se acompaña de una **ficha reducida** que recoge los atributos mínimos exigidos por 29148 §5.2.4 ("Characteristics of individual requirements"): identificador único, descripción no ambigua y verificable, fuente trazable y necesidad declarada (criterio MoSCoW). En el capítulo 5 se desarrolla la ficha completa con la verificación, prioridad y dependencias asociadas a cada requisito funcional o no funcional derivado.

## 4.1 Alcance del sistema

El objetivo de este sistema es proporcionar una herramienta software que ayude en el análisis y transformación de modelos de datos desnormalizados, típicos de bases de datos NoSQL orientadas a documentos, en modelos relacionales normalizados.

En muchos sistemas modernos, especialmente aquellos que utilizan bases de datos documentales como MongoDB, los modelos de datos suelen estar diseñados siguiendo un enfoque desnormalizado que prioriza el rendimiento de lectura y la simplicidad de acceso a los datos. Sin embargo, cuando se requiere migrar estos sistemas a bases de datos relacionales o mejorar su diseño estructural, es necesario realizar un proceso de análisis y normalización del modelo de datos.

Este proceso suele realizarse manualmente por arquitectos de datos o desarrolladores experimentados, lo que puede resultar complejo y costoso, especialmente cuando los modelos de datos son grandes o las relaciones entre entidades no están explícitamente definidas.

El sistema propuesto busca facilitar este proceso mediante el uso de modelos de lenguaje de gran tamaño (LLMs), capaces de analizar estructuras de datos desnormalizadas e inferir entidades, relaciones y dependencias entre datos. A partir de este análisis, el sistema genera una propuesta de modelo relacional normalizado que sirve como punto de partida para el diseño de una base de datos relacional equivalente.

La herramienta está diseñada como un sistema de apoyo al análisis de modelos de datos, no como un sistema completamente automático de migración. El modelo generado debe ser interpretado y validado posteriormente por un desarrollador o arquitecto de datos.

Las formas previstas de proporcionar el modelo de datos al sistema son tres:

- Carga de un archivo con la definición explícita de *schemas*.
- Carga de un conjunto curado de fragmentos heterogéneos de evidencia documental.
- Suministro de la URL de un repositorio de código, donde el propio sistema descubre mediante agentes los archivos relevantes para inferir el modelo documental.

A partir de esa entrada, el sistema realiza un análisis estructural, propone un modelo relacional normalizado y genera las sentencias DDL compatibles con Oracle, permitiendo al usuario inspeccionar los artefactos intermedios y comparar ejecuciones distintas.

Los principales interesados (*stakeholders*) del sistema son:

- **Desarrolladores de software** que trabajan con bases de datos NoSQL y necesitan analizar o migrar sus modelos de datos.
- **Arquitectos de software o arquitectos de datos**, responsables del diseño y evolución de modelos de datos en sistemas complejos.
- **Investigadores y estudiantes**, interesados en explorar el uso de modelos de lenguaje para tareas de ingeniería de datos.

## 4.2 Requisitos de usuario

### 4.2.1 RU-1. Suministro del modelo de datos de entrada

El usuario debe poder proporcionar al sistema el modelo de base de datos desnormalizado que se quiere analizar, a través de distintos mecanismos según el grado de elaboración del material disponible. Esta flexibilidad reconoce que, en la práctica, los modelos documentales no siempre están declarados de forma explícita: con frecuencia hay que inferirlos cruzando *schemas* parciales, consultas, operaciones de escritura, ejemplos de documentos y accesos a campos desde código de aplicación.

#### RU-1.1 Carga desde archivo de *schemas*

El usuario debe poder seleccionar un único archivo que contenga la definición explícita de los *schemas* de una base de datos documental (por ejemplo, *schemas* Mongoose en JavaScript) y entregárselo al sistema como entrada.

| Atributo | Valor |
|---|---|
| Fuente | Desarrollador / arquitecto de datos con material auto-contenido. |
| Necesidad | Must. |
| Verificación | Ejecución end-to-end del modo archivo sobre los ficheros de `data/spruce/`, comprobando que se obtienen las cuatro fases de salida (`01_input`…`04_ddl.sql`). |

#### RU-1.2 Carga desde directorio de evidencia heterogénea

El usuario debe poder proporcionar un conjunto de archivos previamente curados que contengan evidencia heterogénea del modelo documental (*schemas* explícitos, consultas, operaciones de escritura, ejemplos de documentos, accesos a campos desde código de aplicación, comentarios) y obtener un resultado igualmente útil cuando no exista una declaración explícita de *schemas*.

| Atributo | Valor |
|---|---|
| Fuente | Arquitecto de datos sobre repositorios sin *schemas* declarativos. |
| Necesidad | Must. |
| Verificación | Ejecución end-to-end del modo directorio sobre `data/spruce-difuso/`, validando la cobertura cualitativa del DDL frente al diagrama de referencia. |

#### RU-1.3 Análisis a partir de la URL de un repositorio

El usuario debe poder proporcionar únicamente la URL pública de un repositorio de código que contenga una aplicación basada en una base de datos documental, sin necesidad de seleccionar manualmente los archivos relevantes ni de preparar ningún material previo.

| Atributo | Valor |
|---|---|
| Fuente | Usuario sin conocimiento previo del repositorio analizado. |
| Necesidad | Must. |
| Verificación | Ejecución del modo URL sobre la URL pública del repositorio Spruce y comparación cualitativa con el diagrama de referencia. |

### 4.2.2 RU-2. Análisis del modelo documental

El usuario debe poder obtener, a partir de la entrada proporcionada, una descripción comprensible del modelo documental subyacente que le permita conocer cómo se ha interpretado su material.

#### RU-2.1 Identificación de entidades y atributos

El usuario debe poder conocer qué entidades (colecciones de documentos) se han identificado en su entrada, así como los atributos que componen cada una y, en la medida de lo posible, sus tipos de datos.

| Atributo | Valor |
|---|---|
| Fuente | Necesidad de interpretar la salida del análisis. |
| Necesidad | Must. |
| Verificación | Inspección del artefacto `02_analysis.md` sobre los datasets de referencia. |

#### RU-2.2 Detección de relaciones implícitas

El usuario debe poder conocer las relaciones entre entidades que se han detectado, distinguiendo entre referencias por identificador, documentos embebidos y arrays anidados, incluso cuando estas relaciones no estuvieran declaradas formalmente en su material.

| Atributo | Valor |
|---|---|
| Fuente | Casuística observada en `data/spruce-difuso/` (relaciones expresadas implícitamente en código de aplicación). |
| Necesidad | Must. |
| Verificación | Inspección de la sección de relaciones del artefacto `02_analysis.md` sobre el dataset difuso, comprobando que se reconstruyen las relaciones implícitas conocidas. |

#### RU-2.3 Trazabilidad del análisis

El usuario debe poder consultar un documento intermedio que explique con qué evidencias se ha llegado a cada entidad, atributo o relación detectados, de modo que pueda validar o discutir el razonamiento del sistema.

| Atributo | Valor |
|---|---|
| Fuente | Requisito de inspeccionabilidad para defensa de los resultados. |
| Necesidad | Should. |
| Verificación | Presencia de citas explícitas de evidencia en el artefacto `02_analysis.md` para cada decisión estructural relevante. |

### 4.2.3 RU-3. Generación del modelo relacional normalizado

El usuario debe poder obtener, a partir del modelo documental analizado, un modelo relacional normalizado equivalente que le sirva como base de partida para una migración o un rediseño.

#### RU-3.1 Diseño de tablas, claves primarias y foráneas

El usuario debe obtener un modelo relacional con tablas, claves primarias bien definidas y claves foráneas explícitas para las relaciones detectadas.

| Atributo | Valor |
|---|---|
| Fuente | Norma de diseño relacional clásica (Codd). |
| Necesidad | Must. |
| Verificación | Inspección del artefacto `03_design.md` y verificación sintáctica del DDL resultante. |

#### RU-3.2 Eliminación de redundancias

El usuario debe obtener un modelo relacional que minimice las redundancias presentes en el modelo documental original: arrays embebidos normalizados en tablas hijas, valores duplicados en distintos documentos consolidados en tablas independientes y atributos repetidos por denormalización reconciliados en una única columna canónica.

| Atributo | Valor |
|---|---|
| Fuente | Casuística observada en `data/spruce-difuso/`: atributos redundantes que apuntan al mismo registro de otra tabla. |
| Necesidad | Must. |
| Verificación | Inspección cualitativa del DDL: ausencia de columnas que dupliquen la información ya alcanzable por *join*. |

#### RU-3.3 Generación de DDL Oracle

El usuario debe poder obtener el modelo relacional final como un conjunto de sentencias DDL compatibles con Oracle (`CREATE TABLE`, claves primarias, claves foráneas y restricciones).

| Atributo | Valor |
|---|---|
| Fuente | Sistemas Oracle dominantes en los entornos *legacy* objetivo del autor. |
| Necesidad | Must. |
| Verificación | Inspección sintáctica del artefacto `04_ddl.sql` y comprobación de su parseo con un analizador SQL. |

### 4.2.4 RU-4. Independencia y configuración del proveedor de LLM

El usuario no debe quedar atado a un único proveedor de LLM, ni a un único modelo dentro de un proveedor.

#### RU-4.1 Elección del proveedor

El usuario debe poder elegir, en el momento de invocar la herramienta, qué proveedor de LLM se utilizará (por ejemplo, Google, Groq u otros que se incorporen en el futuro).

| Atributo | Valor |
|---|---|
| Fuente | Necesidad de cobertura ante retiradas de modelos o reducciones de cuota observadas durante el desarrollo. |
| Necesidad | Must. |
| Verificación | Invocación del CLI con `--provider google` y `--provider groq` sobre el mismo dataset, comprobando que ambas ejecuciones producen artefactos válidos. |

#### RU-4.2 Elección del modelo concreto

El usuario debe poder seleccionar, dentro del proveedor elegido, el modelo concreto a emplear (por ejemplo, distintos modelos de la misma familia).

| Atributo | Valor |
|---|---|
| Fuente | Necesidad de calibrar el coste y la calidad de la ejecución según el dataset. |
| Necesidad | Must. |
| Verificación | Invocación del CLI con `--model` y `--agent-model` y comprobación de que los valores efectivamente usados aparecen en la traza. |

#### RU-4.3 Gestión segura de credenciales

El usuario debe poder configurar las credenciales (API keys) de los proveedores sin tener que modificar el código de la herramienta y sin que éstas queden registradas en repositorios públicos.

| Atributo | Valor |
|---|---|
| Fuente | Buenas prácticas de seguridad (OWASP ASVS, Nivel 1). |
| Necesidad | Must. |
| Verificación | Auditoría del repositorio: ausencia de claves en el código y en el historial Git; presencia de un `.env.example` y de la entrada `.env` en `.gitignore`. |

### 4.2.5 RU-5. Uso de agentes para análisis de repositorios

Cuando la entrada a la herramienta es la URL de un repositorio completo (RU-1.3) —y no un archivo o un directorio que el usuario ha preparado de antemano (RU-1.1, RU-1.2)—, la evidencia sobre el modelo documental queda mezclada con código de propósitos muy distintos, del que es solo una parte menor y en el que no siempre se declara de forma explícita. Identificarla exige explorar el repositorio, abrir archivos candidatos y juzgar cuáles aportan información sobre los datos — el mismo trabajo que haría un analista humano al estudiar un proyecto ajeno. El usuario debe poder delegar esa exploración en un agente: un LLM que, además de generar texto, dispone de un repertorio de operaciones sobre el repositorio (listar directorios, leer archivos, buscar patrones) y decide por sí mismo qué operación ejecutar en cada paso, a la vista de los resultados de las anteriores, hasta reunir la evidencia necesaria para reconstruir el modelo documental.

#### RU-5.1 Descubrimiento autónomo de archivos relevantes

El usuario no debe tener que identificar ni aportar manualmente los archivos relevantes: dada únicamente la URL del repositorio, el agente debe explorar su contenido y seleccionar de forma autónoma los archivos que contienen evidencia útil del modelo documental.

| Atributo | Valor |
|---|---|
| Fuente | RU-1.3 (entrada por URL). |
| Necesidad | Must. |
| Verificación | Ejecución sobre la URL pública del repositorio Spruce y comprobación de que el agente selecciona los cuatro *schemas* declarativos del repositorio. |

#### RU-5.2 Justificación de las decisiones del agente

El usuario debe poder consultar una traza o explicación de por qué el agente ha seleccionado unos archivos y descartado otros, para poder confiar en su criterio o corregirlo.

| Atributo | Valor |
|---|---|
| Fuente | Mismas necesidades de defensa pública que motivan RU-2.3. |
| Necesidad | Must. |
| Verificación | Inspección del artefacto `00_discovery/discovery.md`: tabla `Iter | Tool calls` con las invocaciones realizadas y lista de archivos seleccionados con sus justificaciones. |

### 4.2.6 RU-6. Interfaz de uso de la herramienta

El usuario debe poder utilizar la herramienta mediante una interfaz adecuada a su preferencia de uso, ya sea por línea de comandos o gráfica. El sistema ofrece dos interfaces que son funcionalmente equivalentes: cualquier flujo expresable desde una de ellas es expresable también desde la otra.

#### RU-6.1 Interfaz de línea de comandos (CLI)

El usuario debe poder utilizar la herramienta desde una interfaz de línea de comandos, de modo que pueda integrarla en *pipelines* automatizados o utilizarla en entornos sin escritorio gráfico.

| Atributo | Valor |
|---|---|
| Fuente | Integración con flujos automatizados (CI/CD, scripts). |
| Necesidad | Must. |
| Verificación | Invocación `python -m normalizer <entrada> [--provider …] [--model …] [--out-dir …]` y observación de los mensajes de progreso por la salida de error estándar. |

#### RU-6.2 Interfaz gráfica de usuario (GUI)

El usuario debe poder utilizar la herramienta desde una interfaz gráfica que le permita cargar la entrada de forma visual, configurar el proveedor y el modelo, seguir el avance del proceso, inspeccionar los resultados intermedios y exportar el resultado final, sin necesidad de conocer la sintaxis de la línea de comandos.

| Atributo | Valor |
|---|---|
| Fuente | Stakeholder que prefiere una interfaz gráfica (arquitecto de datos sin experiencia previa en CLI). |
| Necesidad | Must. |
| Verificación | Reproducción de un caso completo (`data/spruce/` y URL pública) desde la GUI por un usuario que no conozca los flags del CLI. |

##### RU-6.2.1 Configuración visual de la ejecución

La GUI debe permitir la selección de la fuente de entrada (archivo, directorio o URL), del proveedor y del modelo, mediante controles visuales en lugar de argumentos textuales.

##### RU-6.2.2 Seguimiento del progreso

La GUI debe presentar el avance del pipeline fase a fase y, en el modo URL, debe reflejar las iteraciones del agente de descubrimiento conforme se producen.

##### RU-6.2.3 Inspección integrada de artefactos

La GUI debe permitir visualizar los artefactos intermedios (`02_analysis.md`, `03_design.md`, `04_ddl.sql`) y la traza `00_discovery/discovery.md` sin necesidad de abrirlos en una aplicación externa.

##### RU-6.2.4 Aislamiento por ejecución

Cada lanzamiento desde la GUI debe generar su propio directorio de salida, de modo que ejecuciones consecutivas no sobrescriban los resultados previas. Este sub-requisito materializa RU-7.2 sobre la interfaz gráfica.

### 4.2.7 RU-7. Inspección de los resultados intermedios

El usuario debe poder inspeccionar todos los artefactos producidos por el sistema durante el proceso, no sólo el DDL final, para entender, depurar y comparar ejecuciones.

#### RU-7.1 Acceso a los artefactos por fases

El usuario debe poder acceder a los resultados de cada fase del proceso (entrada agregada, análisis del modelo documental, diseño relacional, DDL final) como archivos independientes que pueda abrir y consultar.

| Atributo | Valor |
|---|---|
| Fuente | Necesidad de diagnóstico y comparación entre proveedores. |
| Necesidad | Must. |
| Verificación | Comprobación de que tras una ejecución existen en el directorio de salida los cuatro artefactos esperados, todos legibles directamente como texto. |

#### RU-7.2 Aislamiento de ejecuciones

El usuario debe poder lanzar varias ejecuciones sobre distintos casos de prueba sin que los resultados de una sobrescriban los de otra.

| Atributo | Valor |
|---|---|
| Fuente | Necesidad práctica observada durante la validación inter-proveedor del propio prototipo. |
| Necesidad | Must. |
| Verificación | Dos ejecuciones consecutivas sobre datasets distintos, con `--out-dir` distintos, mantienen sus artefactos sin colisión. |

### 4.2.8 RU-8. Prototipo

El usuario debe poder disponer de un prototipo end-to-end que cubra el flujo completo de la herramienta para los tres modos de entrada considerados (archivo, directorio curado y URL), accesible tanto desde la CLI como desde la GUI.

#### RU-8.1 Ejecución end-to-end

El usuario debe poder, mediante una única invocación, ejecutar todo el proceso de transformación (lectura, análisis, diseño, DDL) y obtener el DDL Oracle final sobre los datasets de prueba.

| Atributo | Valor |
|---|---|
| Fuente | Demostrabilidad del trabajo. |
| Necesidad | Must. |
| Verificación | Ejecución de `python -m normalizer data/spruce/ --out-dir out-spruce/` y comprobación de la presencia y validez sintáctica del DDL final. |

#### RU-8.2 Validación frente al modelo de referencia

El usuario debe poder validar el prototipo comparando cualitativamente su salida con el modelo relacional de referencia elaborado manualmente para el repositorio de prueba seleccionado (Spruce).

| Atributo | Valor |
|---|---|
| Fuente | Ausencia de DDL manual; el baseline es el diagrama UML del autor. |
| Necesidad | Must. |
| Verificación | Comparación cualitativa entidad a entidad del DDL generado contra el diagrama UML manual de Spruce. |

#### RU-8.3 Validación del prototipo desde la GUI

El usuario debe poder reproducir, desde la interfaz gráfica, los mismos casos de validación que se hayan ejecutado desde la CLI, comprobando que ambos caminos producen artefactos equivalentes.

| Atributo | Valor |
|---|---|
| Fuente | Paridad funcional CLI / GUI. |
| Necesidad | Must. |
| Verificación | Reproducción manual desde la GUI de los casos `data/spruce/`, `data/spruce-difuso/` y URL pública de Spruce, y comparación de los DDL resultantes con los obtenidos por CLI sobre los mismos datos. |

## 4.3 Alternativas

Cuando existió libertad de elección entre varias alternativas técnicas para dar cumplimiento a los requisitos de usuario, se documentan a continuación los principales puntos de decisión, los criterios considerados y la opción finalmente seleccionada. Las alternativas que afectan a la organización interna del código (patrones de diseño concretos, estructura de paquetes) se discuten en el capítulo 6.

### 4.3.1 Tecnología de la interfaz gráfica (RU-6.2)

Se consideraron tres familias de *toolkits* gráficos compatibles con Python: una librería de *widgets* nativos sobre Qt (PyQt6 / PySide6), un *toolkit* basado en Tkinter con un aspecto moderno (CustomTkinter) y un *framework* de aplicación web ligera (Streamlit).

| Alternativa | Ventajas | Inconvenientes | Decisión |
|---|---|---|---|
| **PyQt6 / PySide6** | Aspecto nativo en cada sistema operativo; *widgets* ricos (resaltado de SQL en `QPlainTextEdit`, `QTabWidget` para paneles, `QThread` integrado en el modelo de señales para el progreso en tiempo real); empaquetable como ejecutable con PyInstaller. | Curva de aprendizaje notable (modelo de *signals/slots*, gestión de hilos); tamaño del ejecutable resultante elevado (≈ 80 MB); decisión sobre licencia (LGPL / GPL) que añade fricción innecesaria en un contexto académico. | Descartada por relación coste / beneficio en el tiempo restante del proyecto. |
| **CustomTkinter** | Curva muy suave para un autor familiarizado con Python pero no con *toolkits* gráficos; API casi idéntica a Tkinter estándar; aspecto consistente entre plataformas; empaquetado trivial con PyInstaller en un binario monolítico. | *Widgets* ricos limitados (sin resaltado SQL nativo: requiere composición sobre `CTkTextbox`); modelo de eventos clásico de Tkinter (`after()` + *polling*) para el progreso en tiempo real. | **Seleccionada.** Equilibrio óptimo entre tiempo de desarrollo, complejidad y cobertura de los requisitos. |
| **Streamlit** | Modelo de programación lineal muy simple; soporte directo de Markdown y SQL para visualizar artefactos; *spinners* y estados ya resueltos. | Requiere un servidor local y un navegador externo, lo que rompe el modelo "ejecutable monolítico"; el ciclo *rerun on interaction* dificulta el seguimiento en *streaming* del agente; experiencia del usuario heterogénea. | Descartada por el requisito implícito de un único proceso de escritorio. |

### 4.3.2 Estrategia de invocación de herramientas por el agente (RU-5)

Existen tres formas habituales de exponer herramientas a un LLM en un bucle agéntico:

| Alternativa | Ventajas | Inconvenientes | Decisión |
|---|---|---|---|
| Esquema de respuesta JSON parseado del texto generado | Funciona con cualquier modelo, independientemente del soporte explícito de *function calling*. | Sensibilidad alta al formato; cualquier desvío del modelo (comillas raras, *markdown* añadido) rompe el *parser*. | Descartada por fragilidad. |
| *Function calling* nativo del SDK del proveedor | Canal estructurado, entrenado específicamente por el proveedor; el SDK valida los argumentos antes de devolverlos. | Cada proveedor expone un formato distinto; requiere una capa de traducción interna. | **Seleccionada.** La capa de traducción se materializa en los adaptadores de cada `LLMProvider` (capítulo 6), aislando al resto del sistema. |
| *Framework* externo de agentes (LangChain, LlamaIndex, AutoGen) | Numerosos componentes prefabricados; comunidad extensa. | Acoplamiento fuerte al *framework*; aumento del número de dependencias; abstracciones intermedias que ocultan el bucle real, dificultando el control de presupuestos y la observabilidad. | Descartada por preferir una implementación directa del bucle, alineada con el principio de "*no magic*" buscado en la defensa del trabajo. |

### 4.3.3 Cobertura multiproveedor (RU-4.1)

La inclusión de un segundo proveedor no era obligatoria a priori, pero la experiencia de desarrollo demostró que un solo proveedor introduce un punto único de fallo. La decisión entre alternativas se documenta en el apartado 5.1 (RF-5.4 Soporte mínimo multiproveedor) y se motiva en mayor detalle en el capítulo 3 (riesgo R-01) y en el capítulo 9 (lecciones aprendidas).

### 4.3.4 Dialecto SQL objetivo (RU-3.3)

Se consideraron otros dialectos relacionales (PostgreSQL, MySQL) por su amplia adopción. Se seleccionó **Oracle** por dos motivos: (i) Oracle es el motor mayoritario en los entornos *legacy* sobre los que el autor trabaja profesionalmente, lo que da una motivación práctica real al trabajo; (ii) Oracle presenta peculiaridades específicas (tipos `NUMBER` con precisión y escala, `VARCHAR2`, soporte de `BOOLEAN` solo a partir de la versión 23ai) que enriquecen el ejercicio frente a dialectos más uniformes. Esta elección queda formalizada en RNF-5.2 del capítulo 5.

---

**Referencias del capítulo**

[1] ISO/IEC/IEEE 29148:2018 — *Systems and software engineering — Life cycle processes — Requirements engineering.*

[2] IEEE 830-1998 — *Recommended Practice for Software Requirements Specifications.* (Retirada en 2011, reemplazada por 29148; se mantiene como referencia histórica.)

[3] ISO/IEC/IEEE 15288:2015 — *Systems and software engineering — System life cycle processes.*
