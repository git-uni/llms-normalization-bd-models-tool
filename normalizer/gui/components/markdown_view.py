"""Visor de Markdown sobre `CTkTextbox` con un parser minimalista.

No es un renderizador HTML, aplica *tags* directamente sobre el texto, lo
que respeta la decisión arquitectónica de "composición sobre CTkTextbox"
(§3.3.1 de la memoria). Soporta los elementos que el pipeline produce en la
práctica: encabezados (#, ##, ###), listas (-, *), bloques de código con
triple-backtick, énfasis con `**bold**` y `code en línea`, y tablas en
formato pipe (renderizadas como *widgets reales* embebidos con scroll
horizontal para que no se rompan en ventanas estrechas).
"""

import re
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk


def _md_palette() -> dict[str, str]:
    """Paleta surface tonal M3 acorde al tema actual (light/dark).

    Cubre tablas (cell/alt/header/border/container) y tags de código
    inline (`code`) y de bloque (`codeblock`).
    """
    if ctk.get_appearance_mode().lower() == "dark":
        return {
            # Tablas
            "container_bg": "#101418",     # surface
            "header_bg": "#26292d",        # surface-container-high
            "header_fg": "#e8edf5",
            "cell_bg": "#101418",          # surface
            "cell_alt_bg": "#181c20",      # surface-container-low
            "cell_fg": "#d8dde8",
            "border": "#3a4456",           # outline-variant
            # Tags de código
            "code_bg": "#26292d",          # surface-container-high
            "codeblock_bg": "#181c20",     # surface-container-low
        }
    return {
        "container_bg": "#eaf0f8",
        "header_bg": "#cedaee",
        "header_fg": "#1f2a3a",
        "cell_bg": "#eaf0f8",
        "cell_alt_bg": "#dfe7f2",
        "cell_fg": "#202838",
        "border": "#a8bcd9",
        "code_bg": "#cedaee",
        "codeblock_bg": "#dfe7f2",
    }


class MarkdownView(ctk.CTkTextbox):
    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("font", ctk.CTkFont(family="Segoe UI", size=13))
        kwargs.setdefault("wrap", "word")
        kwargs.setdefault("fg_color", ("#dfe7f2", "#181c20"))  # surface-container-low
        super().__init__(master, **kwargs)
        pal = _md_palette()
        tk_text = self._textbox
        tk_text.tag_config("h1", font=("Segoe UI", 20, "bold"), spacing3=8)
        tk_text.tag_config("h2", font=("Segoe UI", 17, "bold"), spacing3=6)
        tk_text.tag_config("h3", font=("Segoe UI", 15, "bold"), spacing3=4)
        tk_text.tag_config("bold", font=("Segoe UI", 13, "bold"))
        tk_text.tag_config("italic", font=("Segoe UI", 13, "italic"))
        tk_text.tag_config(
            "code",
            font=("Consolas", 12),
            background=pal["code_bg"],
        )
        tk_text.tag_config(
            "codeblock",
            font=("Consolas", 12),
            background=pal["codeblock_bg"],
            lmargin1=12,
            lmargin2=12,
            spacing1=4,
            spacing3=4,
        )
        tk_text.tag_config("bullet", lmargin1=14, lmargin2=28)
        # Las tablas ya no usan tags: se renderizan como widgets reales
        # embebidos con `window_create` (ver `_render_table`).

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
        """Parsea un bloque de tabla pipe-style y lo embebe como widget.

        Versión 1 renderizaba con texto monospace alineado, pero el
        `wrap="word"` del Textbox rompía la alineación cuando la tabla era
        más ancha que el visor (caso típico con ventana pequeña). Ahora
        cada tabla se construye como un `tk.Frame` con una grid de
        `tk.Label` (header + cuerpo con filas alternas, bordes finos), se
        envuelve en un `tk.Canvas` con scrollbar horizontal y se embebe en
        el Textbox con `window_create`. Resultado: las tablas anchas se
        scrollean, no se cortan; las cortas ocupan justo lo necesario.
        """
        rows: list[list[str]] = []
        for raw in raw_lines:
            cells = [c.strip() for c in raw.split("|")]
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            rows.append(cells)
        if not rows:
            return

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

        widget = self._build_table_widget(data_rows, has_header=has_header)
        self._textbox.insert("end", "\n")
        self._textbox.window_create("end", window=widget)
        self._textbox.insert("end", "\n\n")
        

    def _build_table_widget(
        self, data_rows: list[list[str]], has_header: bool
    ) -> tk.Frame:
        pal = _md_palette()
        n_cols = max(len(r) for r in data_rows)

        # Estructura: outer (visible en el Textbox) → canvas (scrollable)
        # → inner (la grid de celdas). El canvas se ajusta a la altura
        # del inner y obtiene scrollbar horizontal abajo si el contenido
        # supera el ancho disponible.
        outer = tk.Frame(self._textbox, bg=pal["container_bg"], bd=0)
        canvas = tk.Canvas(
                        outer,
                        width=max(1360, self._textbox.winfo_width() - 20),                       
                        bg=pal["container_bg"],
                        highlightthickness=0,
                        bd=0,
                        )
        hbar = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=hbar.set)
        inner = tk.Frame(canvas, bg=pal["border"])  # bg=border → líneas de rejilla
        canvas_window = canvas.create_window(
            (0, 0), window=inner, anchor="nw",
        )

        # Render de celdas como tk.Label sobre `inner`. Usamos padx/pady en
        # `grid()` con bg=border en el frame padre para simular líneas de
        # rejilla finas (el "padding" muestra el bg del frame de abajo).
        font_regular = ("Consolas", 11)
        font_bold = ("Consolas", 11, "bold")
        WRAPLEN = 1080  # px, ≈ 55 chars en Consolas 11

        def _cell(row: int, col: int, text: str, is_header: bool, alt: bool) -> None:
            bg = (
                pal["header_bg"] if is_header
                else (pal["cell_alt_bg"] if alt else pal["cell_bg"])
            )
            fg = pal["header_fg"] if is_header else pal["cell_fg"]
            lbl = tk.Label(
                inner, text=text or " ",
                font=font_bold if is_header else font_regular,
                bg=bg, fg=fg, anchor="w", justify="left",
                wraplength=WRAPLEN, padx=10, pady=5, bd=0,
                highlightthickness=0,
            )
            lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

        body_offset = 0
        if has_header:
            for j, cell in enumerate(data_rows[0]):
                _cell(0, j, cell, is_header=True, alt=False)
            for j in range(len(data_rows[0]), n_cols):
                _cell(0, j, "", is_header=True, alt=False)
            body_offset = 1

        body = data_rows[1:] if has_header else data_rows
        for r, row in enumerate(body):
            for j in range(n_cols):
                cell = row[j] if j < len(row) else ""
                _cell(
                    r + body_offset, j, cell,
                    is_header=False, alt=r % 2 == 1,
                )

        # Ajustar canvas a la altura real del contenido y configurar
        # scrollregion para el scrollbar horizontal.
        def _on_inner_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            req_h = inner.winfo_reqheight()
            canvas.configure(height=req_h)
        inner.bind("<Configure>", _on_inner_configure)

        # Mostrar el scrollbar solo si la tabla es más ancha que el visor.
        def _on_canvas_configure(event):
            inner_w = inner.winfo_reqwidth()
            if inner_w > event.width:
                hbar.grid(row=1, column=0, sticky="ew")
            else:
                hbar.grid_remove()
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        return outer

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
