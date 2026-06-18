# Capítulo 1. Descripción General del Trabajo

## 1.1 Resumen

Este Trabajo de Fin de Grado aborda el uso de modelos de lenguaje de gran tamaño (LLMs) para asistir en la transformación de modelos de datos desnormalizados, típicos de bases de datos NoSQL orientadas a documentos, en modelos relacionales normalizados. El objetivo principal del proyecto es explorar cómo las capacidades de análisis y razonamiento de estos modelos pueden utilizarse para facilitar tareas de diseño y reestructuración de bases de datos, especialmente en contextos donde se requiere migrar o integrar sistemas con diferentes paradigmas de almacenamiento de datos.

El proyecto se centra en el desarrollo de una herramienta software que utiliza técnicas basadas en inteligencia artificial para analizar estructuras de datos desnormalizadas y proponer una representación equivalente en un modelo relacional normalizado. Este proceso puede resultar complejo cuando se realiza manualmente, ya que implica identificar entidades, relaciones y dependencias entre datos que no siempre están explícitamente definidas en el modelo original. Mediante el uso de LLMs se busca automatizar parcialmente este análisis, proporcionando sugerencias estructurales que ayuden a generar esquemas relacionales más organizados y consistentes.

La herramienta resultante se materializa como una aplicación Python que ofrece dos modos de interacción —una interfaz de línea de comandos, para su uso desde terminal o en *pipelines* automatizados, y una interfaz gráfica que guía el mismo flujo sin necesidad de la línea de comandos— y un pipeline de cuatro fases (lectura, análisis del modelo documental, diseño relacional y generación de DDL Oracle) cuyos artefactos intermedios pueden inspeccionarse de forma independiente. El sistema admite tres modos de entrada: un fichero único con la definición explícita de los *schemas*, un directorio con evidencia heterogénea previamente curada, o la URL pública de un repositorio Git, en cuyo caso un agente de descubrimiento basado en *function calling* identifica autónomamente los archivos relevantes. La abstracción del proveedor de LLM permite alternar entre Google y Groq —y, por extensión, cualquier otro proveedor— sin modificar el resto del sistema.

El proyecto se plantea como una investigación aplicada dentro del ámbito académico y no está desarrollado para un cliente específico. Sin embargo, su enfoque está orientado a problemas reales que aparecen en entornos de desarrollo y mantenimiento de software, especialmente en escenarios de migración entre distintos tipos de bases de datos o en procesos de refactorización de modelos de datos existentes. La compatibilidad con Oracle como dialecto SQL objetivo responde directamente a la presencia mayoritaria de este motor en los sistemas legacy susceptibles de beneficiarse del enfoque.

En conjunto, este trabajo explora la aplicación práctica de modelos de lenguaje en tareas de ingeniería de datos, evaluando hasta qué punto estas herramientas pueden servir como apoyo en actividades tradicionalmente complejas y que requieren un alto nivel de conocimiento técnico, como es el diseño y normalización de esquemas de bases de datos.

## 1.2 Palabras clave

- LLM
- Normalización
- NoSQL
- MongoDB
- Oracle
- *Function calling*

## 1.3 Abstract

This Final Degree Project explores the use of Large Language Models (LLMs) to assist in the transformation of denormalized data models —typical of document-oriented NoSQL databases— into normalized relational models. The main goal of the project is to investigate the extent to which the analytical and reasoning capabilities of modern LLMs can be applied to database design and restructuring tasks, particularly in scenarios where systems built around different storage paradigms must be migrated or integrated.

The project develops a software tool that leverages artificial intelligence techniques to analyze denormalized data structures and propose an equivalent representation in a normalized relational model. This task can be complex when carried out manually, since it requires identifying entities, relations and dependencies that are not always explicitly declared in the original model. Using LLMs, the system partially automates this analysis and provides structural suggestions that help produce relational schemas that are better organized and more consistent.

The resulting tool is implemented as a Python application that offers two interaction modes —a command-line interface for technical users and a graphical user interface for non-technical users— and a four-stage pipeline (ingestion, document model analysis, relational design and Oracle DDL generation) whose intermediate artifacts can be inspected independently. The system supports three input modes: a single file with explicit schema definitions, a directory with previously curated heterogeneous evidence, or the public URL of a Git repository, in which case a *function-calling* discovery agent autonomously identifies the relevant files. The LLM provider abstraction allows switching between Google and Groq —and, by extension, any other provider— without modifying the rest of the system.

The project is positioned as applied research within the academic context and is not developed for a specific client. Nonetheless, its focus is aligned with real-world problems encountered in software development and maintenance environments, in particular those involving migrations between different database paradigms or refactoring of existing data models. The choice of Oracle as the target SQL dialect responds directly to the widespread presence of this engine in legacy systems likely to benefit from the proposed approach.

Overall, this work explores the practical application of LLMs in data engineering tasks and evaluates the extent to which such tools can support traditionally complex activities that demand a high level of technical knowledge, such as the design and normalization of database schemas.

## 1.4 Keywords

- LLM
- Normalization
- NoSQL
- MongoDB
- Oracle
- *Function calling*
