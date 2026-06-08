"""Pantalla 3 — Resultado.

Banner de estado (OK / cancelado / error), `CTkTabview` con los artefactos
producidos (diagrama ER + markdown + DDL) y barra de acciones (abrir el
directorio en el explorador, exportar a ZIP, nueva ejecución).

El diagrama ER se renderiza al entrar en la pestaña; si Graphviz no está
instalado, la pestaña muestra instrucciones de instalación sin romper el
resto de la pantalla.
"""

import os
import platform
import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk
from PIL import Image, ImageTk

from normalizer.gui.components.markdown_view import MarkdownView
from normalizer.gui.components.sql_view import SqlView
from normalizer.gui.ddl_graph import render_to_png
from normalizer.gui.state import GuiState


class ResultScreen(ctk.CTkFrame):
    def __init__(self, app: ctk.CTk) -> None:
        super().__init__(app)
        self.app = app
        self.gui_state: GuiState = app.gui_state
        self.out_dir: Path | None = self.gui_state.out_dir
        # Estado del visor ER. Las referencias a la imagen y el PhotoImage
        # tienen que sobrevivir al método que las crea, si no Tkinter las
        # libera y aparece un cuadro en blanco.
        self._er_pil_image: Image.Image | None = None
        self._er_png_path: Path | None = None
        self._er_photo_ref: ImageTk.PhotoImage | None = None
        self._er_canvas: tk.Canvas | None = None
        self._er_zoom: float = 1.0
        self._er_zoom_label: ctk.CTkLabel | None = None
        # Debounce del redraw para que zooms rápidos no encolen N resizes
        # caros — sobre el ER de Habitica (2896x2578 px) el resize LANCZOS
        # tardaba 2s+ por iteración, ahora usamos BILINEAR + debounce.
        self._er_redraw_job: str | None = None

        self._build()

    def _build(self) -> None:
        # Banner de estado
        self._build_banner()

        # Tabview con artefactos
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=(12, 12))

        if self.out_dir is None or not self.out_dir.exists():
            ctk.CTkLabel(
                self.tabs.add("Sin artefactos"),
                text="No se ha producido ningún artefacto.",
                text_color="gray",
            ).pack(pady=40)
        else:
            self._build_tabs()

        # Barra de acciones
        self._build_actions()

    # ------------------------------------------------------------------

    def _build_banner(self) -> None:
        # Paleta M3: error-container para fallo, tertiary-container para
        # cancelado, primary-container para éxito. Sin amarillos sueltos.
        s = self.gui_state
        if s.error_message:
            text = f"Error durante {s.error_phase or '?'}: {s.error_message}"
            fg = ("#ffdad6", "#5a1a18")   # error-container
            tcol = ("#410002", "#ffdad6")  # on-error-container
        elif s.cancelled:
            text = "Ejecución cancelada por el usuario. Los artefactos producidos hasta el momento están disponibles abajo (la última llamada al LLM puede seguir terminando en background)."
            fg = ("#d2e6ee", "#244c5f")   # tertiary-container
            tcol = ("#0e2a3a", "#d2e6ee")  # on-tertiary-container
        elif s.finished_ok:
            text = f"DDL generado en {self.out_dir}"
            fg = ("#d6e4f3", "#1f3a52")   # primary-container suave
            tcol = ("#082942", "#d6e4f3")  # on-primary-container
        else:
            text = "Resultado"
            fg = ("transparent", "transparent")
            tcol = None

        banner = ctk.CTkFrame(self, fg_color=fg, corner_radius=12)
        banner.pack(fill="x")
        lbl = ctk.CTkLabel(
            banner, text=text, anchor="w", wraplength=950, justify="left",
            font=ctk.CTkFont(size=13),
        )
        if tcol is not None:
            lbl.configure(text_color=tcol)
        lbl.pack(fill="x", padx=18, pady=14)

    def _build_tabs(self) -> None:
        assert self.out_dir is not None
        ddl_path = self.out_dir / "04_ddl.sql"
        design_path = self.out_dir / "03_design.md"
        analysis_path = self.out_dir / "02_analysis.md"
        discovery_path = self.out_dir / "00_discovery" / "discovery.md"
        
        if self.gui_state.is_url and discovery_path.exists():
            mv_disc = MarkdownView(self.tabs.add("Descubrimiento"))
            mv_disc.render(discovery_path.read_text(encoding="utf-8"))
            mv_disc.pack(fill="both", expand=True)

        if analysis_path.exists():
            mv_analysis = MarkdownView(self.tabs.add("Análisis"))
            mv_analysis.render(analysis_path.read_text(encoding="utf-8"))
            mv_analysis.pack(fill="both", expand=True)
            
        if design_path.exists():
            mv_design = MarkdownView(self.tabs.add("Diseño"))
            mv_design.render(design_path.read_text(encoding="utf-8"))
            mv_design.pack(fill="both", expand=True)

        if ddl_path.exists():
            sv = SqlView(self.tabs.add("DDL"))
            sv.render(ddl_path.read_text(encoding="utf-8"))
            sv.pack(fill="both", expand=True)

        # Pestaña por defecto: si hay DDL, ER. Si no, la primera disponible.
        if not ddl_path.exists():
            for name in ("Diseño", "Análisis", "Descubrimiento"):
                try:
                    self.tabs.set(name)
                    break
                except ValueError:
                    continue
        
        # Diagrama ER — pestaña por defecto.
        er_tab = self.tabs.add("Diagrama ER")
        self._build_er_tab(er_tab, ddl_path)
        self.tabs.set("Diagrama ER")
        

    def _build_er_tab(self, parent: ctk.CTkFrame, ddl_path: Path) -> None:
        # Guardamos el parent para que el botón "Reintentar" pueda
        # reconstruir el contenido sin recrear la pestaña entera.
        self._er_parent = parent
        self._er_ddl_path = ddl_path
        self._render_er_into(parent, ddl_path)

    def _render_er_into(self, parent: ctk.CTkFrame, ddl_path: Path) -> None:
        if not ddl_path.exists():
            ctk.CTkLabel(
                parent,
                text=(
                    "Aún no hay DDL — no se puede generar el diagrama.\n"
                    "Revisa las demás pestañas para ver los artefactos disponibles."
                ),
                text_color="gray",
                justify="center",
            ).pack(expand=True)
            return

        ddl = ddl_path.read_text(encoding="utf-8")
        assert self.out_dir is not None
        out_base = self.out_dir / "_er_diagram"
        png = render_to_png(ddl, out_base)
        if png is None or not png.exists():
            self._build_graphviz_missing(parent)
            return

        try:
            self._er_pil_image = Image.open(png)
            self._er_png_path = png
            self._er_zoom = 1.0
            self._build_er_viewer(parent)
        except Exception as e:
            ctk.CTkLabel(
                parent,
                text=f"No se pudo cargar la imagen ER:\n{e}",
                text_color=("#ba1a1a", "#ffb4ab"),  # error M3
            ).pack(expand=True)

    def _build_er_viewer(self, parent: ctk.CTkFrame) -> None:
        # Toolbar de zoom.
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            toolbar, text="−", width=34, command=lambda: self._zoom_er(0.8)
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            toolbar, text="+", width=34, command=lambda: self._zoom_er(1.25)
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            toolbar, text="100%", width=60,
            command=lambda: self._set_er_zoom(1.0),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            toolbar, text="Ajustar a ventana", width=150,
            command=self._fit_er_to_window,
        ).pack(side="left", padx=(0, 4))
        self._er_zoom_label = ctk.CTkLabel(
            toolbar, text="zoom: 100%", text_color="gray"
        )
        self._er_zoom_label.pack(side="left", padx=8)
        ctk.CTkButton(
            toolbar, text="Abrir en visor externo", width=180,
            command=self._open_er_external,
        ).pack(side="right")

        # Canvas con scrollbars XY. Usamos tk.Canvas + ttk.Scrollbar porque
        # CTkScrollableFrame solo permite una orientación a la vez.
        canvas_frame = ctk.CTkFrame(parent)
        canvas_frame.pack(fill="both", expand=True)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # Fondo blanco para que el PNG (que tiene fondo transparente) se
        # lea bien tanto en tema claro como oscuro.
        self._er_canvas = tk.Canvas(
            canvas_frame,
            bg="#f9fafc" if ctk.get_appearance_mode().lower() != "dark" else "#101418",
            highlightthickness=0
        )
        yscroll = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=self._er_canvas.yview
        )
        xscroll = ttk.Scrollbar(
            canvas_frame, orient="horizontal", command=self._er_canvas.xview
        )
        self._er_canvas.configure(
            xscrollcommand=xscroll.set, yscrollcommand=yscroll.set
        )
        self._er_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        # Ctrl+rueda → zoom; rueda sola → scroll vertical (Tk lo hace solo).
        self._er_canvas.bind(
            "<Control-MouseWheel>", self._on_er_mouse_zoom
        )

        self._redraw_er()

    def _redraw_er(self) -> None:
        self._er_redraw_job = None
        if (
            self._er_pil_image is None
            or self._er_canvas is None
        ):
            return
        try:
            if not self._er_canvas.winfo_exists():
                return
        except Exception:
            return
        w, h = self._er_pil_image.size
        zw, zh = max(1, int(w * self._er_zoom)), max(1, int(h * self._er_zoom))
        # BILINEAR es ~10x más rápido que LANCZOS y la diferencia es
        # imperceptible para un diagrama ER con líneas y texto. LANCZOS
        # sobre 2896×2578 (Habitica) tardaba 2-3 s por resize.
        img = self._er_pil_image.resize((zw, zh), Image.BILINEAR)
        self._er_photo_ref = ImageTk.PhotoImage(img)
        self._er_canvas.delete("all")
        self._er_canvas.create_image(
            0, 0, anchor="nw", image=self._er_photo_ref
        )
        self._er_canvas.configure(scrollregion=(0, 0, zw, zh))

    def _zoom_er(self, factor: float) -> None:
        # Limitar a un rango razonable para evitar resize gigantes.
        self._set_er_zoom(self._er_zoom * factor)

    def _set_er_zoom(self, zoom: float) -> None:
        self._er_zoom = max(0.1, min(5.0, zoom))
        # La etiqueta de zoom se actualiza inmediatamente para que el
        # usuario reciba feedback aunque el redraw esté debounced.
        if self._er_zoom_label is not None:
            try:
                self._er_zoom_label.configure(
                    text=f"zoom: {int(self._er_zoom * 100)}%"
                )
            except Exception:
                pass
        # Debounce: si llegan varios clicks rápidos en +/+, descartamos
        # los redraws intermedios y solo hacemos el último.
        if self._er_redraw_job is not None:
            try:
                self.after_cancel(self._er_redraw_job)
            except Exception:
                pass
        self._er_redraw_job = self.after(80, self._redraw_er)

    def _fit_er_to_window(self) -> None:
        if self._er_pil_image is None or self._er_canvas is None:
            return
        cw = self._er_canvas.winfo_width()
        ch = self._er_canvas.winfo_height()
        if cw < 50 or ch < 50:
            # Canvas aún no realizado: reintentar en el próximo tick.
            self.after(100, self._fit_er_to_window)
            return
        iw, ih = self._er_pil_image.size
        self._set_er_zoom(min(cw / iw, ch / ih))

    def _on_er_mouse_zoom(self, event) -> None:
        # En Windows, event.delta es múltiplo de 120; arriba positivo.
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        self._zoom_er(factor)

    def _open_er_external(self) -> None:
        if self._er_png_path is None or not self._er_png_path.exists():
            return
        path = str(self._er_png_path.resolve())
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _build_graphviz_missing(self, parent: ctk.CTkFrame) -> None:
        msg = ctk.CTkFrame(parent, fg_color="transparent")
        msg.pack(expand=True)
        ctk.CTkLabel(
            msg,
            text="Graphviz no está disponible",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(0, 8))
        instr = (
            "El diagrama ER necesita el binario `dot` de Graphviz para renderizarse.\n\n"
            "Instálalo según tu sistema operativo:\n\n"
            "  • Windows:  winget install Graphviz.Graphviz\n"
            "  • macOS:    brew install graphviz\n"
            "  • Linux:    sudo apt install graphviz  (o equivalente)\n\n"
            "Si acabas de instalarlo, pulsa Reintentar — la GUI buscará el\n"
            "binario en las rutas estándar sin necesidad de reiniciar la\n"
            "terminal. Las demás pestañas funcionan ya."
        )
        ctk.CTkLabel(msg, text=instr, justify="left").pack()
        ctk.CTkButton(
            msg, text="Reintentar", command=self._retry_er, width=140
        ).pack(pady=(14, 0))

    def _retry_er(self) -> None:
        # Limpia el contenido actual de la pestaña ER y vuelve a intentar
        # generar el diagrama. Útil cuando el usuario instala Graphviz con
        # la GUI ya abierta.
        if not hasattr(self, "_er_parent") or not hasattr(self, "_er_ddl_path"):
            return
        for w in self._er_parent.winfo_children():
            w.destroy()
        self._er_photo_ref = None
        self._er_pil_image = None
        self._er_canvas = None
        self._er_zoom_label = None
        self._render_er_into(self._er_parent, self._er_ddl_path)

    def _build_actions(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x")
        ctk.CTkButton(
            bar,
            text="Abrir directorio",
            command=self._open_dir,
            width=160,
            state="normal" if self.out_dir and self.out_dir.exists() else "disabled",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            bar,
            text="Exportar como ZIP",
            command=self._export_zip,
            width=160,
            state="normal" if self.out_dir and self.out_dir.exists() else "disabled",
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            bar,
            text="↻ Nueva ejecución",
            command=self.app.show_config,
            width=160,
        ).pack(side="right")

    # ------------------------------------------------------------------

    def _open_dir(self) -> None:
        if self.out_dir is None or not self.out_dir.exists():
            return
        path = str(self.out_dir.resolve())
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _export_zip(self) -> None:
        if self.out_dir is None or not self.out_dir.exists():
            return
        target = filedialog.asksaveasfilename(
            title="Exportar artefactos a ZIP",
            defaultextension=".zip",
            initialfile=f"{self.out_dir.name}.zip",
            filetypes=[("ZIP", "*.zip")],
        )
        if not target:
            return
        target_path = Path(target)
        base = target_path.with_suffix("")
        # shutil.make_archive añade la extensión.
        try:
            shutil.make_archive(
                str(base), "zip", root_dir=str(self.out_dir)
            )
        except Exception:
            pass
