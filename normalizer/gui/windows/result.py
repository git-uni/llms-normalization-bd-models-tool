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
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

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
        self._er_image_ref: ctk.CTkImage | None = None  # mantener viva

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
        s = self.gui_state
        if s.error_message:
            text = f"Error durante {s.error_phase or '?'}: {s.error_message}"
            fg = ("#fde2e2", "#5a1f1f")
            tcol = ("#7a1a1a", "#ffcaca")
        elif s.cancelled:
            text = "Ejecución cancelada por el usuario. Los artefactos producidos hasta el momento están disponibles abajo."
            fg = ("#fff4d6", "#5a4a1f")
            tcol = ("#7a5a1a", "#ffeac0")
        elif s.finished_ok:
            text = f"DDL generado en {self.out_dir}"
            fg = ("#e2f5e9", "#1f4a2a")
            tcol = ("#1a5a2a", "#caffd1")
        else:
            text = "Resultado"
            fg = ("transparent", "transparent")
            tcol = None

        banner = ctk.CTkFrame(self, fg_color=fg, corner_radius=8)
        banner.pack(fill="x")
        lbl = ctk.CTkLabel(
            banner, text=text, anchor="w", wraplength=950, justify="left"
        )
        if tcol is not None:
            lbl.configure(text_color=tcol)
        lbl.pack(fill="x", padx=14, pady=10)

    def _build_tabs(self) -> None:
        assert self.out_dir is not None
        ddl_path = self.out_dir / "04_ddl.sql"
        design_path = self.out_dir / "03_design.md"
        analysis_path = self.out_dir / "02_analysis.md"
        discovery_path = self.out_dir / "00_discovery" / "discovery.md"

        # Diagrama ER — pestaña por defecto.
        er_tab = self.tabs.add("Diagrama ER")
        self._build_er_tab(er_tab, ddl_path)

        if design_path.exists():
            mv_design = MarkdownView(self.tabs.add("Diseño"))
            mv_design.render(design_path.read_text(encoding="utf-8"))
            mv_design.pack(fill="both", expand=True)

        if ddl_path.exists():
            sv = SqlView(self.tabs.add("DDL"))
            sv.render(ddl_path.read_text(encoding="utf-8"))
            sv.pack(fill="both", expand=True)

        if analysis_path.exists():
            mv_analysis = MarkdownView(self.tabs.add("Análisis"))
            mv_analysis.render(analysis_path.read_text(encoding="utf-8"))
            mv_analysis.pack(fill="both", expand=True)

        if self.gui_state.is_url and discovery_path.exists():
            mv_disc = MarkdownView(self.tabs.add("Descubrimiento"))
            mv_disc.render(discovery_path.read_text(encoding="utf-8"))
            mv_disc.pack(fill="both", expand=True)

        # Pestaña por defecto: si hay DDL, ER. Si no, la primera disponible.
        if not ddl_path.exists():
            for name in ("Diseño", "Análisis", "Descubrimiento"):
                try:
                    self.tabs.set(name)
                    break
                except ValueError:
                    continue

    def _build_er_tab(self, parent: ctk.CTkFrame, ddl_path: Path) -> None:
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
            img = Image.open(png)
            w, h = img.size
            # Encajar en una zona razonable preservando aspect ratio.
            max_w, max_h = 1000, 580
            scale = min(max_w / w, max_h / h, 1.0)
            target = (int(w * scale), int(h * scale))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=target)
            self._er_image_ref = ctk_img
            container = ctk.CTkScrollableFrame(parent)
            container.pack(fill="both", expand=True)
            ctk.CTkLabel(container, image=ctk_img, text="").pack(pady=8)
            ctk.CTkLabel(
                parent,
                text=f"Generado en: {png.name}",
                text_color="gray",
            ).pack(side="bottom", pady=(2, 0))
        except Exception as e:
            ctk.CTkLabel(
                parent,
                text=f"No se pudo cargar la imagen ER:\n{e}",
                text_color=("#b30000", "#ff7a7a"),
            ).pack(expand=True)

    def _build_graphviz_missing(self, parent: ctk.CTkFrame) -> None:
        msg = ctk.CTkFrame(parent, fg_color="transparent")
        msg.pack(expand=True)
        ctk.CTkLabel(
            msg,
            text="Graphviz no está instalado",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(0, 8))
        instr = (
            "El diagrama ER necesita el binario `dot` de Graphviz para renderizarse.\n\n"
            "Instálalo según tu sistema operativo:\n\n"
            "  • Windows:  winget install Graphviz.Graphviz\n"
            "  • macOS:    brew install graphviz\n"
            "  • Linux:    sudo apt install graphviz  (o equivalente)\n\n"
            "Luego, vuelve a lanzar la GUI. Las demás pestañas (Diseño, DDL,\n"
            "Análisis, Descubrimiento) están disponibles ya."
        )
        ctk.CTkLabel(msg, text=instr, justify="left").pack()

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
