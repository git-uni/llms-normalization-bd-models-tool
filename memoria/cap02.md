# Capítulo 2. Definiciones

Varios términos recurrentes en esta memoria tienen, dentro del trabajo, un significado más preciso y acotado que su uso habitual. Algunos —como *prompt*— son además recientes y admiten lecturas dispares según el contexto; otros —como *evidencia*— se emplean aquí con una acepción deliberadamente amplia que conviene fijar para evitar malentendidos. Este capítulo reúne esas definiciones y constituye la referencia terminológica del resto del documento. No pretende ser un glosario exhaustivo de bases de datos o de inteligencia artificial, sino acotar el sentido con el que se usan los conceptos propios del proyecto.

## 2.1 Términos del problema y del resultado

**Modelo documental.** Estructura —explícita o implícita— de las colecciones y documentos de una base de datos NoSQL orientada a documentos, típicamente MongoDB: entidades, atributos, documentos embebidos, arrays y referencias entre documentos. Es el punto de partida que la herramienta analiza. Puede estar declarado mediante *schemas* (por ejemplo, Mongoose) o no estarlo, en cuyo caso debe inferirse a partir de la evidencia.

**Evidencia.** Conjunto **heterogéneo** de fragmentos procedentes de una aplicación documental que, cruzados, permiten reconstruir su modelo de datos. En este trabajo "evidencia" **no es sinónimo de *schema***: además de las definiciones explícitas de *schema* cuando existen, cuentan como evidencia las consultas a la base de datos (`find`, `aggregate`…), las operaciones de escritura (`insertOne`, `$push`…), los ejemplos de documentos, los accesos a campos desde el código de la aplicación y los comentarios que describen la estructura. El sistema no asume que el modelo esté declarado; en el caso realista (*difuso*), la evidencia vive dispersa en el código y hay que reunirla para inferir el modelo.

**Modelo relacional normalizado.** Representación del modelo documental en forma de tablas con claves primarias y foráneas, con la redundancia eliminada al menos hasta la tercera forma normal (3FN): cada array de objetos se convierte en una tabla con clave foránea hacia su entidad propietaria, y las denormalizaciones del documento se resuelven en referencias. Es el resultado que la herramienta produce.

**DDL (*Data Definition Language*).** Subconjunto de SQL dedicado a definir estructuras de datos —`CREATE TABLE`, claves primarias y foráneas, restricciones y tipos—, por oposición al lenguaje de consulta o de manipulación de datos. El artefacto final de la herramienta es DDL compatible con Oracle.

## 2.2 Términos del proceso y de la arquitectura

**Pipeline.** Cadena de cuatro fases —lectura, análisis del modelo documental, diseño relacional y generación de DDL— que transforma la evidencia de partida en el modelo relacional normalizado, comunicándose las fases entre sí a través de artefactos escritos en disco (véase el capítulo 6). El término se usa siempre con este sentido concreto, no como el "*pipeline*" genérico de integración continua.

**Artefacto.** Cada fichero que una fase del *pipeline* escribe en el directorio de salida de una ejecución: la evidencia agregada (`01_input.txt`), el análisis (`02_analysis.md`), el diseño relacional (`03_design.md`), el DDL (`04_ddl.sql`) y la traza del agente de descubrimiento. Los artefactos son a la vez el medio de comunicación entre fases y el material que el usuario puede inspeccionar tras la ejecución.

**Prompt.** Instrucción de texto que el sistema envía al modelo de lenguaje para obtener un resultado concreto en una fase del proceso. En este trabajo un *prompt* es una **pieza de diseño**: un fichero versionado y parametrizado del subsistema de *prompts* (§6.2.5), no el turno de una conversación. Conviene distinguir esta acepción de la coloquial: escribir un mensaje a un asistente conversacional en una interfaz web de chat también se denomina "*prompt*", pero ese uso —interactivo, manual e irrepetible— es justamente lo que el proyecto sustituye por una invocación **programática, reproducible y parametrizada** de la API del proveedor. Cuando esta memoria habla de "los *prompts* del sistema" se refiere a esos ficheros de instrucción, no a una sesión de chat.

**Agente de descubrimiento.** Componente que, cuando la entrada es la URL de un repositorio Git, explora autónomamente el código y selecciona la evidencia relevante antes de invocar el *pipeline*. "Agente" designa aquí ese bucle acotado que dialoga con el modelo y ejecuta un conjunto cerrado de herramientas (listar, leer, buscar, seleccionar y finalizar), no un sistema autónomo de propósito general.

**Function calling (*tool-use*).** Mecanismo por el que el modelo de lenguaje, en lugar de responder únicamente con texto, puede solicitar la ejecución de funciones predefinidas —*herramientas*— cuyos resultados se le devuelven para que continúe razonando. Es la capacidad sobre la que se construye el agente de descubrimiento, y la que distingue al modelo que usa el agente del modelo, más simple, que basta para el *pipeline*.

**Proveedor (interfaz `LLMProvider`).** Servicio externo que expone un modelo de lenguaje a través de una API —Google o Groq en este trabajo— y, en el código, la **interfaz** `LLMProvider` que lo abstrae. Gracias a esa interfaz, el resto del sistema es independiente del proveedor concreto y de su SDK: cambiar de proveedor no obliga a tocar el *pipeline* ni el agente.

## 2.3 Términos de la evaluación

**Modelo de referencia (*ground truth*).** Modelo elaborado manualmente por una persona experta —en este trabajo, un diagrama UML del autor del repositorio o del autor del TFG— que se toma como patrón para evaluar el resultado generado. Define qué entidades y relaciones *debería* recuperar la herramienta, y es la base de la comparación cualitativa, dado que no existe un DDL de referencia.

**Cobertura de entidades.** Métrica principal de validación: proporción de entidades del modelo de referencia que aparecen recuperadas en el modelo relacional generado. Se acompaña de la distinción entre entidades extra *legítimas* (sobre-normalización razonable) y *ruido*, y de la observación de su estabilidad entre ejecuciones (véase el capítulo 6).
