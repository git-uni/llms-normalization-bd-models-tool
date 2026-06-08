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


class SqlView(ctk.CTkTextbox):
    """Textbox de solo lectura que renderiza SQL con resaltado."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("font", ctk.CTkFont(family="Consolas", size=12))
        kwargs.setdefault("wrap", "none")
        super().__init__(master, **kwargs)
        # Configurar tags. Colores escogidos para que funcionen en claro y oscuro.
        # `tag_config` se delega a la Text widget interna.
        tk_text = self._textbox
        tk_text.tag_config("kw", foreground="#0050b3")
        tk_text.tag_config("builtin", foreground="#7c3aed")
        tk_text.tag_config("op", foreground="#888888")
        tk_text.tag_config("str", foreground="#a06800")
        tk_text.tag_config("num", foreground="#0050b3")
        tk_text.tag_config("comment", foreground="#6a737d", font=(
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
