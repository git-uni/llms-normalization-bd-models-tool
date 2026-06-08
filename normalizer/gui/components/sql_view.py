"""Visor de SQL con resaltado de sintaxis sobre `CTkTextbox`.

Usa `pygments` para tokenizar el código. Cada token se inserta con un *tag*
de Tkinter configurado con color e itálica/bold. No depende de ningún tema
de Pygments — solo del árbol de tipos de tokens.
"""

import customtkinter as ctk
from pygments import lex
from pygments.lexers.sql import SqlLexer
from pygments.token import Token


def _tag_for(token_type) -> str:
    """Reduce el árbol de tokens de Pygments a unas pocas categorías."""
    t = token_type
    while t is not None:
        if t in (Token.Keyword, Token.Keyword.Type, Token.Keyword.Reserved,
                 Token.Keyword.DML, Token.Keyword.DDL):
            return "kw"
        if t is Token.Name.Builtin:
            return "builtin"
        if t in (Token.Operator, Token.Punctuation, Token.Operator.Word):
            return "op"
        if t in (Token.Literal.String, Token.Literal.String.Single,
                 Token.Literal.String.Symbol, Token.Literal.String.Double):
            return "str"
        if t in (Token.Literal.Number, Token.Literal.Number.Integer,
                 Token.Literal.Number.Float):
            return "num"
        if t in (Token.Comment, Token.Comment.Single, Token.Comment.Multiline):
            return "comment"
        t = t.parent
    return ""


def _sql_palette() -> dict[str, str]:
    """Paleta del resaltado SQL acorde al tema actual (light/dark).

    Inspirada en roles M3: keywords y números en primary, builtins en
    secondary, strings en tertiary. Sin amarillos sueltos.
    """
    if ctk.get_appearance_mode().lower() == "dark":
        return {
            "kw": "#9ec3e4",       # primary tone 80
            "builtin": "#b8c5d5",  # secondary tone 80
            "op": "#a8a8a8",
            "str": "#a4c8d6",      # tertiary tone 80
            "num": "#9ec3e4",
            "comment": "#8a92a0",
        }
    return {
        "kw": "#0050b3",        # primary tone 40
        "builtin": "#516a86",   # secondary tone 40
        "op": "#888888",
        "str": "#3c6477",       # tertiary tone 40
        "num": "#0050b3",
        "comment": "#6a737d",
    }


class SqlView(ctk.CTkTextbox):
    """Textbox de solo lectura que renderiza SQL con resaltado."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("font", ctk.CTkFont(family="Consolas", size=12))
        kwargs.setdefault("wrap", "none")
        kwargs.setdefault("fg_color", ("#dfe7f2", "#181c20"))  # surface-container-low
        super().__init__(master, **kwargs)
        pal = _sql_palette()
        tk_text = self._textbox
        tk_text.tag_config("kw", foreground=pal["kw"])
        tk_text.tag_config("builtin", foreground=pal["builtin"])
        tk_text.tag_config("op", foreground=pal["op"])
        tk_text.tag_config("str", foreground=pal["str"])
        tk_text.tag_config("num", foreground=pal["num"])
        tk_text.tag_config("comment", foreground=pal["comment"], font=(
            "Consolas", 12, "italic",
        ))

    def render(self, sql: str) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        for token_type, value in lex(sql, SqlLexer()):
            tag = _tag_for(token_type)
            if tag:
                self.insert("end", value, tag)
            else:
                self.insert("end", value)
        self.configure(state="disabled")
