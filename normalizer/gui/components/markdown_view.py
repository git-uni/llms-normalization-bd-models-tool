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
        tk_text.tag_config(
            "table", font=("Consolas", 12), background="#fafafa"
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
                    tbl_lines.append(lines[i])
                    i += 1
                for tl in tbl_lines:
                    self._textbox.insert("end", tl + "\n", "table")
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
