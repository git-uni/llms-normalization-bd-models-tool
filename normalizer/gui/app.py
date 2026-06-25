"""Punto de entrada de la GUI.

Construye la ventana raíz (`NormalizerApp`), carga las credenciales del
fichero `.env` (si existe) y arranca el bucle de eventos de CustomTkinter.
La navegación entre pantallas se hace destruyendo el frame actual y
empacando el siguiente; el estado compartido vive en `app.gui_state` (un
`GuiState`). El atributo no se llama `state` porque `Tk` ya hereda un
método `state()` para iconificar la ventana.
"""

import platform
import tkinter.font as tkfont

import customtkinter as ctk
from dotenv import load_dotenv

from normalizer.gui.state import GuiState

# Fuentes de UI preferidas por sistema operativo. El default de CustomTkinter es
# "Roboto", que no suele estar instalada: Tk cae entonces a una fuente genérica
# que da aspecto anticuado. Elegimos la primera nativa disponible.
_UI_FONT_PREFS = {
    "Windows": ["Segoe UI Variable Text", "Segoe UI", "Calibri"],
    "Darwin": ["SF Pro Text", ".AppleSystemUIFont", "Helvetica Neue", "Helvetica"],
}
_UI_FONT_FALLBACK = ["Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans"]


def _pick_ui_font(root: ctk.CTk) -> str | None:
    """Primera familia de UI nativa disponible para el SO, o None."""
    available = set(tkfont.families(root))
    for fam in _UI_FONT_PREFS.get(platform.system(), []) + _UI_FONT_FALLBACK:
        if fam in available:
            return fam
    return None


class NormalizerApp(ctk.CTk):
    def __init__(self) -> None:
        # `fg_color` se pasa en el constructor porque `configure` post-init
        # no siempre actualiza el background de la ventana raíz en CTk.
        # Subido el chroma azul para que la paleta surface tonal sea
        # visible (antes era casi blanco neutral y no se notaba).
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=("#eaf0f8", "#101418"))
        # Fija la fuente de UI a la nativa del SO (Segoe UI en Windows). Debe ir
        # tras crear la ventana (para consultar las familias) y antes de construir
        # las pantallas: los CTkFont sin family heredan esta del tema.
        ui_font = _pick_ui_font(self)
        if ui_font:
            ctk.ThemeManager.theme["CTkFont"]["family"] = ui_font
        self.title("NormalizerApp")
        self.geometry("1100x780")
        self.minsize(900, 640)

        # No usar `state` — Tk hereda un método `state()` para iconificar.
        self.gui_state = GuiState()
        self._current: ctk.CTkFrame | None = None
        self.show_config()

    def _swap(self, screen: ctk.CTkFrame) -> None:
        if self._current is not None:
            self._current.destroy()
        screen.pack(fill="both", expand=True, padx=20, pady=20)
        self._current = screen

    def show_config(self) -> None:
        from normalizer.gui.windows.config import ConfigScreen

        self._swap(ConfigScreen(self))

    def show_run(self) -> None:
        from normalizer.gui.windows.run import RunScreen

        self._swap(RunScreen(self))

    def show_result(self) -> None:
        from normalizer.gui.windows.result import ResultScreen

        self._swap(ResultScreen(self))


def main() -> None:
    load_dotenv()
    app = NormalizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
