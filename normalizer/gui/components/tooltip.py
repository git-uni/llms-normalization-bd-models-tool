"""Tooltip ligero para widgets Tk / CustomTkinter.

CustomTkinter no incluye un *tooltip* nativo, así que se implementa uno mínimo:
`attach_tooltip(widget, text)` muestra un recuadro flotante con `text` cuando el
cursor se posa sobre `widget` (tras un breve retardo) y lo oculta al salir o al
pulsar. Se usa un `tk.Label` plano dentro de un `Toplevel` sin bordes — basta
para un texto de ayuda y evita complicaciones con las tuplas de color de CTk.
"""

import tkinter as tk


class _Tooltip:
    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        *,
        delay_ms: int = 450,
        wraplength: int = 320,
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.wraplength = wraplength
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event: object = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        try:
            self._tip.attributes("-topmost", True)
        except Exception:
            pass
        tk.Label(
            self._tip,
            text=self.text,
            justify="left",
            background="#11161a",
            foreground="#e7eef8",
            relief="solid",
            borderwidth=1,
            wraplength=self.wraplength,
            padx=10,
            pady=6,
            font=("Segoe UI", 10),
        ).pack()

    def _hide(self, _event: object = None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


def attach_tooltip(widget: tk.Widget, text: str, **kwargs: object) -> _Tooltip:
    """Asocia un tooltip con `text` a `widget`. Devuelve el objeto (mantener
    una referencia no es necesario: los *bindings* lo mantienen vivo)."""
    return _Tooltip(widget, text, **kwargs)  # type: ignore[arg-type]
