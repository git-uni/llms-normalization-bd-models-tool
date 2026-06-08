# Capítulo 8. Conclusiones y Ampliaciones

Este capítulo cierra la memoria con una auto-evaluación del trabajo realizado frente a los requisitos del capítulo 3 y con la enumeración de las líneas de ampliación que el propio proyecto deja abiertas. Las conclusiones se centran en lo que efectivamente se ha aportado y en las lecciones —técnicas y metodológicas— que sintetizan la experiencia del proyecto; las ampliaciones recogen mejoras y extensiones identificadas durante el desarrollo.

## 8.1 Conclusiones

### 8.1.1 Cumplimiento de los requisitos de usuario

La tabla siguiente resume el grado de cobertura de cada uno de los ocho requisitos de usuario enunciados en el capítulo 3 frente a la evidencia observable en el sistema entregado.

| Requisito | Cobertura | Evidencia |
|---|---|---|
| RU-1.1 Carga desde archivo | Total | Ejecución end-to-end sobre `data/spruce/keys.js`; artefactos producidos. |
| RU-1.2 Carga desde directorio | Total | Ejecución end-to-end sobre `data/spruce-difuso/`; concatenación con marcas de origen. |
| RU-1.3 Análisis a partir de URL | Total | Ejecución sobre la URL pública de Spruce; clonado en caché, agente activo, evidencia agregada. |
| RU-2 Análisis del modelo documental | Total | Artefacto `02_analysis.md` con entidades, atributos, relaciones y trazas de evidencia. |
| RU-3 Generación del modelo relacional | Total | Artefactos `03_design.md` y `04_ddl.sql` en todos los casos validados. |
| RU-4 Independencia y configuración del proveedor de LLM | Total | Dos proveedores (Google, Groq) intercambiables sin cambios fuera de `providers/`. |
| RU-5 Uso de agentes para análisis de repositorios | Total | Agente con cinco herramientas (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`) sobre tres repositorios validados. |
| RU-6 Interfaz de uso (CLI + GUI) | Total | CLI Click y GUI CustomTkinter; misma capa de núcleo para ambas. |
| RU-7 Inspección de los resultados intermedios | Total | Cuatro artefactos del *pipeline* + traza del agente en directorios `--out-dir` aislados. |
| RU-8 Prototipo | Total | Validación cualitativa sobre los tres modos de entrada y desde ambas interfaces. |

La evaluación de los requisitos del sistema (RFs y RNFs del capítulo 4) sigue el mismo patrón: cada RF se traza a una decisión arquitectónica del capítulo 5 (§5.1.5) y a su materialización en un módulo del capítulo 6 (§6.1.1); cada RNF se acredita con la inspección del código y, cuando aplica, con las mediciones de §6.2.2.

### 8.1.2 Resultados cuantitativos

La cobertura del sistema sobre los *datasets* de referencia es la siguiente:

- **`data/spruce/`** (caso de control con *schemas* explícitos): cobertura **11/11** entidades del modelo UML manual con Google (Gemma 4 31B); cobertura **10/11** con Groq (Llama 3.3 70B). La única entidad perdida por Groq es marginal en el corpus.
- **`data/spruce-difuso/`** (mismo modelo, sin *schemas* declarativos): cobertura **11/11** con Google; **7/11** con Groq, perdiendo las familias `keys` / `key_stats` y `analytics` / `analytics_stats`.
- **URL pública de Spruce** (modo URL, agente activo): cobertura **11/11** del UML con un agente Gemini que selecciona los cuatro *schemas* declarativos del repositorio en cinco iteraciones.
- **URL pública de Habitica** (modo URL, validación cualitativa adicional): 31 tablas generadas, recuperando el modelo `User` descompuesto en 13 tablas y las familias `Tasks`, `Groups`, `Challenges`, `Messages`, `Webhooks`, `Subscriptions`, `Transactions` y `Tags`. No se recuperan `Coupon`, `Blocker`, `IapPurchaseReceipt`, `NewsPost`, `EmailUnsubscription`, `PushDevice` ni `Inbox`. La cobertura es satisfactoria como caso de tamaño realista pero no completa.

Sobre tres ejecuciones independientes del agente sobre Habitica con la misma configuración se observaron rangos de 5 a 22 archivos seleccionados. El sistema documenta de forma intencional este rango en lugar de un único número favorable, alineándose con la lección L7 ("honestidad estadística") del capítulo 2.

### 8.1.3 Reflexión sobre el techo del modelo

Una de las conclusiones más relevantes del trabajo, ya formulada como lección L1 del capítulo 2, es que **la capacidad del modelo elegido pone un techo a lo que el *prompt* puede lograr**. Sobre el mismo *prompt*, la jerarquía observada de modelos para el agente con *function calling* es:

`Gemini 3.1 Flash Lite` > `Qwen3-32B` > `Llama 4 Scout` ≫ `Llama 3.x` / `gpt-oss`

Esta jerarquía se traduce directamente en cobertura sobre el modelo de referencia: sobre Spruce, todos los modelos hasta `Llama 4 Scout` cierran el caso; sobre Habitica, solo Gemini lo aborda con éxito. La consecuencia metodológica del trabajo es que **invertir tiempo en *prompt engineering* tiene rendimientos decrecientes una vez se exprime el modelo elegido**, y que la mejora de la cobertura a partir de cierto punto requiere subir de modelo (con el coste correspondiente, si no es gratuito) o asumir el residuo de varianza.

### 8.1.4 Reflexión sobre el coste y la dependencia del *free tier*

La adopción inicial de un único proveedor (Google) resultó frágil tras el recorte de cuotas de diciembre de 2025. La incorporación del segundo proveedor (Groq) fue posterior y se motivó como mitigación del riesgo R-01. Esta experiencia confirma que, en proyectos académicos o de investigación que se apoyan en proveedores externos, **la abstracción multi-proveedor es una decisión arquitectónica con valor de gestión de riesgo**, no solo de elegancia técnica.

### 8.1.5 Reflexión final

Más allá del cumplimiento de los requisitos, el trabajo ha aportado tres elementos que el autor considera contribuciones genuinas para futuros proyectos similares: (i) una abstracción **`LLMProvider`** reducida a dos operaciones que ha probado ser suficiente para dos SDKs con paradigmas distintos (Google con `Content/Part`, Groq con formato OpenAI); (ii) un **agente con *function calling* nativo** cuya implementación cabe en menos de 250 líneas de Python sin depender de *frameworks* de agentes externos, lo que reduce drásticamente la superficie de mantenimiento; y (iii) un **enfoque metodológico** que combina rigor de ingeniería del *software* (29148 en requisitos, ISO 31000 en riesgos, patrones GoF en diseño) con honestidad estadística en los resultados (rango observado y no número único). Las tres aportaciones son transferibles a otros TFG que se apoyen en LLMs como herramienta y, en opinión del autor, constituyen el valor principal del trabajo para la comunidad académica.

## 8.2 Ampliaciones

Esta sección recoge seis líneas de ampliación que el propio proyecto deja abiertas: mejoras y extensiones identificadas durante el desarrollo.

### Ampliación A. Selección independiente de proveedores para *pipeline* y agente

En la versión actual, el *flag* `--provider` es único y obliga a usar el mismo proveedor para el *pipeline* y para el agente. Añadir un segundo *flag* `--agent-provider` independiente permitiría combinaciones útiles como "agente Google + *pipeline* Groq", que durante el desarrollo se ha probado de facto como respuesta a episodios transitorios de 5xx en Gemma. El cambio es localizado: se concentra en `cli.py` (un *option* adicional) y no requiere modificaciones en el resto del sistema, dado que `build_provider` ya admite invocaciones independientes para los dos roles.

### Ampliación B. Tercer proveedor: Z.ai

Z.ai constituye el candidato más prometedor para un tercer proveedor de LLM. Los modelos `GLM-4.5-Flash` y `GLM-4.7-Flash` están disponibles en *free tier* sin tarjeta de crédito, con 128 K de contexto (suficiente para absorber el árbol BFS de 2 000 entradas de Habitica sin chocar contra el TPM), soporte oficial de *function calling* y una API OpenAI-compatible que facilita la implementación. El único cuello observado del *free tier* —una sola petición concurrente— se cumple de manera trivial con el diseño actual, dado que el bucle del agente es secuencial.

La implementación consistiría en un módulo nuevo `normalizer/providers/zai.py` aproximadamente equivalente a `groq.py` con `base_url` y modelos por defecto distintos, y el registro en `_REGISTRY`, `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`. La validación seguiría el mismo patrón que para Groq: Spruce-URL primero (caso pequeño) y luego Habitica para comparar con la ejecución Google de referencia.

### Ampliación C. Suite de pruebas automatizadas

El plan de pruebas descrito en §4.3 y §5.3 contempla los niveles unitario, integración y sistema. Su materialización es la principal ampliación en el plano de la ingeniería del *software*: introducir `pytest` como armazón, `MockProvider` como doble de prueba para los niveles aislados del LLM, *fixtures* JSON con respuestas reales del SDK capturadas para los adaptadores, y `sqlparse` para la verificación sintáctica del DDL en el nivel de aceptación. La estructura del repositorio ya contempla esta ampliación con el directorio `tests/baseline/<dataset>.yaml` para los *checklists* de los casos de aceptación cualitativa.

### Ampliación D. Integración continua

Como continuación natural de la Ampliación C, la activación de GitHub Actions permitiría ejecutar la suite en cada *commit* y disponer de los análisis de seguridad SCA y SAST descritos en RNF-4.3. El esfuerzo es bajo (un único fichero YAML en `.github/workflows/`) y completaría la columna "Implementado" en la tabla de cumplimiento de RNFs.

### Ampliación E. Portabilidad del DDL a Oracle anterior a 23ai

El DDL generado utiliza el tipo `BOOLEAN`, soportado de forma nativa por Oracle 23ai pero ausente de las versiones anteriores. Un mapeo posterior trivial —`BOOLEAN` → `NUMBER(1) CHECK (X IN (0,1))` o `CHAR(1) CHECK (X IN ('Y','N'))`— ampliaría la portabilidad del DDL al universo Oracle <23, mayoritario en los entornos *legacy* objetivo. La ampliación puede materializarse como una opción adicional del *pipeline* (`--oracle-version 12c|19c|23ai`) o como un *postprocesador* externo aplicable al artefacto `04_ddl.sql`.

### Ampliación F. Reducción de la varianza del agente

La varianza observada del agente (5–22 archivos sobre Habitica) tiene tres palancas de reducción:

- **Herramienta `select_evidence_batch(items=[…])`**, que materialice el *batching* en una sola invocación y elimine la ambigüedad del *batching* implícito por consecutividad. El cambio se localiza en `discovery/tools.py`.
- **Agrupación de `select_evidence` consecutivos en `dispatch()`**, sin cambiar la interfaz expuesta al LLM. Solución alternativa más conservadora.
- **Nudges dinámicos**: tras cada `read_file`, devolver al agente la lista de archivos del mismo directorio que aún no ha leído. Esto ataca de forma directa el patrón "principal vs secundario". El cambio se concentra en `discovery/tools.py:_do_read_file` y en una pequeña ampliación de `DiscoveryState` para llevar la lista de archivos vistos.

Ninguna de las tres elimina la varianza por completo —es propiedad latente del modelo—, pero las tres reducen su techo de forma medible.
