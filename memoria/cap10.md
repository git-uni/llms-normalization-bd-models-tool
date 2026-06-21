# Capítulo 10. Apéndices

## 10.1 Plan de gestión de riesgos

Este apéndice desarrolla el plan de gestión de riesgos referenciado en §3.1.4 y proporciona las hojas individuales de los doce riesgos identificados durante el proyecto, conforme a la recomendación de la plantilla del TFG.

### 10.1.1 Marco de referencia

La gestión de riesgos del proyecto sigue las recomendaciones de la norma **ISO 31000:2018 — Risk management — Guidelines** y se concreta sobre la práctica habitual del PMBOK 7.ª edición. El proceso se descompone en cinco actividades secuenciales que se realimentan a lo largo del proyecto: identificación, análisis cualitativo, planificación de la respuesta, seguimiento y registro.

### 10.1.2 Categorías y escalas

Los riesgos del proyecto se clasifican en tres categorías según su origen, todas ellas específicas del dominio *LLM-as-a-service* que diferencia este trabajo de un desarrollo software clásico:

- **Dependencia externa**: riesgos cuya materialización depende de un actor o sistema externo al control del autor (proveedores de LLM, retiradas de modelos, cambios de política, suspensión de cuentas).
- **Técnico**: riesgos relacionados con la viabilidad técnica de las decisiones adoptadas (compatibilidad de SDKs, fronteras de cuota, soporte irregular de *function calling*, *aliasing* silencioso de modelos).
- **Calidad**: riesgos que afectan a la calidad del resultado producido por el sistema (varianza del agente, cobertura inter-proveedor, sesgo del LLM, *drift* del *prompt*).

La probabilidad y el impacto se evalúan en una escala 1–5 cualitativa-cuantitativa:

| Valor | Probabilidad | Impacto |
|---|---|---|
| 1 | Muy baja (≤ 10 %) | Despreciable: no afecta al alcance ni al plazo. |
| 2 | Baja (10–30 %) | Menor: corregible con horas adicionales. |
| 3 | Media (30–60 %) | Moderado: requiere replanificación parcial. |
| 4 | Alta (60–80 %) | Mayor: pone en riesgo un paquete WBS completo. |
| 5 | Muy alta (≥ 80 %) | Crítico: pone en riesgo la entrega del proyecto. |

La **exposición** resultante (P × I, 1–25) define la urgencia de la respuesta:

- Exposición ≥ 12: **crítico** — plan de mitigación obligatorio antes de cualquier nueva tarea.
- Exposición entre 6 y 11: **alto** — plan de mitigación recomendado, contingencia preparada.
- Exposición entre 3 y 5: **moderado** — monitorizado con indicadores.
- Exposición ≤ 2: **bajo** — aceptado.

### 10.1.3 Plantilla de hoja de riesgo

Cada riesgo identificado se documenta con los siguientes campos:

| Campo | Descripción |
|---|---|
| Identificador | Código único R-NN del registro de riesgos. |
| Descripción | Enunciado claro del riesgo, evitando confundir causa con consecuencia. |
| Categoría | Una de las tres categorías (dependencia externa, técnico, calidad). |
| Probabilidad / Impacto / Exposición | Valoración inicial 1–5 × 1–5 y producto resultante. |
| Estrategia | Una de las cuatro estrategias canónicas: **evitar**, **mitigar**, **transferir**, **aceptar**. |
| Plan de mitigación | Acciones concretas a emprender para reducir la probabilidad o el impacto. |
| Indicadores de materialización | Eventos observables que avisarían de la cercanía del riesgo. |
| Plan de contingencia | Acciones a emprender si el riesgo se materializa pese a la mitigación. |
| Estado final | Resultado al cierre del proyecto: materializado y mitigado, materializado y aceptado, reducido, o no materializado. |

### 10.1.4 Hojas individuales de riesgo

A continuación se incluyen las doce hojas individuales correspondientes a los riesgos identificados en §3.1.4. Cinco de ellas se anticiparon en §3.2.3 con detalle completo; aquí se consolidan todas con la plantilla aplicada de forma uniforme.

#### R-01. Colapso del *free tier* de Google

| Campo | Valor |
|---|---|
| Categoría | Dependencia externa. |
| Probabilidad / Impacto / Exposición | 4 / 5 / 20 (crítico). |
| Estrategia | Mitigar. |
| Plan de mitigación | Implementar `GroqProvider` como proveedor alternativo desde el inicio del paquete P3 ("Abstracción de proveedor"); migrar al sucesor de `gemini-2.5-flash-lite` (`gemini-3.1-flash-lite`) cuando se libere. |
| Indicadores | Errores HTTP 429 persistentes; comunicaciones públicas del proveedor; mediciones empíricas registradas en `notes/2026-05-25-free-tier-google-y-alternativas.md`. |
| Contingencia | Migración temporal del agente a Groq (con la advertencia de R-02 para repositorios medianos+). |
| Estado final | Materializado en diciembre de 2025; mitigado mediante adopción de `gemini-3.1-flash-lite` y de `GroqProvider`. |

#### R-02. Frontera Groq × tamaño del árbol del repositorio

| Campo | Valor |
|---|---|
| Categoría | Técnico. |
| Probabilidad / Impacto / Exposición | 3 / 4 / 12 (crítico). |
| Estrategia | Mitigar. |
| Plan de mitigación | Documentar la frontera de TPM × tamaño del árbol; reservar Groq para el *pipeline* texto-a-texto y usar Google para el agente sobre repositorios medianos+. |
| Indicadores | HTTP 413 sobre la primera petición al LLM; medición del tamaño del árbol antes de invocar. |
| Contingencia | Uso forzado de Google para el agente; investigación del *dev tier* de Cerebras como ampliación. |
| Estado final | Materializado y aceptado como límite del *free tier* de Groq. |

#### R-03. Soporte irregular de *function calling* en modelos *open-weight*

| Campo | Valor |
|---|---|
| Categoría | Técnico. |
| Probabilidad / Impacto / Exposición | 4 / 3 / 12 (crítico). |
| Estrategia | Mitigar. |
| Plan de mitigación | Caracterización empírica del catálogo Groq: solo `qwen/qwen3-32b` y `meta-llama/llama-4-scout-17b-16e-instruct` validados como agentes; el resto descartados (Llama 3.x emite *markup* `<function=…>`, `gpt-oss-20b` produce JSON malformado, `gpt-oss-120b` emite *chain-of-thought* no parseable). |
| Indicadores | Errores `tool_use_failed` del SDK; salidas con *markup* no estructurado. |
| Contingencia | Forzar el modelo del agente a `qwen/qwen3-32b` (que es el valor por defecto en `DEFAULT_AGENT_MODELS`). |
| Estado final | Materializado y mitigado. La frontera está documentada en la traza experimental del proyecto como referencia futura. |

#### R-04. Alta varianza del agente sobre el mismo *input*

| Campo | Valor |
|---|---|
| Categoría | Calidad. |
| Probabilidad / Impacto / Exposición | 5 / 3 / 15 (crítico). |
| Estrategia | Mitigar parcialmente y aceptar el residuo. |
| Plan de mitigación | Tres palancas de *prompt engineering*: (i) Principio del hermano (filtro principal/secundario en el *pipeline*, no en el agente); (ii) dos pasadas obligatorias (declarativa + implícita); (iii) *batching* como regla dura. Árbol BFS con corte a 2 000 entradas. Documentación honesta del rango. |
| Indicadores | Variaciones >50 % en el número de archivos seleccionados sobre el mismo *input*. |
| Contingencia | Ejecución múltiple del agente y selección del mejor *run*; documentación del rango observado. |
| Estado final | Reducido (del rango 1–22 al rango 5–22 con prompt v5) y aceptado. |

#### R-05. Retirada o sustitución de modelos durante el desarrollo

| Campo | Valor |
|---|---|
| Categoría | Dependencia externa. |
| Probabilidad / Impacto / Exposición | 3 / 3 / 9 (alto). |
| Estrategia | Mitigar. |
| Plan de mitigación | Externalización de los nombres de modelos en `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`; documentación comentada de las migraciones. |
| Indicadores | Errores 404 / "model not found"; anuncios del proveedor. |
| Contingencia | Sustitución del modelo en `DEFAULT_MODELS` y re-validación con `data/spruce/`. |
| Estado final | Materializado en mayo de 2026 (retirada de Gemma 3 27B); mitigado mediante migración a `gemma-4-31b-it`. |

#### R-06. Diferencia de cobertura inter-proveedor

| Campo | Valor |
|---|---|
| Categoría | Calidad. |
| Probabilidad / Impacto / Exposición | 4 / 2 / 8 (alto). |
| Estrategia | Aceptar. |
| Plan de mitigación | Validación cualitativa sobre los dos proveedores; documentación honesta del *trade-off* en §11.3.3 y en §9.1.3. |
| Indicadores | Cobertura del UML manual significativamente distinta entre proveedores sobre el mismo *input*. |
| Contingencia | Recomendación por defecto del proveedor con mejor cobertura (Google para *datasets* difusos). |
| Estado final | Materializado y aceptado; documentado el *trade-off* velocidad (Groq sobre el *pipeline* texto-a-texto) ↔ calidad (Google sobre el agente en Habitica). |

#### R-07. Suspensión o limitación de cuentas de proveedor por uso intensivo

| Campo | Valor |
|---|---|
| Categoría | Dependencia externa. |
| Probabilidad / Impacto / Exposición | 2 / 3 / 6 (alto). |
| Estrategia | Aceptar. |
| Plan de mitigación | Cumplimiento de los términos de uso de los proveedores; uso responsable de los *free tiers*; vigilancia razonable durante las campañas de validación. |
| Indicadores | Notificaciones del proveedor; rechazos de autenticación persistentes. |
| Contingencia | Migración al otro proveedor disponible. |
| Estado final | No materializado. |

#### R-08. Cambios estructurales en políticas de uso del proveedor

| Campo | Valor |
|---|---|
| Categoría | Dependencia externa. |
| Probabilidad / Impacto / Exposición | 3 / 4 / 12 (crítico). |
| Estrategia | Mitigar. |
| Plan de mitigación | Diferente de R-01 (cuota numérica) y R-07 (cuenta individual): aquí se atacan los cambios estructurales que afectan a todos los usuarios del *free tier* (retirada completa, exigencia de verificación de pago, restricciones de uso académico, retirada simultánea de modelos demo-críticos). Mitigación: *snapshot* offline del *run* canónico sobre Spruce y Habitica (DDL, trazas del agente, *prompts* y *outputs* en disco) grabado con antelación a la defensa, utilizable como demo de respaldo sin invocar al proveedor; *fallback* claramente comunicable al tribunal si el sistema en vivo no responde; multi-proveedor reduce la exposición frente a un único cambio. |
| Indicadores | Anuncios oficiales del proveedor; cambios en los términos de servicio; foros y *subreddits* del SDK; cambios bruscos en las respuestas de la API en los días previos a la defensa. |
| Contingencia | Reproducción de la demo desde el *snapshot* offline; comunicación abierta del incidente al tribunal. |
| Estado final | No materializado a fecha de cierre del prototipo. *Snapshot* offline preparado como contingencia para la defensa. |

#### R-09. Breaking changes en los SDKs cliente

| Campo | Valor |
|---|---|
| Categoría | Técnico. |
| Probabilidad / Impacto / Exposición | 3 / 3 / 9 (alto). |
| Estrategia | Mitigar. |
| Plan de mitigación | Los SDKs `google-genai` y `groq` son jóvenes y siguen una cadencia de evolución rápida con riesgo de cambios incompatibles entre versiones. Mitigación mediante *pinning* de versiones en `requirements.txt`, *smoke test* tras cada actualización y aislamiento del SDK detrás de la abstracción `LLMProvider` para localizar el impacto en `providers/*.py`. |
| Indicadores | Errores `ImportError` / `AttributeError` al actualizar; avisos de *deprecation* en `stderr`; notas de versión del SDK. |
| Contingencia | Bloqueo de la versión funcional anterior; *rollback* del `requirements.txt`. |
| Estado final | No materializado: un único *bump* de versión durante el proyecto, compatible. |

#### R-10. Reenrutamiento silencioso del alias del modelo

| Campo | Valor |
|---|---|
| Categoría | Técnico. |
| Probabilidad / Impacto / Exposición | 2 / 2 / 4 (moderado). |
| Estrategia | Mitigar. |
| Plan de mitigación | A diferencia de R-05 (retirada formal), aquí el identificador del modelo se mantiene mientras el modelo subyacente cambia silenciosamente (*model aliasing*), alterando *outputs* entre *runs* aparentemente idénticos. Mitigación preventiva fijando IDs de modelo explícitamente versionados cuando el proveedor los ofrece, en lugar de alias genéricos. |
| Indicadores | Discrepancias en *outputs* entre *runs* con la misma configuración; cambios en los metadatos de la respuesta de la API. |
| Contingencia | Fijar la versión exacta del modelo en `DEFAULT_MODELS` y `DEFAULT_AGENT_MODELS`; re-validación contra la *baseline* de Spruce. |
| Estado final | No materializado: sin discrepancias observadas en *runs* idénticos durante el proyecto. |

#### R-11. Sesgo del LLM hacia modelos relacionales convencionales

| Campo | Valor |
|---|---|
| Categoría | Calidad. |
| Probabilidad / Impacto / Exposición | 4 / 2 / 8 (alto). |
| Estrategia | Mitigar. |
| Plan de mitigación | Los LLMs están mayoritariamente entrenados sobre modelos relacionales y pueden aplanar denormalizaciones legítimas o forzar agrupaciones que pierdan información presente en el modelo documental original. Mitigación en el *prompt* del paso 2 (`analyze.md`) y en la regla de reconciliación de FKs de `design.md` (cap. 2 §3.1.3); trazabilidad RU-2.3 permite detección humana del aplanamiento residual. |
| Indicadores | Pérdida de campos respecto al UML manual; agrupaciones forzadas; FKs que no respetan la multiplicidad observada. |
| Contingencia | Revisión cualitativa del DDL frente al modelo documental original; ajuste de los *prompts*. |
| Estado final | Reducido: aplanamientos detectados y corregidos vía *prompt engineering* durante P4; residuo aceptado. |

#### R-12. *Drift* del *prompt* del agente hacia un dataset concreto

| Campo | Valor |
|---|---|
| Categoría | Calidad. |
| Probabilidad / Impacto / Exposición | 3 / 3 / 9 (alto). |
| Estrategia | Mitigar. |
| Plan de mitigación | La iteración del *prompt* del agente sobre un único dataset (Spruce) podría optimizar el *prompt* para ese caso particular y degradar la generalización a otros repositorios. Mitigación mediante validación cruzada en cada iteración significativa: `data/spruce/` (caso de control) y URL pública de Habitica (caso de tamaño realista). El *drift* hacia Mongoose se ataca explícitamente en la pasada declarativa multi-*stack* del *prompt* v5.2. |
| Indicadores | Caída de cobertura en repositorios fuera del conjunto de iteración. |
| Contingencia | Reintroducir el dataset divergente en el conjunto de iteración del *prompt*. |
| Estado final | Reducido mediante la validación cruzada Spruce + Habitica en cada iteración del *prompt*. |

## 10.2 Referencias bibliográficas

Las referencias siguientes corresponden a las fuentes citadas a lo largo de la memoria. Se utiliza el estilo IEEE.

[1] ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*, International Organization for Standardization, Ginebra, 2018.

[2] IEEE 830-1998, *Recommended Practice for Software Requirements Specifications*, Institute of Electrical and Electronics Engineers, Nueva York, 1998. (Retirada en 2011, reemplazada por [1].)

[3] ISO/IEC/IEEE 15288:2015, *Systems and software engineering — System life cycle processes*, International Organization for Standardization, Ginebra, 2015.

[4] ISO 31000:2018, *Risk management — Guidelines*, International Organization for Standardization, Ginebra, 2018.

[5] Project Management Institute, *A Guide to the Project Management Body of Knowledge (PMBOK Guide)*, 7.ª ed. Newtown Square, PA: PMI, 2021.

[6] E. Gamma, R. Helm, R. Johnson y J. Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*. Reading, MA: Addison-Wesley, 1994.

[7] J. M. Redondo y P. J. Tuya González, *Plantilla TFG — Escuela Politécnica de Ingeniería de Gijón*, versión 2.1, Universidad de Oviedo, 2025. Proyecto de innovación docente PINN-19-A-029.

[8] Ministerio de Administraciones Públicas, *Metodología Métrica versión 3*, Madrid, 2001.

[9] OWASP Foundation, *OWASP Application Security Verification Standard (ASVS) — Nivel 1*, versión 4.0, 2019.

[10] Google LLC, *google-genai Python SDK Documentation*, 2025. [En línea]. Disponible: <https://github.com/googleapis/python-genai>.

[11] Google LLC, *Gemini API — Function Calling*, 2025. [En línea]. Disponible: <https://ai.google.dev/gemini-api/docs/function-calling>.

[12] Groq Inc., *Groq Python SDK Documentation*, 2025. [En línea]. Disponible: <https://github.com/groq/groq-python>.

[13] OpenAI, *Function Calling Guide*, 2025. [En línea]. Disponible: <https://platform.openai.com/docs/guides/function-calling>.

[14] Pallets Projects, *Click Documentation*, 2025. [En línea]. Disponible: <https://click.palletsprojects.com>.

[15] T. Schimansky, *CustomTkinter*, 2025. [En línea]. Disponible: <https://github.com/TomSchimansky/CustomTkinter>.

[16] *Spruce — Live Chat Web Application*, 2018. [En línea]. Disponible: <https://github.com/dan-divy/spruce>.

[17] HabitRPG / Habitica Authors, *Habitica — Open-Source Habit Building Web Application*, 2013–2026. [En línea]. Disponible: <https://github.com/HabitRPG/habitica>.

[18] Automattic Inc., *Mongoose — Elegant MongoDB Object Modeling for Node.js*, 2025. [En línea]. Disponible: <https://mongoosejs.com>.

[19] Oracle Corporation, *Oracle Database 23ai — Release Notes*, 2024. [En línea]. Disponible: <https://docs.oracle.com/en/database/oracle/oracle-database/23/>.
## 10.3 Contenido entregado en los anexos

### 10.3.1 Descripción del contenido

El anexo digital del Trabajo de Fin de Grado se entrega como un único fichero comprimido que contiene todos los elementos necesarios para reproducir el sistema, verificar los resultados y, en su caso, extenderlo. El contenido se ha adaptado a la naturaleza del proyecto (un paquete Python con CLI y GUI), divergiendo de la estructura por defecto recomendada por la plantilla (Java / Ant) que no aplica al *stack* utilizado.

El anexo se organiza en tres grandes bloques: el **código fuente** del paquete `normalizer`, los **datos** utilizados para la validación cualitativa y los **artefactos** producidos por las ejecuciones de validación.

### 10.3.2 Recomendación de la estructura de directorios

La estructura propuesta para el anexo digital es la siguiente:

```
anexo/
├── README.TXT                          # Punto de entrada del anexo
├── codigo/
│   ├── pyproject.toml
│   ├── normalizer/                     # Paquete Python completo
│   ├── memoria/                        # Borradores Markdown de los capítulos
│   ├── notes/                          # Documentos vivos y registros de sesión
│   └── .env.example                    # Plantilla de credenciales
├── instalacion/
│   ├── README.md                       # Procedimiento detallado de instalación
│   └── checklist.md                    # Comprobaciones post-instalación
├── documentacion/
│   ├── MemoriaTFG.pdf                  # Memoria en PDF navegable
│   └── diagramas/                      # Diagramas individuales en PNG
├── explotacion/
│   ├── data/
│   │   ├── spruce/                     # Dataset de control
│   │   └── spruce-difuso/              # Dataset realista
│   ├── runs/
│   │   ├── out-spruce/                 # Artefactos de validación
│   │   ├── out-difuso-google/          # Artefactos de validación
│   │   ├── out-spruce-url/             # Artefactos del modo URL
│   │   └── out-habitica-2026-06-01/    # Artefactos del caso realista
│   └── README.md                       # Guía de reproducción de las ejecuciones
└── presentacion/
    └── defensa.pdf                     # Diapositivas de la defensa
```

El fichero `README.TXT` en la raíz del anexo describe el contenido, indica las dependencias mínimas y resume el procedimiento de instalación referenciando los `README.md` de cada subdirectorio. El directorio `codigo/` contiene una copia limpia del repositorio en el momento de la entrega (sin `.cache/`, sin `out-*/` superfluos, sin `.env`). El directorio `documentacion/` incluye el PDF navegable de la memoria con los marcadores activos. El directorio `explotacion/` reproduce los *datasets* utilizados y los artefactos de las ejecuciones de validación que sustentan las afirmaciones cuantitativas de §11.3.3 y §9.1.2.
