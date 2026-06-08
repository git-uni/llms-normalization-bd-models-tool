"""Punto de entrada de la GUI.

Construye la ventana raíz (`NormalizerApp`), carga las credenciales del
fichero `.env` (si existe) y arranca el bucle de eventos de CustomTkinter.
La navegación entre pantallas se hace destruyendo el frame actual y
empacando el siguiente; el estado compartido vive en `app.gui_state` (un
`GuiState`). El atributo no se llama `state` porque `Tk` ya hereda un
método `state()` para iconificar la ventana.
"""

import customtkinter as ctk
from dotenv import load_dotenv

from normalizer.gui.state import GuiState


class NormalizerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NormalizerApp")
        self.geometry("1100x780")
        self.minsize(900, 640)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Surface base de la paleta M3 con seed azul: ligeramente teñido
        # de azul en light, casi neutral en dark. Override del fg_color del
        # root para que todas las pantallas hereden esta base.
        self.configure(fg_color=("#f9fafc", "#101418"))

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
