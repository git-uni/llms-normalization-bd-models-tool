# Capítulo 2. Planificación y Gestión

Este capítulo describe la planificación, ejecución y cierre del proyecto desde la perspectiva de gestión, complementando la perspectiva técnica del resto de la memoria. Su contenido se estructura según las recomendaciones de la asignatura *Dirección y Planificación de Proyectos Informáticos* y la práctica habitual del PMBOK 7.ª edición.

El proyecto se desarrolla en el contexto de un Trabajo de Fin de Grado, con un único recurso técnico (el autor) y dos directores académicos (los tutores). Esta circunstancia condiciona la elaboración de la OBS y simplifica drásticamente la estructura de comunicación, pero no la del plan de riesgos: el carácter experimental del trabajo —dependencia de proveedores externos de LLM, naturaleza estocástica de los resultados— hace que la identificación y el seguimiento de los riesgos sea una de las actividades centrales de la gestión.

## 2.1 Planificación del proyecto

### 2.1.1 Identificación de interesados

Los interesados (*stakeholders*) del proyecto, ya identificados en §3.1 desde la perspectiva del sistema, se completan aquí con los actores del proyecto en sí:

- **Autor** (Daniel Uría Edroso, UO282813). Responsable único de análisis, diseño, implementación, validación y redacción.
- **Tutores** (María José Suárez Cabal y Pablo Suárez-Otero González, Departamento de Informática, Universidad de Oviedo). Responsables de la dirección académica, de la validación intermedia y de la aprobación de los hitos.
- **Tribunal de defensa**. Responsable de la evaluación final del trabajo.
- **Usuarios finales potenciales**. Desarrolladores y arquitectos de datos que pudieran adoptar la herramienta en el futuro. No participan en el proyecto pero condicionan decisiones de diseño (RU-6.2 GUI para usuarios no técnicos, RNF-3 usabilidad).
- **Comunidad científico-académica**. Lectores futuros de la memoria si el trabajo se publica o se reutiliza como base de proyectos posteriores.
- **Proveedores externos de LLM** (Google, Groq). No son interesados en sentido estricto pero condicionan la planificación: cuotas, retiradas de modelos y disponibilidad de la API impactan directamente en el plan de trabajo.

### 2.1.2 OBS y PBS

#### Estructura de descomposición de la organización (OBS)

La organización del proyecto es plana y única-recurso, lo que simplifica la OBS hasta hacerla trivial:

![Figura 2.1. Estructura de descomposición de la organización (OBS)](assets/png/fig-02-1.png)

Aunque la OBS contiene un único recurso humano, distinguir explícitamente sus cuatro **roles** —analista, desarrollador, tester y redactor técnico— resulta útil para el cálculo de costes (§2.1.5) y para la atribución de horas en el seguimiento (§2.2).

#### Estructura de descomposición del producto (PBS)

El proyecto entrega tres productos diferenciados:

![Figura 2.2. Estructura de descomposición del producto (PBS)](assets/png/fig-02-2.png)

### 2.1.3 Planificación inicial. WBS y diagrama de Gantt

El proyecto se planifica como una sucesión de paquetes de trabajo (WBS) con un alto grado de paralelismo entre las actividades de redacción de memoria y las de desarrollo de la herramienta. La fase inicial es secuencial (estudios previos → primer prototipo); a partir del primer prototipo, las iteraciones sobre la herramienta y la redacción de los capítulos correspondientes corren en paralelo. La metodología de trabajo es **iterativa** (cada hito técnico se consolida con una revisión con los tutores) más que estrictamente ágil: no hay *sprints* fijos sino entregables identificables.

#### WBS

La estructura de descomposición del trabajo se organiza en tres niveles. El **nivel 1** agrupa las cuatro fases del ciclo de vida del proyecto: *Inicio*, *Desarrollo* (paquetes P1–P7 y P10), *Documentación y cierre* (P8, P9). El **nivel 2** son los diez paquetes de trabajo (P1–P10) — cada uno con un hito de cierre identificable y un único responsable. El **nivel 3** descompone cada paquete en actividades planificables, con su predecesor lógico, duración estimada en días laborables, fechas planificadas, rol responsable y entregable. La codificación jerárquica `n.m` (con `n` el paquete y `m` la actividad) materializa la trazabilidad entre niveles. El esfuerzo agregado coincide con el presupuesto inicial (§2.1.5).

Roles utilizados en la columna **Resp.**: **AN** analista, **DEV** desarrollador, **TST** *tester*, **DOC** redactor técnico, **TUT** tutores (ver §2.1.2 OBS). Cuando una actividad implica más de un rol se indica el primario y el secundario separados por barra.

| Cód. | Actividad | Pred. | Dur. (d) | Inicio | Fin | Resp. | Entregable |
|---|---|---|---:|---|---|---|---|
| **F0** | **Fase 0. Inicio** | — | 10 | 2026-02-02 | 2026-02-13 | AN | Documento de objetivos |
| 0.1 | Aprobación del tema y nombramiento de dirección académica | — | 2 | 2026-02-02 | 2026-02-03 | AN/TUT | Acta de aceptación |
| 0.2 | Reunión de arranque y formalización del alcance preliminar | 0.1 | 1 | 2026-02-04 | 2026-02-04 | AN/TUT | Acta de reunión |
| 0.3 | Borrador inicial de objetivos, alcance y plan de trabajo | 0.2 | 7 | 2026-02-05 | 2026-02-13 | AN | Plan inicial (cap. 1 *draft*) |
| **P1** | **P1. Estudios previos** | F0 | 45 | 2026-02-16 | 2026-04-15 | AN | Decisión de viabilidad + diseño del *pipeline* |
| 1.1 | Revisión de literatura sobre LLMs aplicados a normalización y modelado relacional | 0.3 | 15 | 2026-02-16 | 2026-03-06 | AN | Estado del arte |
| 1.2 | Revisión del estado del arte de *function calling* y agentes con LLM | 1.1 | 8 | 2026-03-09 | 2026-03-18 | AN | Notas técnicas |
| 1.3 | Selección y análisis del repositorio Spruce como dataset de referencia | 1.1 | 4 | 2026-03-09 | 2026-03-12 | AN | Mapa del repo + UML manual |
| 1.4 | Experimento manual: extracción de DDL vía interfaz de *chat* con cuatro modelos (GPT-3.5, GPT-5, Claude Opus 4.6, GPT-5.3-Codex) | 1.3 | 12 | 2026-03-19 | 2026-04-03 | AN/TST | Comparativa cuantitativa |
| 1.5 | Diseño preliminar del *pipeline* multi-paso de cuatro fases | 1.4 | 6 | 2026-04-06 | 2026-04-13 | AN | Diseño del *pipeline* |
| 1.6 | Documento de viabilidad y decisión *go/no-go* | 1.5 | 2 | 2026-04-14 | 2026-04-15 | AN/TUT | Acta de viabilidad |
| **P2** | **P2. Prototipo base del *pipeline*** | P1 | 12 | 2026-04-16 | 2026-04-30 | DEV | Ejecución end-to-end sobre Spruce |
| 2.1 | Esqueleto del proyecto Python y *layout* `normalizer/` (CLI con *click*) | 1.6 | 2 | 2026-04-16 | 2026-04-17 | DEV | Esqueleto del repo |
| 2.2 | Curado del dataset `data/spruce/` (cuatro *schemas* Mongoose) | 2.1 | 1 | 2026-04-20 | 2026-04-20 | AN | `data/spruce/` |
| 2.3 | Implementación de los cuatro pasos del *pipeline* (lectura, análisis, diseño, DDL) | 2.1 | 5 | 2026-04-20 | 2026-04-24 | DEV | `pipeline.py` |
| 2.4 | Redacción inicial de los *prompts* y placeholders `{evidence}/{analysis}/{design}` | 2.3 | 2 | 2026-04-23 | 2026-04-24 | AN/DEV | `prompts/*.md` |
| 2.5 | Curado del dataset `data/spruce-difuso/` (8 ficheros de servidor) | 2.2 | 2 | 2026-04-27 | 2026-04-28 | AN | `data/spruce-difuso/` |
| 2.6 | Validación end-to-end sobre los dos datasets y refinamiento de `design.md` (regla de reconciliación de FKs) | 2.4,2.5 | 2 | 2026-04-29 | 2026-04-30 | TST/DEV | Traza de ejecución + `design.md` v2 |
| **P3** | **P3. Abstracción del proveedor LLM** | P2 | 18 | 2026-04-29 | 2026-05-22 | DEV | CLI multi-proveedor con `GoogleProvider` |
| 3.1 | Diseño del `Protocol LLMProvider` y de las *dataclasses* neutras (`Message`, `ToolSpec`, `ToolCall`, `ChatResponse`) | 2.3 | 3 | 2026-04-29 | 2026-05-01 | AN/DEV | `providers/base.py` |
| 3.2 | *Registry* + *factory* `build_provider(for_agent=...)` y dos modelos por proveedor (`DEFAULT_MODELS`, `DEFAULT_AGENT_MODELS`) | 3.1 | 2 | 2026-05-04 | 2026-05-05 | DEV | `providers/__init__.py` |
| 3.3 | Implementación de `GoogleProvider` (`google-genai` SDK) con `generate()` y `chat()` | 3.2 | 5 | 2026-05-06 | 2026-05-12 | DEV | `providers/google.py` |
| 3.4 | *Refactor* del *pipeline* para depender únicamente de la abstracción | 3.3 | 2 | 2026-05-13 | 2026-05-14 | DEV | `pipeline.py` desacoplado |
| 3.5 | Extracción de *prompts* a `normalizer/prompts/*.md` cargados al importar | 3.4 | 2 | 2026-05-15 | 2026-05-18 | DEV | `prompts/__init__.py` |
| 3.6 | Configuración segura de credenciales (variables de entorno, `.env` gitignored) | 3.3 | 1 | 2026-05-19 | 2026-05-19 | DEV | Documentación de despliegue |
| 3.7 | Validación de regresión del *pipeline* multi-proveedor | 3.5,3.6 | 3 | 2026-05-20 | 2026-05-22 | TST | Traza de ejecución |
| **P4** | **P4. Agente de descubrimiento** | P3 | 14 | 2026-05-20 | 2026-06-02 | DEV | Selección autónoma sobre Spruce desde URL |
| 4.1 | Diseño del bucle agéntico con *tool-use* nativo del SDK | 3.3 | 2 | 2026-05-20 | 2026-05-21 | AN | Diseño en `notes/` |
| 4.2 | Implementación de las cinco herramientas (`list_dir`, `read_file`, `grep`, `select_evidence`, `done`) y `dispatch()` | 4.1 | 3 | 2026-05-22 | 2026-05-24 | DEV | `discovery/tools.py` |
| 4.3 | Clonado de repositorios con cache local (`git clone --depth 1`) y validación anti *path-traversal* | 4.2 | 1 | 2026-05-24 | 2026-05-24 | DEV | `discovery/repo.py`, `filesystem.py` |
| 4.4 | Recorrido del árbol BFS con *cap* 2 000 entradas (`build_tree_summary`) | 4.3 | 1 | 2026-05-25 | 2026-05-25 | DEV | `filesystem.py` |
| 4.5 | Observabilidad por *stderr* `[mm:ss]` (helper `_log.py`) y reintentos extendidos a 5xx en `GoogleProvider` | 4.2 | 1 | 2026-05-25 | 2026-05-25 | DEV | `_log.py` |
| 4.6 | Iteración del *prompt* de sistema v1 → v5.2 (principio del hermano, dos pasadas obligatorias, *batching*) | 4.4 | 5 | 2026-05-26 | 2026-06-01 | AN/TST | `discovery_system.md` v5.2 |
| 4.7 | Validación autónoma sobre Spruce-URL (4/4 *schemas* recuperados, 11/11 entidades en DDL) | 4.6 | 2 | 2026-06-01 | 2026-06-02 | TST | Traza `discovery.md` |
| **P5** | **P5. Segundo proveedor (Groq)** | P3 | 7 | 2026-05-19 | 2026-05-27 | DEV | Multi-proveedor operativo |
| 5.1 | Implementación de `GroqProvider` con SDK OpenAI-compatible | 3.3 | 2 | 2026-05-19 | 2026-05-20 | DEV | `providers/groq.py` |
| 5.2 | Caracterización del catálogo Groq (Qwen3-32B, Llama-4-Scout, *gpt-oss-20b/120b*, `groq/compound-*`) | 5.1 | 3 | 2026-05-21 | 2026-05-25 | TST | Notas en `notes/2026-05-25-groq-provider.md` |
| 5.3 | Fijado del modelo por defecto del agente Groq a `qwen/qwen3-32b` | 5.2 | 1 | 2026-05-26 | 2026-05-26 | DEV | `DEFAULT_AGENT_MODELS` |
| 5.4 | Validación end-to-end con Groq sobre `data/spruce/` | 5.3 | 1 | 2026-05-27 | 2026-05-27 | TST | Traza de ejecución |
| **P6** | **P6. Validación experimental** | P4,P5 | 6 | 2026-05-28 | 2026-06-02 | TST | Cobertura UML satisfactoria sobre Habitica |
| 6.1 | Diseño experimental: definición de métricas (cobertura UML, número de archivos/iter, *wall-clock*, 429s absorbidos) | 4.7 | 1 | 2026-05-28 | 2026-05-28 | AN/TST | Plan de pruebas |
| 6.2 | Ejecución sobre Habitica × Google (`gemini-3.1-flash-lite`, run 2026-06-01) | 6.1 | 2 | 2026-05-29 | 2026-06-01 | TST | `out-habitica-2026-06-01/` |
| 6.3 | Caracterización empírica de la frontera Groq × tamaño del árbol (HTTP 413 con `qwen/qwen3-32b` 6K TPM y Llama-4-Scout 30K TPM) | 6.1 | 2 | 2026-05-29 | 2026-06-01 | TST | Anotaciones en `CLAUDE.md` |
| 6.4 | Descarte de Cerebras (cap 8 192 *tokens* en *free tier*) | 6.3 | 1 | 2026-06-02 | 2026-06-02 | TST | Comprobación en `notes/` |
| 6.5 | Consolidación de lecciones aprendidas en `CLAUDE.md` y `notes/` | 6.2,6.3,6.4 | 1 | 2026-06-02 | 2026-06-02 | DOC | `CLAUDE.md` actualizado |
| **P7** | **P7. Interfaz gráfica (GUI)** | P6 | 9 | 2026-06-03 | 2026-06-15 | DEV | Reproducción manual de los tres casos desde la GUI |
| 7.1 | Diseño de las cinco pantallas guiadas y *wireframes* | 6.5 | 2 | 2026-06-03 | 2026-06-04 | AN | *Wireframes* |
| 7.2 | Esqueleto de la GUI con CustomTkinter y navegación entre pantallas | 7.1 | 2 | 2026-06-05 | 2026-06-08 | DEV | Esqueleto de la GUI |
| 7.3 | Conexión de la GUI con el núcleo (CLI/`pipeline.py`/agente) | 7.2 | 3 | 2026-06-09 | 2026-06-11 | DEV | GUI conectada |
| 7.4 | Validación manual de los tres casos (`data/spruce/`, `data/spruce-difuso/`, Spruce-URL) | 7.3 | 2 | 2026-06-12 | 2026-06-15 | TST | Trazas de uso |
| **P10** | **P10. Agente de refinamiento (RU-6)** | P7 | 8 | 2026-06-16 | 2026-06-25 | DEV | Diálogo de refinamiento sobre `04_ddl.sql` |
| 10.1 | Diseño del bucle agéntico de refinamiento sobre el resultado del *pipeline* | 7.4 | 1 | 2026-06-16 | 2026-06-16 | AN | Diseño en `notes/` |
| 10.2 | Implementación de las *tools* de edición textual (`replace_text`, `add_text`, `delete_text`) | 10.1 | 3 | 2026-06-17 | 2026-06-19 | DEV | `refinement/tools.py` |
| 10.3 | Iteración del *prompt* de sistema (RU-6.1 verbos: renombrar, fusionar, dividir) | 10.2 | 2 | 2026-06-22 | 2026-06-23 | AN/DEV | `refinement_system.md` |
| 10.4 | Validación cualitativa con dos sesiones de refinamiento sobre el DDL de Spruce | 10.3 | 2 | 2026-06-24 | 2026-06-25 | TST | Trazas de refinamiento |
| **P8** | **P8. Memoria (transversal)** | F0 | 88 | 2026-02-16 | 2026-06-17 | DOC | Documento final aprobado |
| 8.1 | Capítulo 1. Descripción general del trabajo | 0.3 | 4 | 2026-02-16 | 2026-02-19 | DOC | `cap01.md` |
| 8.2 | Capítulo 3. Requisitos de usuario | 1.5 | 6 | 2026-04-06 | 2026-04-13 | DOC | `cap03.md` |
| 8.3 | Capítulo 4. Análisis del sistema | 2.6 | 8 | 2026-05-01 | 2026-05-12 | DOC | `cap04.md` |
| 8.4 | Capítulo 5. Diseño del sistema | 3.7 | 10 | 2026-05-13 | 2026-05-26 | DOC | `cap05.md` |
| 8.5 | Capítulo 6. Implementación | 5.4 | 5 | 2026-05-28 | 2026-06-03 | DOC | `cap06.md` |
| 8.6 | Capítulo 7. Pruebas | 6.5 | 4 | 2026-06-03 | 2026-06-08 | DOC | `cap07.md` |
| 8.7 | Capítulo 2. Planificación y gestión | 8.5 | 4 | 2026-06-04 | 2026-06-09 | DOC | `cap02.md` |
| 8.8 | Capítulo 8. Conclusiones y trabajo futuro | 7.4 | 3 | 2026-06-15 | 2026-06-17 | DOC | `cap08.md` |
| 8.9 | Capítulo 9. Apéndices (hojas de riesgo, glosario, manuales) | 8.7 | 2 | 2026-06-10 | 2026-06-11 | DOC | `cap09.md` |
| 8.10 | Generación de figuras (Mermaid → PNG vía *build script*) | 8.4 | 2 | 2026-06-08 | 2026-06-09 | DOC | `assets/png/*` |
| 8.11 | Revisiones intermedias con dirección (4 reuniones de tutoría) | 8.1 | — | 2026-03-01 | 2026-06-15 | TUT/DOC | Actas de revisión |
| 8.12 | Revisión final ortográfica/gramatical y maquetación a `.docx` | 8.9 | 3 | 2026-06-12 | 2026-06-17 | DOC | `MemoriaTFG.vN.docx` |
| **P9** | **P9. Cierre y defensa** | P8 | 8 | 2026-06-15 | 2026-06-25 | AN | Acta de defensa |
| 9.1 | Preparación de la presentación (diapositivas y demo en vivo) | 8.12 | 4 | 2026-06-15 | 2026-06-18 | DOC/AN | `presentacion.pdf` |
| 9.2 | Entrega telemática del trabajo en la aplicación de TFG | 8.12 | 1 | 2026-06-17 | 2026-06-17 | AN | Justificante de entrega |
| 9.3 | Ensayo de la defensa con dirección | 9.1 | 2 | 2026-06-19 | 2026-06-22 | AN/TUT | Acta de revisión |
| 9.4 | Defensa pública ante el tribunal | 9.3 | 1 | 2026-06-25 | 2026-06-25 | AN | Acta de defensa |

#### Comentario del WBS

El **camino crítico** del proyecto, en su planificación inicial, recorre 0.3 → 1.5 → 1.6 → 2.6 → 3.7 → 4.7 → 6.5 → 7.4 → 10.4 → 8.12 → 9.4. Las actividades 4.6 (iteración del *prompt* del agente) y 6.2 (validación Habitica) concentran el riesgo de retraso por su naturaleza experimental: el rango observado de archivos seleccionados por el agente (5 a 22 sobre el mismo *input*, riesgo R-04) puede forzar a repetir 4.6 varias veces dentro de su ventana planificada.

Los paquetes técnicos P3 (abstracción) y P5 (Groq) se planifican con cierto solapamiento controlado: la implementación del `GroqProvider` (5.1) puede iniciarse en cuanto la abstracción está estable (3.3), sin esperar al cierre completo de P3. Esta concurrencia es la principal palanca para acortar el plan general y materializa el principio arquitectónico de que "añadir un proveedor es un *copy-paste*" (cap. 5).

El paquete **P8 (Memoria)** corre en paralelo desde la finalización de F0; los capítulos se redactan en la ventana inmediatamente posterior al cierre del paquete técnico que documentan, salvo el cap. 2 (planificación y gestión), que requiere la traza completa del proyecto y se redacta hacia el final. Las **revisiones de dirección** (8.11) son hitos discretos distribuidos a lo largo del proyecto que no consumen días laborables del autor sino horas del rol TUT, reflejadas en el presupuesto (§2.1.5).

El paquete **P10 (Agente de refinamiento)** está inicialmente planificado tras el cierre de P7, en una ventana muy ajustada que comparte el cierre con la propia defensa (riesgo R-08, sec. 2.1.4). Esa tensión de planificación es precisamente la que materializa el riesgo y motiva el descope en LB-2 (§2.2.2, §2.3.1).

#### Diagrama de Gantt

El diagrama de Gantt resume la distribución temporal de los paquetes WBS sobre el periodo del proyecto (febrero–junio de 2026), con las actividades de nivel 3 anidadas dentro de su paquete. Por legibilidad, las actividades de duración inferior a tres días se agregan en su paquete contenedor; el detalle granular de cada actividad se encuentra en la tabla WBS anterior. Los paquetes técnicos (P1–P7, P10) corren en serie hasta P3 y a partir de ahí muestran solapamiento por la naturaleza iterativa del trabajo; la memoria (P8) corre en paralelo desde el inicio.

![Figura 2.3. Diagrama de Gantt del proyecto](assets/png/fig-02-3.png)

### 2.1.4 Riesgos

#### Plan de gestión de riesgos

La gestión de riesgos sigue las recomendaciones de la norma ISO 31000 ([4]) y de PMBOK 7. El procedimiento consta de cinco actividades: identificación, análisis cualitativo (probabilidad × impacto), planificación de la respuesta, seguimiento y registro. La política de aceptación se define en términos de **exposición** (P × I, escala 1–5 × 1–5 = 1–25):

- Exposición ≥ 12: riesgo **crítico**, plan de mitigación obligatorio antes de cualquier nueva tarea.
- Exposición entre 6 y 11: riesgo **alto**, plan de mitigación recomendado, contingencia preparada.
- Exposición entre 3 y 5: riesgo **moderado**, monitorizado con indicadores.
- Exposición ≤ 2: riesgo **bajo**, aceptado.

Las hojas individuales de cada riesgo, con su descripción completa, indicadores de materialización y plan de contingencia, se incluyen en el apéndice 9.1 conforme a la recomendación de la plantilla.

#### Identificación de riesgos

Se identifican doce riesgos, agrupados en cuatro categorías: dependencia externa, técnico, calidad y gestión.

| ID | Categoría | Descripción resumida |
|---|---|---|
| R-01 | Dependencia externa | Colapso de la cuota del *free tier* de Google. |
| R-02 | Técnico | Frontera entre Groq *free tier* y el tamaño del árbol del repositorio en repositorios medianos. |
| R-03 | Técnico | Soporte irregular de *function calling* en los modelos *open-weight* hospedados por Groq. |
| R-04 | Calidad | Alta varianza del agente sobre el mismo *input*. |
| R-05 | Dependencia externa | Retirada o sustitución de modelos durante el desarrollo. |
| R-06 | Dependencia externa | Inviabilidad de un tercer proveedor (Cerebras) por cap de contexto en *free tier*. |
| R-07 | Calidad | Patrón "principal vs secundario" del agente: cerrar el descubrimiento tras leer pocos archivos del directorio de modelos. |
| R-08 | Gestión | Tiempo limitado para implementar todos los requisitos planificados, en particular el agente de refinamiento. |
| R-09 | Técnico | Generación de tipos no nativos en Oracle <23 (uso de `BOOLEAN`). |
| R-10 | Calidad | Diferencia significativa de cobertura entre proveedores sobre el mismo *input*. |
| R-11 | Gestión | Pérdida de trabajo por falta de control de versiones disciplinado. |
| R-12 | Dependencia externa | Suspensión o limitación de cuentas de proveedor por uso intensivo en pruebas. |

#### Registro de riesgos (probabilidad × impacto inicial)

Los valores siguientes corresponden a la evaluación realizada al inicio del proyecto. La evolución del registro durante la ejecución se detalla en §2.2.3 y el cierre en §2.3.2.

| ID | Probabilidad | Impacto | Exposición | Estrategia | Categoría |
|---|---|---|---|---|---|
| R-01 | 4 | 5 | 20 | Mitigar | Crítico |
| R-02 | 3 | 4 | 12 | Mitigar | Crítico |
| R-03 | 4 | 3 | 12 | Mitigar | Crítico |
| R-04 | 5 | 3 | 15 | Aceptar / Mitigar parcial | Crítico |
| R-05 | 3 | 3 | 9 | Mitigar | Alto |
| R-06 | 3 | 2 | 6 | Aceptar | Alto |
| R-07 | 4 | 3 | 12 | Mitigar | Crítico |
| R-08 | 4 | 4 | 16 | Mitigar | Crítico |
| R-09 | 2 | 2 | 4 | Aceptar | Moderado |
| R-10 | 4 | 2 | 8 | Aceptar | Alto |
| R-11 | 2 | 5 | 10 | Mitigar | Alto |
| R-12 | 2 | 3 | 6 | Aceptar | Alto |

### 2.1.5 Presupuesto inicial

#### Presupuesto de costes

El proyecto no tiene cliente externo: el coste se calcula como horas de trabajo del autor y de los tutores. La estimación inicial considera 300 horas efectivas del autor distribuidas entre los cuatro roles y unas 24 horas de los tutores en reuniones de tutoría. Los costes por hora se toman del baremo recomendado para TFG por la propia plantilla (líneas 142–144 del extracto oficial), ajustado a tarifas habituales del mercado para perfiles junior en cada rol.

| Concepto | Horas | €/h | Coste estimado |
|---|---:|---:|---:|
| Autor — rol analista (P1, requisitos, diseño) | 80 | 30 | 2 400 € |
| Autor — rol desarrollador (P2–P7) | 140 | 25 | 3 500 € |
| Autor — rol tester (validación cualitativa) | 30 | 22 | 660 € |
| Autor — rol redactor técnico (P8) | 50 | 22 | 1 100 € |
| Tutores — reuniones de dirección | 24 | 60 | 1 440 € |
| Infraestructura *cloud* (*free tier* Google + Groq) | — | — | 0 € |
| *Hardware* (equipo propio del autor, amortización despreciable) | — | — | 0 € |
| **Total estimado** | **324** | | **9 100 €** |

#### Presupuesto de cliente

No aplica: el proyecto es académico, sin cliente externo.

## 2.2 Ejecución del proyecto

### 2.2.1 Plan de seguimiento de la planificación

El seguimiento se materializa mediante tres **líneas base** que registran el estado de la planificación al cierre de hitos significativos. Las líneas base se reconstruyen a partir de la traza disponible en el repositorio del proyecto: `git log` (commits con fechas exactas) y los documentos vivos del directorio `notes/`, fechados explícitamente.

| Línea base | Fecha de corte | Estado |
|---|---|---|
| **LB-0. Planificación inicial** | 2026-02-15 | WBS, riesgos y presupuesto descritos en §2.1, antes de iniciar el desarrollo. |
| **LB-1. Línea base intermedia** | 2026-05-25 | Post-implementación del segundo proveedor (Groq) y primera validación experimental del agente sobre Habitica. Decisión de mantener la GUI dentro del alcance y el agente de refinamiento fuera. |
| **LB-2. Línea base de cierre del prototipo** | 2026-06-01 | Cierre técnico de los paquetes P1–P6 y consolidación de las lecciones aprendidas. Inicio del paquete P7 (GUI). |

### 2.2.2 Bitácora de incidencias del proyecto

La bitácora siguiente recoge los eventos relevantes acaecidos durante la ejecución, correlacionados con los *commits* del repositorio que los cierran y con los riesgos identificados que materializan.

| Fecha | Evento | Riesgo | Commit / referencia |
|---|---|---|---|
| 2026-04-28 | Primer esqueleto del prototipo y `CLAUDE.md` inicial. | — | `d37ce4e`, `83f33f6` |
| 2026-04-29 | Versión 0.2.0: el proveedor de LLM se puede elegir; *pipeline* desacoplado de Spruce. Datasets `spruce` y `spruce-difuso` consolidados. | — | `9f97ce2`, `867b545`, `4becf01` |
| 2026-05-24 | Primer *commit* del agente de descubrimiento; *fixes* post-validación. | — | `daf255b`, `8010b0e` |
| 2026-05-25 | Extracción de *prompts* a `normalizer/prompts/*.md`. | — | `f497393` |
| 2026-05-25 | Implementación del `GroqProvider` con SDK OpenAI-compatible. | — | `4946e05` |
| 2026-05-25 | Caracterización experimental: *gpt-oss-120b* descartado por *chain-of-thought* no parseable. | R-03 (materializado) | `29cb93d` |
| 2026-05-25 | Fijado modelo por defecto del agente Groq a `qwen/qwen3-32b`. | R-03 (mitigado) | `d623752` |
| 2026-05-25 | Documentación pública del colapso del *free tier* de Google y catálogo de alternativas. | R-01 (materializado) | `d560863` |
| 2026-05-25 | Adopción de `gemini-3.1-flash-lite` (500 RPD) como modelo por defecto del agente Google. | R-01 (mitigado) | `1668d91` |
| 2026-05-25 | Prompt v4 del agente + ampliación de `MAX_ITERS` y `MAX_FILES` a 30. Primera validación en Habitica. | R-04, R-07 | `6f7db5f` |
| 2026-05-25 | Trace turno-a-turno + prompt v5 (dos pasadas obligatorias + *batching*). | R-04, R-07 | `f5da046` |
| 2026-05-25 | Sustitución del recorrido DFS por BFS en `build_tree_summary`, con *cap* a 2 000 entradas. | R-02, R-07 | `fce52b2` |
| 2026-05-25 | Observabilidad por *stderr* con sello `[mm:ss]`. Reintentos de Google extendidos a 5xx. | RNF-2.2 | `137f416` |
| 2026-06-01 | Prompt v5.2 (pasada declarativa multi-*stack*). | R-04 | `5897106` |
| 2026-06-01 | Run completo Habitica × Google: cobertura satisfactoria; frontera Groq confirmada. Consolidación de lecciones. | R-02, R-04 | `eadfc35` |
| 2026-06-02 | Inicio del paquete P7 (GUI). | R-08 (asumido) | — |
| 2026-06-04 | Replanificación del alcance: descope explícito del paquete P10 (agente de refinamiento, RU-6) para asegurar la entrega. | R-08 (mitigado) | — |

### 2.2.3 Riesgos durante la ejecución

A continuación se detallan, en formato de hoja de riesgo, los cinco riesgos cuya materialización o evolución condicionó significativamente la ejecución del proyecto. El registro completo de los doce se consolida en el apéndice 9.1.

#### Hoja de riesgo R-01 — Colapso del *free tier* de Google

| Campo | Valor |
|---|---|
| Descripción | El proveedor Google reduce drásticamente la cuota *free* de sus modelos Gemini en diciembre de 2025: `gemini-2.0-flash` queda con `limit: 0` y `gemini-2.5-flash-lite` con 20 peticiones por día, insuficientes para un agente que consume ~30 peticiones por sesión. |
| Categoría | Dependencia externa. |
| Probabilidad / Impacto / Exposición | 4 / 5 / 20 — Crítico. |
| Estrategia | Mitigar mediante implementación de un segundo proveedor (Groq) y mediante migración al nuevo modelo `gemini-3.1-flash-lite` (15 RPM / 250K TPM / 500 RPD) cuando se libera. |
| Indicadores | Cuotas devueltas en errores 429; documentación oficial del proveedor; mediciones empíricas (notes/2026-05-25-free-tier-google-y-alternativas.md). |
| Estado | **Materializado y mitigado.** Mantener vigilancia sobre futuros cambios de cuota. |

#### Hoja de riesgo R-02 — Frontera Groq × tamaño del árbol

| Campo | Valor |
|---|---|
| Descripción | El árbol del repositorio que el agente recibe en su primer mensaje supera el *tokens per minute* del *free tier* de Groq sobre repositorios medianos+. `qwen/qwen3-32b` (6 K TPM) y `meta-llama/llama-4-scout-17b-16e-instruct` (30 K TPM) devuelven HTTP 413 sobre el árbol BFS de Habitica (~30–50 K *tokens*). |
| Categoría | Técnico. |
| Probabilidad / Impacto / Exposición | 3 / 4 / 12 — Crítico. |
| Estrategia | Mitigar mediante uso de Google para el agente en repositorios medianos+ y reservar Groq para el *pipeline* texto-a-texto (que sí cabe en TPM). Documentar el *trade-off* en CLAUDE.md y en la memoria. |
| Indicadores | HTTP 413; conteo de *tokens* del árbol antes de invocar. |
| Estado | **Materializado y aceptado** como límite del *free tier*. Se documenta como ampliación futura el uso del *dev tier* de Cerebras (sin *cap* diario). |

#### Hoja de riesgo R-04 — Alta varianza del agente

| Campo | Valor |
|---|---|
| Descripción | Sobre el mismo *input* (Habitica, mismo *prompt*, mismo modelo) se observan ejecuciones del agente con entre 5 y 22 archivos seleccionados. La varianza es propiedad latente del modelo y no se elimina con iteraciones del *prompt*. |
| Categoría | Calidad. |
| Probabilidad / Impacto / Exposición | 5 / 3 / 15 — Crítico. |
| Estrategia | Mitigar mediante (i) iteración del *prompt* con regla dura de *batching*, principio del hermano, dos pasadas obligatorias; (ii) reducción del techo de varianza con árbol BFS *cap* 2 000; (iii) documentación honesta del fenómeno en la memoria (rango, no número único). Aceptar el residuo. |
| Indicadores | Rango observado de archivos / iteraciones por *run*; cobertura mínima sobre el modelo de referencia. |
| Estado | **Reducido** pero no eliminado. La defensa del trabajo asume y documenta este límite. |

#### Hoja de riesgo R-08 — Tiempo limitado para todos los requisitos

| Campo | Valor |
|---|---|
| Descripción | El alcance inicial del trabajo (RU-1 a RU-9) incluía un agente de refinamiento interactivo con LLM (RU-6 original) y una GUI (RU-7.2 original). El tiempo restante del proyecto, dado el esfuerzo invertido en la validación del agente y en la implementación del segundo proveedor, es insuficiente para entregar ambos a un nivel de calidad defendible. |
| Categoría | Gestión. |
| Probabilidad / Impacto / Exposición | 4 / 4 / 16 — Crítico. |
| Estrategia | Mitigar mediante **descope explícito** del agente de refinamiento, justificado en LB-2 con el acuerdo de la dirección. La GUI se mantiene como cierre del prototipo. El agente de refinamiento se documenta como ampliación A en §8.2. |
| Indicadores | Estimación de horas restantes; complejidad real de la GUI tras prototipo inicial. |
| Estado | **Materializado y mitigado** mediante descope. El descope se considera una decisión de proyecto, no una concesión técnica: la abstracción `LLMProvider.chat(messages, tools)` queda diseñada para soportar el agente de refinamiento cuando se aborde. |

#### Hoja de riesgo R-11 — Pérdida de trabajo por mal control de versiones

| Campo | Valor |
|---|---|
| Descripción | Riesgo de perder trabajo si el repositorio no se gestiona con disciplina (rebases destructivos, fuerzas-push, archivos no versionados). |
| Categoría | Gestión. |
| Probabilidad / Impacto / Exposición | 2 / 5 / 10 — Alto. |
| Estrategia | Mitigar mediante uso disciplinado de Git desde el primer *commit* (`d37ce4e`), *commits* frecuentes con mensajes descriptivos, ramificación mínima y *backups* implícitos en `origin`. Política explícita en `CLAUDE.md` de no usar opciones destructivas sin autorización. |
| Indicadores | Tamaño de los *commits*; tiempo entre *commits*; archivos no versionados de larga duración. |
| Estado | **No materializado.** Política aplicada con éxito. |

## 2.3 Cierre del proyecto

### 2.3.1 Planificación final

La planificación final coincide en sus paquetes con la planificación inicial salvo por la eliminación del paquete **P10 (Agente de refinamiento)**. La decisión documentada en LB-2 (descope de RU-6) retira P10 del WBS final; las horas reservadas para sus cuatro actividades (10.1–10.4, ~12 días laborables) se redistribuyen a P7 (GUI) y P8 (memoria), donde resultan necesarias.

La diferencia entre lo planificado y lo realizado se concentra en tres áreas:

- **Paquete P3 (Abstracción de proveedor)** consumió más horas de las previstas (~ +25 %), por la necesidad de iterar sobre la forma de la abstracción para que cupiera `GroqProvider` sin distorsionar `GoogleProvider`. La inversión amortizó con creces: añadir el segundo proveedor (P5) llevó menos de un día.
- **Paquete P4 (Agente de descubrimiento)** consumió aproximadamente +50 % de las horas previstas por la cantidad de iteraciones del *prompt* necesarias para domar los patrones "principal vs secundario" y la alta varianza del agente. Es la fuente principal del *overrun* del proyecto.
- **Paquete P6 (Validación experimental)** se materializó como una serie de *runs* sobre repositorios reales en lugar de como un esfuerzo puntual. Su carácter exploratorio justifica el sobrecoste.

El conjunto del proyecto se cierra dentro del plazo académico de defensa, gracias al descope de R-08 (RU-6).

### 2.3.2 Informe final de riesgos

| ID | Estado final | Comentario |
|---|---|---|
| R-01 | Materializado y mitigado | El cambio a `gemini-3.1-flash-lite` y la implementación de Groq resolvieron la cuota. |
| R-02 | Materializado y aceptado | Documentada como ampliación futura. |
| R-03 | Materializado y mitigado | Modelos `qwen/qwen3-32b` y `meta-llama/llama-4-scout` validados; otros descartados. |
| R-04 | Reducido y aceptado | El rango observado se documenta honestamente. |
| R-05 | Materializado y mitigado | Gemma 3 retirada en mayo de 2026, sustituida sin pérdida. |
| R-06 | Aceptado | Cerebras *free tier* confirmado como inviable. |
| R-07 | Reducido y aceptado | Mitigado por *prompt* v5 y árbol BFS. |
| R-08 | Materializado y mitigado | Mediante descope de RU-6. |
| R-09 | Aceptado | `BOOLEAN` se mantiene; documentado como ampliación. |
| R-10 | Materializado y aceptado | Documentado el *trade-off* Google (calidad) vs Groq (velocidad). |
| R-11 | No materializado | Política aplicada con éxito. |
| R-12 | No materializado | Vigilancia razonable. |

### 2.3.3 Presupuesto final de costes

| Concepto | Horas finales | €/h | Coste final | Δ vs inicial |
|---|---:|---:|---:|---|
| Autor — rol analista | 75 | 30 | 2 250 € | −5 h |
| Autor — rol desarrollador | 175 | 25 | 4 375 € | +35 h |
| Autor — rol tester | 40 | 22 | 880 € | +10 h |
| Autor — rol redactor técnico | 70 | 22 | 1 540 € | +20 h |
| Tutores — reuniones | 26 | 60 | 1 560 € | +2 h |
| Infraestructura *cloud* | — | — | 0 € | — |
| **Total final** | **386** | | **10 605 €** | **+62 h / +1 505 €** |

El sobrecoste real (~17 %) es coherente con el *overrun* observado en P4 (agente). El uso exclusivo del *free tier* de los proveedores mantiene los costes de infraestructura en cero.

### 2.3.4 Informe de lecciones aprendidas

Las lecciones aprendidas durante el proyecto, ordenadas por su valor para trabajos futuros similares, son las siguientes.

**L1. El modelo es el techo del agente, no el *prompt*.** Iterar sobre el *prompt* mejora el resultado pero hay un techo ligado a la capacidad del modelo para honrar instrucciones complejas. Sobre el mismo *prompt*, Gemini supera a Qwen3-32B, que supera a Llama 4 Scout, que supera a Llama 3.x. La consecuencia operativa: invertir tiempo en *prompt engineering* tiene rendimientos decrecientes una vez se exprime el modelo elegido.

**L2. La abstracción de proveedor amortiza pronto si se diseña con dos modelos por proveedor.** Distinguir desde el principio entre el modelo del *pipeline* (texto a texto, barato) y el del agente (con *function calling*, más capaz) anticipa decisiones que de otro modo se tomarían sobre la marcha y se documentan mal.

**L3. *Function calling* nativo > bucle JSON manual.** El SDK del proveedor entrena el formato; intentar replicarlo con JSON parseado de la salida textual es frágil incluso con modelos grandes.

**L4. *Free tier* dimensionado para una sola ejecución diaria.** En Google, 500 RPD ≈ ~15 sesiones del agente; en Groq la frontera la pone el TPM sobre el árbol del repositorio. Planificar el trabajo asumiendo cuotas escasas y diseñar los presupuestos del agente (`max_iters`, `max_files`) en consecuencia.

**L5. Recorrido por anchura (BFS) en el árbol del repositorio.** Una primera implementación con DFS hacía invisible al agente directorios de primer nivel cuando otros se profundizaban antes. Cambiar a BFS con *cap* a 2 000 entradas garantiza la visibilidad de todos los directorios *top-level* y resuelve el problema con un coste de complejidad insignificante.

**L6. Observabilidad como inversión temprana.** El registro `[mm:ss]` por la salida de error estándar, instrumentado en el CLI, el *pipeline*, el agente y los proveedores, fue determinante en la depuración del agente y en el diagnóstico de la frontera Groq. Una hora de trabajo amortizada cien veces.

**L7. El descope explícito es preferible a la entrega parcial.** Mantener RU-6 en el alcance habría resultado en una implementación parcial e indefendible. El descope formalizado con la dirección, documentado en la memoria como ampliación A, libera horas para cerrar bien el resto.

**L8. Honestidad estadística defiende mejor que la magnificación.** Presentar el rango observado de cobertura del agente sobre Habitica (5 a 22 archivos) ayuda a la defensa más que un único número favorable; el tribunal valora el rigor metodológico.

---

**Referencias del capítulo**

[4] ISO 31000:2018 — *Risk management — Guidelines.*

[5] Project Management Institute, *A Guide to the Project Management Body of Knowledge (PMBOK Guide)*, 7.ª edición, 2021.
