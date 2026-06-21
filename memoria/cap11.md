# Capítulo 11. Pruebas

Este capítulo recoge la verificación y validación del sistema. Se organiza en tres apartados: la **introducción** (§11.1) fija la estrategia de pruebas y qué se prueba; el **diseño de las pruebas** (§11.2) deriva los casos concretos mediante técnicas clásicas de prueba de caja negra; y la **ejecución** (§11.3) recoge los resultados obtenidos.

## 11.1 Introducción

El sistema combina dos clases de componentes con propiedades muy distintas de cara a las pruebas:

- Una **parte determinista** —lectura de la entrada, persistencia de artefactos, despacho y confinamiento de las herramientas del agente, control del presupuesto, reintentos ante fallos transitorios y traducción entre el formato neutro y los SDK de cada proveedor—, cuyo comportamiento puede verificarse de forma mecánica: dada una entrada, hay un único resultado correcto.
- Una **parte probabilística** —las decisiones del LLM en cada fase del *pipeline* y en cada turno del agente—, cuyo resultado correcto no es objetivamente definible y, por tanto, se valida **cualitativamente** por comparación con un modelo de referencia elaborado por un experto humano.

La estrategia aborda ambas en paralelo, sin reducir una a la otra: la parte determinista se verifica con **pruebas funcionales de caja negra** diseñadas por partición en clases de equivalencia; la parte probabilística se valida con **pruebas de aceptación cualitativas** que miden la cobertura del modelo relacional generado frente al modelo objetivo.

Todas las pruebas son **manuales**. Es una decisión deliberada y proporcionada al sistema: su superficie de entrada es reducida —tres modos de entrada y un puñado de condiciones de borde—, la parte más valiosa de evaluar es precisamente la probabilística (que requiere juicio humano), y la ejecución manual es la que ha acompañado al prototipo durante todo el desarrollo. No se persigue una *suite* automatizada de regresión, cuya incorporación se plantea como línea de ampliación (capítulo 9).

Quedan **fuera del alcance** las pruebas de carga y de rendimiento sostenido: el sistema no se concibe como un servicio de producción multiusuario, por lo que sus requisitos de rendimiento (RNF-1) se cubren con mediciones puntuales durante la validación.

La tabla siguiente recoge, para cada subsistema, las propiedades que la verificación debe cubrir.

| Subsistema | Propiedades verificadas |
|---|---|
| Lectura de la entrada | Lectura correcta del fichero único; concatenación correcta del directorio con marcas de origen; descarte silencioso de binarios y de ficheros que excedan el umbral configurado; manejo de entrada inexistente o inaccesible con mensaje claro. |
| *Pipeline* | Generación de los cuatro artefactos esperados en el directorio de salida; carga correcta de los *prompts*; propagación ordenada de errores producidos en cada fase con identificación de la fase fallida, conservando los artefactos previos. |
| Agente de descubrimiento | Cumplimiento del presupuesto de iteraciones; clonado y reutilización correctos de la caché de repositorios; construcción del árbol filtrado con recorrido por niveles y límite de entradas; despacho correcto de cada herramienta; producción de la traza (`discovery.md`) con la lista de archivos seleccionados y sus justificaciones. |
| Herramientas confinadas | Rechazo de rutas que escapen del directorio del repositorio clonado o del directorio de salida; validación de los argumentos recibidos del LLM con mensajes de error estructurados. |
| Abstracción del proveedor | Traducción correcta entre el formato neutro y el formato del SDK en ambos sentidos; reintentos sobre los códigos transitorios definidos; selección correcta de la clase y del modelo por la *factory* según los parámetros. |
| Interfaces (CLI y GUI) | Paridad funcional entre ambas; emisión de mensajes de progreso por cada fase; presentación al usuario de los errores del proveedor con indicación de la fase de origen. |

## 11.2 Diseño de las pruebas

### 11.2.1 Técnica

Las pruebas funcionales se diseñan mediante **partición en clases de equivalencia** complementada con **análisis de valores límite**: para cada condición de entrada relevante se identifican las clases —válidas e inválidas— que el sistema debe tratar de la misma forma, de modo que baste un representante de cada clase para ejercitar el comportamiento asociado. De esas clases se derivan las **situaciones de prueba**: casos concretos con una entrada o acción, la clase que cubren y el resultado esperado. Esta técnica acota el número de casos a un conjunto pequeño y justificado, sin renunciar a cubrir las situaciones de borde que más riesgo concentran (entrada inválida, escape del confinamiento, agotamiento del presupuesto, fallo de fase).

### 11.2.2 Clases de equivalencia

| Condición de entrada | Clases válidas | Clases inválidas |
|---|---|---|
| Naturaleza del argumento de entrada (RF-1) | Archivo de texto existente; directorio existente con al menos un fichero legible; URL de repositorio Git público | Ruta inexistente o inaccesible; directorio sin ningún fichero legible |
| Tipo de cada fichero leído (RF-1.5) | Fichero decodificable como texto UTF-8 | Fichero binario / no decodificable; fichero que supera el umbral de tamaño |
| Ruta solicitada por una herramienta del agente (RF-4.2) | Ruta contenida en el repositorio clonado o en el directorio de salida | Ruta que escapa de ese ámbito (p. ej. `../../etc/passwd`) |
| Presupuesto del agente (RF-3.5, RNF-1.2) | Iteraciones ≤ `max_iters`, selecciones ≤ `max_files`, árbol ≤ `max_tree_entries` | Se supera `max_iters`; se supera `max_files`; el árbol supera `max_tree_entries` (se trunca) |
| Proveedor y modelo (RF-5) | Proveedor registrado con un modelo válido para su rol | Nombre de proveedor o de modelo inexistente |
| Continuidad ante fallo de fase (RF-7.3) | Las cuatro fases del *pipeline* terminan correctamente | Una fase falla (deben conservarse los artefactos de las fases previas) |

### 11.2.3 Situaciones de prueba

Cada situación operacionaliza el criterio de verificación enunciado para el requisito correspondiente en el capítulo 5; entre paréntesis se indica el requisito de origen.

| ID | Entrada / acción | Clase cubierta | Resultado esperado |
|---|---|---|---|
| SP-01 | `normalizer data/spruce/keys.js` | Archivo de texto | `01_input.txt` reproduce el contenido con su marca de origen; se generan los cuatro artefactos. (RF-1.1) |
| SP-02 | `normalizer data/spruce-difuso/` | Directorio | `01_input.txt` concatena los ocho ficheros, cada uno con su marca de origen. (RF-1.2) |
| SP-03 | Directorio anterior con un fichero binario añadido | Fichero binario | El binario se omite y su nombre se anota al final del artefacto. (RF-1.5) |
| SP-04 | Ruta de entrada inexistente | Ruta inexistente | Error claro al usuario; el *pipeline* no llega a arrancar. (RF-1.4) |
| SP-05 | `normalizer https://github.com/dan-divy/spruce` | URL Git pública | Clonado en caché; el agente selecciona evidencia y produce `00_discovery/discovery.md`. (RF-1.3, RF-3) |
| SP-06 | Invocación sintética de `read_file` con `../../etc/passwd` | *Path traversal* | La herramienta devuelve un error estructurado y no accede al fichero. (RF-4.2) |
| SP-07 | Agente con `max_iters` reducido sobre un repositorio grande | Excede el presupuesto | La operación aborta con un mensaje claro y la traza registra la causa. (RF-3.5) |
| SP-08 | Fallo inducido en la fase de generación de DDL | Fallo de fase | `02_analysis.md` y `03_design.md` permanecen en el directorio de salida. (RF-7.3) |
| SP-09 | Misma entrada con `--provider groq` | Proveedor alternativo | Mismo flujo y artefactos equivalentes, sin cambios fuera de `providers/`. (RF-5) |
| SP-10 | Misma entrada ejecutada por CLI y por GUI | Paridad de interfaces | Ambas producen artefactos equivalentes sobre el mismo núcleo. (RF-6.3) |
| SP-11 | `--max-tree-entries` reducido sobre un repositorio grande | Árbol supera el cap | `00_discovery/tree.txt` se trunca al valor indicado, con la línea final «árbol truncado a N entradas». (RF-3.5, RNF-1.2) |

### 11.2.4 Diseño de la validación cualitativa

La parte probabilística se valida sobre un banco de *datasets* de referencia, cada uno acompañado de un **modelo de referencia** elaborado manualmente por un experto (un diagrama UML del autor del repositorio o del autor del TFG). El banco se agrupa según su grado de formalización:

**Datasets de cobertura con lista de entidades de referencia:**

- **`data/spruce/`**: caso de control con cuatro *schemas* Mongoose explícitos. El modelo documental está declarado de forma íntegra y ejercita el *pipeline* aislado del agente de descubrimiento.
- **`data/spruce-difuso/`**: el mismo modelo documental pero distribuido implícitamente en código de aplicación (rutas Express, manejadores de socket) sin *schemas* declarados. Ejercita la capacidad del *prompt* de análisis para inferir el modelo a partir de evidencia heterogénea.
- **URL pública del repositorio de Spruce**: el repositorio completo, suministrado únicamente como URL, ejercita el agente de descubrimiento sobre un proyecto pequeño con *schemas* explícitos.

**Dataset de validación cualitativa adicional:**

- **URL pública del repositorio de Habitica**: una aplicación real de tamaño realista, con muchos directorios irrelevantes para el modelo documental. Se utiliza para observar la varianza del agente frente a repositorios grandes y para detectar las fronteras de cuota de los proveedores en condiciones reales. La comparación es cualitativa contra una lista no exhaustiva de entidades esperadas elaborada por inspección del código fuente.

Para cada *dataset* y modelo de LLM, la validación calcula y registra:

- **Cobertura de entidades**: cociente entre las entidades del modelo de referencia recuperadas en el DDL generado y el total de entidades del modelo de referencia.
- **Entidades extra**: clasificadas en *legítimas* (sobre-normalización razonable, como la separación en tablas independientes de los *arrays* embebidos) y *ruido* (entidades sin justificación en la entrada).
- **Invariantes estructurales**: toda tabla declara una clave primaria; toda clave foránea referencia una tabla y columna existentes; la regla de reconciliación de atributos redundantes no deja referencias duplicadas.
- **Reproducibilidad inter-ejecuciones**: estabilidad de la cobertura a lo largo de varias ejecuciones con la misma entrada, el mismo proveedor y el mismo modelo, como concreción de RNF-2.1.
- **Cobertura cruzada modelo × *dataset***: una tabla que cruza los modelos de LLM disponibles con los *datasets* de referencia. Constituye la evidencia empírica del comportamiento del sistema bajo distintos modelos y documenta, sin ocultarlo, que la capacidad del modelo elegido es un factor determinante en la calidad del resultado.

## 11.3 Ejecución de las pruebas

### 11.3.1 Pruebas funcionales

Las situaciones de prueba de §11.2.3 se ejecutaron de forma manual sobre los *datasets* locales y, para los casos de borde, mediante invocaciones sintéticas e inducción controlada de fallos. La tabla resume el resultado y la evidencia que lo respalda.

| ID | Resultado | Evidencia |
|---|---|---|
| SP-01 | Correcto | Artefacto `01_input.txt` y los cuatro artefactos del *pipeline* en el directorio de salida. |
| SP-02 | Correcto | `01_input.txt` con los ocho ficheros concatenados y sus marcas de origen. |
| SP-03 | Correcto | El binario no aparece concatenado; su nombre figura en la nota final del artefacto (`_read_input` en `pipeline/pipeline.py`). |
| SP-04 | Correcto | Mensaje de error de la CLI antes de instanciar el *pipeline* (`cli.py`). |
| SP-05 | Correcto | Directorio `.cache/repos/<hash>/` y traza `00_discovery/discovery.md` con la selección del agente. |
| SP-06 | Correcto | Rechazo por `resolve_within` en `discovery/filesystem.py`; la herramienta devuelve error sin leer. |
| SP-07 | Correcto | Aborto con mensaje y registro de la causa en la traza del agente. |
| SP-08 | Correcto | `02_analysis.md` y `03_design.md` conservados, al escribir cada fase su artefacto antes de continuar. |
| SP-09 | Correcto | DDL generado con Groq sin tocar el núcleo (`out-difuso-groq/`). |
| SP-10 | Correcto | Misma capa de núcleo (`run_pipeline`, `discover_from_url`) invocada desde CLI y GUI. |
| SP-11 | Correcto | `tree.txt` truncado al valor de `--max-tree-entries`; línea final «árbol truncado a N entradas» (`build_tree_summary` en `discovery/filesystem.py`). |

### 11.3.2 Estado de la validación cualitativa

La validación del prototipo se ha concentrado en el nivel de **aceptación cualitativa** sobre los *datasets* de referencia. Esto no significa que el sistema no se haya verificado: el banco de pruebas cualitativas se ejecutó de forma sistemática sobre los tres *datasets* de cobertura y, de forma adicional, sobre Habitica. Esta priorización es coherente con la planificación del proyecto (capítulo 3) y con la naturaleza del trabajo, donde el factor de mayor incertidumbre es el comportamiento del LLM, no la parte determinista del código.

### 11.3.3 Resultados de la validación cualitativa

La tabla siguiente resume las ejecuciones realizadas. La métrica de cobertura es entidad-a-entidad contra el modelo UML manual; las celdas vacías indican combinaciones que el *free tier* no permite (por ejemplo, agente Groq sobre Habitica por la frontera de TPM documentada en R-02).

| Dataset | Modo | Proveedor *pipeline* | Modelo *pipeline* | Proveedor agente | Modelo agente | Iter. agente | Archivos sel. | DDL tablas | Cobertura UML |
|---|---|---|---|---|---|---:|---:|---:|---|
| `data/spruce/` | Directorio | Google | gemma-4-31b-it | — | — | — | — | 11 | 11 / 11 |
| `data/spruce/` | Directorio | Groq | llama-3.3-70b-versatile | — | — | — | — | ≈11 | 10 / 11 |
| `data/spruce-difuso/` | Directorio | Google | gemma-4-31b-it | — | — | — | — | 11 | 11 / 11 |
| `data/spruce-difuso/` | Directorio | Groq | llama-3.3-70b-versatile | — | — | — | — | 9 | 7 / 11 |
| Spruce URL pública | URL | Google | gemma-4-31b-it | Google | gemini-3.1-flash-lite | 5 | 4 | 11 | 11 / 11 |
| Habitica URL pública | URL | Google | gemma-4-31b-it | Google | gemini-3.1-flash-lite | 13 | 11 | 31 | cualitativa adicional |
| Habitica URL pública | URL | Groq | llama-3.3-70b-versatile | Groq | qwen/qwen3-32b | — | — | — | no completada — 413 TPM |

Las dos primeras filas muestran que la cobertura del *pipeline* sobre el *dataset* de control no depende fuertemente del proveedor (Spruce con *schemas* explícitos cae bien para ambos), mientras que la cuarta fila evidencia el *trade-off* identificado como riesgo R-06 (diferencia de cobertura inter-proveedor): sobre el *dataset* difuso, Groq pierde las familias `keys` / `key_stats` y `analytics` / `analytics_stats`, las menos representadas en el corpus. La quinta fila confirma RU-5.1: el agente recupera los cuatro *schemas* declarativos de Spruce sin intervención manual. La sexta fila documenta el caso end-to-end más rico ejecutado durante el proyecto; la séptima refleja la materialización de R-02.

Tres ejecuciones independientes del agente sobre Habitica con Google (el mismo *prompt*, el mismo modelo) produjeron 5, 11 y 22 archivos seleccionados respectivamente. Este rango se reporta de forma intencional para alinearse con la lección L7 del capítulo 3 (honestidad estadística).

### 11.3.4 Reproducibilidad de los resultados reportados

Los artefactos de las ejecuciones reportadas en §11.3.3 se conservan en el repositorio bajo `out-*` por *dataset* (`out-spruce/`, `out-difuso/`, `out-spruce-url/`, `out-habitica-2026-06-01/`). La marca temporal y el modelo concreto utilizado en cada ejecución se identifican por la cabecera del propio directorio y por la traza `[mm:ss]` de `_log.py`. Las invocaciones exactas reproducibles son:

```
python -m normalizer data/spruce/ --out-dir out-spruce/
python -m normalizer data/spruce-difuso/ --provider groq --out-dir out-difuso-groq/
python -m normalizer https://github.com/dan-divy/spruce --out-dir out-spruce-url/
python -m normalizer https://github.com/HabitRPG/habitica --out-dir out-habitica/
```

Esta política de reproducibilidad responde a RNF-2.1: los artefactos quedan disponibles para inspección por la dirección académica y por el tribunal, y constituyen la evidencia empírica que sustenta las afirmaciones del capítulo 9 (Conclusiones).
