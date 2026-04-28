# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

---

## 1. Objetivo inmediato

Construir un **programa que, dado un archivo con schemas MongoDB, llame a la API de Gemini/Gemma y produzca automáticamente un modelo relacional normalizado en DDL** — replicando mediante código y APIs el proceso que hasta ahora se realizaba manualmente en interfaces de chat.

**Hito:** prototipo funcional listo para mostrar en la siguiente reunión con tutores.

**Decisiones ya tomadas:**

- API principal: **Google Generative AI (Gemini / Gemma)**
- Formato de entrada del prototipo: **archivo con schemas MongoDB** (el usuario le pasa un archivo al programa)
- Output esperado: DDL Oracle

**Decisiones pendientes (a discutir al arrancar):**

- Lenguaje y stack — se valoran Python (ecosistema LLM) y Java (experiencia previa del autor)
- Estrategia: prompt único vs. pipeline multi-paso (la fase experimental sugiere que multi-paso da mejores resultados)
- Forma de invocación: script CLI, función importable, API mínima

**Fuera del alcance de esta fase:**

- UI o frontend
- Soporte multi-proveedor (vendrá después)
- Análisis automático de repositorios (requiere agentes, demasiado complejo para el tiempo disponible)
- Soporte de todos los formatos de entrada de la visión completa

**Datos de prueba disponibles:**
Los schemas del repositorio [Spruce](https://github.com/dan-divy/spruce) se usaron en la fase experimental y sirven como input de referencia para probar el prototipo. Existe un modelo relacional manual (baseline) para comparar los resultados.

---

## 2. Primeros pasos sugeridos

Cuando se arranque una sesión nueva sin código existente, el orden recomendado es:

1. Decidir lenguaje y stack con el autor
2. Inicializar el proyecto (gestor de paquetes, dependencias mínimas, gitignore)
3. Crear estructura de carpetas básica
4. Preparar los schemas de Spruce como archivo de input de prueba
5. Implementar la lectura y parseo del archivo de schemas
6. Integrar la API de Gemini/Gemma
7. Iterar sobre el pipeline hasta producir DDL válido
8. Comparar el DDL generado con el baseline manual

---

## 3. Contexto del TFG

### Datos del proyecto

- **Título:** "Uso de LLMs para la transformación de modelos desnormalizados en bases de datos NoSQL orientadas a documentos en modelos normalizados"
- **Autor:** Daniel Uría Edroso (UO282813)
- **Universidad:** Universidad de Oviedo — Grado en Ingeniería Informática del Software
- **Curso:** 2025 / 2026
- **Tipo:** TFG de investigación con desarrollo de herramienta
- **Tutores:** María José Suárez Cabal / Pablo Suárez-Otero González

### Problema que aborda

Las bases de datos NoSQL orientadas a documentos (MongoDB) almacenan datos desnormalizados. Migrarlos a un modelo relacional requiere identificar entidades, detectar relaciones implícitas, eliminar redundancia y diseñar claves primarias y foráneas. Es un proceso manual, complejo y propenso a errores. El TFG explora hasta qué punto los LLMs pueden automatizarlo.

### Spruce como dataset de prueba

[Spruce](https://github.com/dan-divy/spruce) es una aplicación real con MongoDB y schemas definidos explícitamente en el código. Se eligió como caso de estudio por su complejidad moderada y la claridad de sus definiciones de esquema.

Entidades del modelo relacional manual (baseline):
`USERS`, `USER_FOLLOWERS`, `POSTS`, `USER_NOTIFICATIONS`, `CHAT_ROOMS`, `CHAT_ROOM_MEMBERS`, `CHAT_MESSAGES`, `API_KEYS`, `API_KEY_STATS`, `ANALYTICS`, `ANALYTICS_STATS`.

El prototipo debería funcionar con cualquier archivo de schemas MongoDB, no solo con Spruce.

### Fase experimental previa (completada, vía chat)

Se evaluaron varios LLMs con el mismo input (schemas de Spruce):

| Modelo          | Modo              | Output                     |
| --------------- | ----------------- | -------------------------- |
| GPT-3.5         | Prompt directo    | DDL Oracle + UML           |
| GPT-5           | Prompt directo    | DDL Oracle + UML           |
| Claude Opus 4.6 | Prompt directo    | DDL Oracle + UML + índices |
| Claude Opus 4.6 | Agente (4 tareas) | DDL Oracle completo        |
| GPT-5.3-Codex   | Agente            | DDL Oracle completo        |

El pipeline multi-paso que mejores resultados produjo (Claude Opus 4.6 como agente):

1. Read all MongoDB Schema Models
2. Analyze Schemas and Relationships
3. Design normalized relational model
4. Generate Oracle DDL statements

Esta secuencia de pasos es una referencia para diseñar el pipeline del prototipo.

### Visión completa de la herramienta (futuro, no este prototipo)

Requisitos de usuario de la herramienta final:

- **RU-1** — Formatos de entrada: archivo de schemas (RU-1.1), URL de repositorio (RU-1.2), texto directo (RU-1.3)
- **RU-2** — Análisis automático del modelo documental (entidades, atributos, relaciones)
- **RU-3** — Generación de modelo relacional normalizado (PKs, FKs, sin redundancia)
- **RU-4** — Generación de DDL SQL
- **RU-5** — Elección de LLM por el usuario
- **RU-6** — Independencia del modelo LLM concreto
- **RU-7** — Independencia del proveedor de API (Anthropic, OpenAI, Google…)

### Contexto profesional del autor

Trabaja con un sistema legacy basado en Oracle (~6000 tablas, Oracle Forms, SQL/PLSQL). Esto motiva el interés práctico en LLMs aplicados al análisis y migración de esquemas complejos, y justifica que el DDL de referencia sea **compatible con Oracle**.

### Documentación complementaria del TFG

Memoria, plantilla y documento de experimentos: `../tfg-memoria/`
