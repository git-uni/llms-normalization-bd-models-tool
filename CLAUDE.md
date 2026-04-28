# CLAUDE.md — Prototipo TFG

> Archivo leído automáticamente por Claude Code al inicio de cada sesión.

---

## 1. Objetivo inmediato

Construir un **pipeline programático** que, dado un conjunto de schemas MongoDB, produzca automáticamente un modelo relacional normalizado en DDL — replicando mediante código el proceso que hasta ahora se realizaba manualmente en interfaces de chat.

**Hito:** prototipo funcional listo para mostrar en la siguiente reunión con tutores.

**Decisiones ya tomadas:**
- API principal: **Google Generative AI (Gemini / Gemma)**
- Input de prueba: schemas del repositorio [Spruce](https://github.com/dan-divy/spruce)
- Output esperado: DDL Oracle equivalente al obtenido manualmente en la fase experimental

**Decisiones pendientes (a discutir al arrancar):**
- Lenguaje y stack — se valoran Python (ecosistema LLM) y Java (experiencia previa del autor)
- Estrategia: prompt único vs. pipeline multi-paso (la fase experimental sugiere que multi-paso da mejores resultados)
- Forma de invocación: script CLI, función importable, API mínima

**Fuera del alcance de esta fase:**
- UI o frontend
- Soporte multi-proveedor (vendrá después)
- Soporte de todos los formatos de entrada de la visión completa
- Análisis automático de repositorios completos

---

## 2. Primeros pasos sugeridos

Cuando se arranque una sesión nueva sin código existente, el orden recomendado es:

1. Decidir lenguaje y stack con el autor
2. Inicializar el proyecto (gestor de paquetes, dependencias mínimas, gitignore)
3. Crear estructura de carpetas básica
4. Cargar los schemas de Spruce como input de referencia
5. Implementar el primer paso del pipeline (lectura y parseo de schemas)
6. Integrar la API de Gemini/Gemma
7. Iterar sobre los pasos del pipeline hasta producir DDL

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

### Dataset de referencia: Spruce

[Spruce](https://github.com/dan-divy/spruce) es una aplicación real con MongoDB y schemas definidos explícitamente en el código. Es el caso de estudio principal del TFG.

Entidades del modelo relacional manual (baseline de comparación):
`USERS`, `USER_FOLLOWERS`, `POSTS`, `USER_NOTIFICATIONS`, `CHAT_ROOMS`, `CHAT_ROOM_MEMBERS`, `CHAT_MESSAGES`, `API_KEYS`, `API_KEY_STATS`, `ANALYTICS`, `ANALYTICS_STATS`.

### Fase experimental previa (completada, vía chat)

Se evaluaron varios LLMs con el mismo input (schemas de Spruce):

| Modelo | Modo | Output |
|---|---|---|
| GPT-3.5 | Prompt directo | DDL Oracle + UML |
| GPT-5 | Prompt directo | DDL Oracle + UML |
| Claude Opus 4.6 | Prompt directo | DDL Oracle + UML + índices |
| Claude Opus 4.6 | Agente (4 tareas) | DDL Oracle completo |
| GPT-5.3-Codex | Agente | DDL Oracle completo |

El pipeline multi-paso que mejores resultados produjo (Claude Opus 4.6 como agente):

1. Read all MongoDB Schema Models
2. Analyze Schemas and Relationships
3. Design normalized relational model
4. Generate Oracle DDL statements

**El prototipo reimplementa esta lógica de forma programática.**

### Visión completa de la herramienta (futuro, no este prototipo)

Requisitos de usuario que tendrá la herramienta final:

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
