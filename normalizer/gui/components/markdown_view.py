"""Visor de Markdown sobre `CTkTextbox` con un parser minimalista.

No es un renderizador HTML — aplica *tags* directamente sobre el texto, lo
que respeta la decisión arquitectónica de "composición sobre CTkTextbox"
(§3.3.1 de la memoria). Soporta los elementos que el pipeline produce en la
práctica: encabezados (#, ##, ###), listas (-, *), bloques de código con
triple-backtick, énfasis con `**bold**` y `code en línea`, y tablas en
formato pipe.
"""

import re

import customtkinter as ctk


class MarkdownView(ctk.CTkTextbox):
    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("font", ctk.CTkFont(family="Segoe UI", size=13))
        kwargs.setdefault("wrap", "word")
        super().__init__(master, **kwargs)
        tk_text = self._textbox
        tk_text.tag_config("h1", font=("Segoe UI", 20, "bold"), spacing3=8)
        tk_text.tag_config("h2", font=("Segoe UI", 17, "bold"), spacing3=6)
        tk_text.tag_config("h3", font=("Segoe UI", 15, "bold"), spacing3=4)
        tk_text.tag_config("bold", font=("Segoe UI", 13, "bold"))
        tk_text.tag_config("italic", font=("Segoe UI", 13, "italic"))
        tk_text.tag_config(
            "code",
            font=("Consolas", 12),
            background="#f0f0f0",
        )
        tk_text.tag_config(
            "codeblock",
            font=("Consolas", 12),
            background="#f6f8fa",
            lmargin1=12,
            lmargin2=12,
            spacing1=4,
            spacing3=4,
        )
        tk_text.tag_config("bullet", lmargin1=14, lmargin2=28)
        # Tablas: tres tags coordinados para que header, separador y
        # cuerpo compartan métrica (Consolas) y se diferencien en peso.
        tk_text.tag_config(
            "table_header",
            font=("Consolas", 12, "bold"),
            background="#eef2fa",
            spacing1=2,
        )
        tk_text.tag_config(
            "table_sep",
            font=("Consolas", 12),
            foreground="#888888",
        )
        tk_text.tag_config(
            "table_cell",
            font=("Consolas", 12),
            background="#fafafa",
        )

    def render(self, md: str) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self._render_lines(md)
        self.configure(state="disabled")

    def _render_lines(self, md: str) -> None:
        lines = md.splitlines()
        in_code = False
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            if stripped.startswith("```"):
                in_code = not in_code
                i += 1
                continue
            if in_code:
                self._textbox.insert("end", line + "\n", "codeblock")
                i += 1
                continue

            # Tablas: filas consecutivas que empiezan por |
            if stripped.startswith("|"):
                tbl_lines = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    tbl_lines.append(lines[i].strip())
                    i += 1
                self._render_table(tbl_lines)
                continue

            # Encabezados
            if stripped.startswith("### "):
                self._textbox.insert("end", stripped[4:] + "\n", "h3")
                i += 1
                continue
            if stripped.startswith("## "):
                self._textbox.insert("end", stripped[3:] + "\n", "h2")
                i += 1
                continue
            if stripped.startswith("# "):
                self._textbox.insert("end", stripped[2:] + "\n", "h1")
                i += 1
                continue

            # Listas
            if re.match(r"^[-*]\s+", stripped):
                self._insert_inline("• " + stripped[2:].lstrip(), "bullet")
                self._textbox.insert("end", "\n")
                i += 1
                continue
            m_ol = re.match(r"^(\d+)\.\s+", stripped)
            if m_ol:
                rest = stripped[len(m_ol.group(0)) :]
                self._insert_inline(m_ol.group(1) + ". " + rest, "bullet")
                self._textbox.insert("end", "\n")
                i += 1
                continue

            # Párrafo normal con inline (negrita, code en línea)
            self._insert_inline(line, "")
            self._textbox.insert("end", "\n")
            i += 1

    _SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")

    def _render_table(self, raw_lines: list[str]) -> None:
        """Parsea un bloque de tabla pipe-style y lo renderiza alineado.

        El visor original insertaba las filas tal cual: con `wrap="word"`
        en el widget las celdas largas envolvían y rompían la alineación
        de la tabla; los `---` aparecían como texto literal; no había
        contraste entre encabezado y cuerpo. Aquí parseamos celdas, las
        alineamos a un ancho fijo (max por columna) y dibujamos un
        separador unicode entre header y cuerpo.
        """
        rows: list[list[str]] = []
        for raw in raw_lines:
            cells = [c.strip() for c in raw.split("|")]
            # Las tablas markdown estándar empiezan y terminan en `|`,
            # así que `split` deja celdas vacías en los extremos.
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            rows.append(cells)
        if not rows:
            return

        # Detectar fila de separadores (`|---|---|`). Marca el header en
        # la fila inmediatamente anterior — convención markdown estándar.
        sep_idx: int | None = None
        for idx, cells in enumerate(rows):
            if cells and all(
                self._SEPARATOR_CELL_RE.match(c) for c in cells if c
            ):
                sep_idx = idx
                break
        has_header = sep_idx == 1
        data_rows = [r for idx, r in enumerate(rows) if idx != sep_idx]
        if not data_rows:
            return

        n_cols = max(len(r) for r in data_rows)
        widths = [0] * n_cols
        for row in data_rows:
            for j, cell in enumerate(row):
                if j < n_cols:
                    widths[j] = max(widths[j], len(cell))

        def _format_row(row: list[str]) -> str:
            padded = []
            for j in range(n_cols):
                cell = row[j] if j < len(row) else ""
                padded.append(cell.ljust(widths[j]))
            return "  " + "  │  ".join(padded) + "  "

        if has_header:
            self._textbox.insert(
                "end", _format_row(data_rows[0]) + "\n", "table_header"
            )
            sep_line = "  " + "──┼──".join("─" * w for w in widths) + "──"
            self._textbox.insert("end", sep_line + "\n", "table_sep")
            body = data_rows[1:]
        else:
            body = data_rows
        for row in body:
            self._textbox.insert("end", _format_row(row) + "\n", "table_cell")
        # Línea en blanco al cerrar la tabla para separar del siguiente
        # bloque de contenido.
        self._textbox.insert("end", "\n")

    _INLINE_RE = re.compile(
        r"(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*)"
    )

    def _insert_inline(self, text: str, base_tag: str) -> None:
        # Aplica tags de bold/italic/code dentro de una línea.
        pos = 0
        for m in self._INLINE_RE.finditer(text):
            if m.start() > pos:
                self._textbox.insert("end", text[pos : m.start()], base_tag)
            if m.group(2) is not None:  # **bold**
                self._textbox.insert("end", m.group(2), ("bold", base_tag))
            elif m.group(3) is not None:  # `code`
                self._textbox.insert("end", m.group(3), ("code", base_tag))
            elif m.group(4) is not None:  # *italic*
                self._textbox.insert("end", m.group(4), ("italic", base_tag))
            pos = m.end()
        if pos < len(text):
            self._textbox.insert("end", text[pos:], base_tag)
