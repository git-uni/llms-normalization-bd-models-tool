A partir de este modelo relacional:

---
{design}
---

Genera el DDL **compatible con Oracle**. Requisitos:
- Usa tipos Oracle: VARCHAR2, NUMBER, DATE, TIMESTAMP, CLOB cuando aplique.
- Define PRIMARY KEY, FOREIGN KEY, NOT NULL y UNIQUE de forma explícita.
- Ordena los CREATE TABLE de manera que ninguna FK referencie una tabla aún no
  creada.
- Devuelve **solo** sentencias SQL ejecutables, sin explicaciones ni bloques de
  código markdown.
