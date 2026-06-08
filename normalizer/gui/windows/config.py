"""Pantalla 1 — Configuración.

Formulario único con tres bloques: entrada (archivo/directorio/URL),
configuración de LLM (proveedor, modelos, directorio de salida) y
credenciales (campo enmascarado por proveedor, con persistencia opcional en
`.env`). El botón "Ejecutar" se habilita solo cuando todos los campos
obligatorios están completos y hay API key disponible para el proveedor
seleccionado.
"""

import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from normalizer.gui.controller import (
    ENV_KEY_BY_PROVIDER,
    persist_api_key,
    resolve_default_out_dir,
)
from normalizer.gui.state import GuiState
from normalizer.providers import (
    DEFAULT_AGENT_MODELS,
    DEFAULT_MODELS,
    available_providers,
)


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@"))


class ConfigScreen(ctk.CTkFrame):
    def __init__(self, app: ctk.CTk) -> None:
        super().__init__(app)
        self.app = app
        self.gui_state: GuiState = app.gui_state

        self._build()
        self._sync_from_state()
        self._refresh_run_button()

    # ------------------------------------------------------------------
    # Construcción de widgets
    # ------------------------------------------------------------------

    def _build(self) -> None:
        ctk.CTkLabel(
            self,
            text="Configuración",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self,
            text="Define la entrada, el proveedor de LLM y las credenciales.",
            text_color="gray",
        ).pack(anchor="w", pady=(0, 8))

        # Acceso rápido a resultados de una ejecucion previa (sin re-ejecutar).
        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.pack(side="top")
        ctk.CTkButton(
            quick,
            text="Abrir resultados existentes...",
            command=self._open_existing,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
            hover_color=("steelblue2"),
            width=220,
            height=26,
        ).pack(side="left", padx=8, pady=(0, 12))

        # Bloque entrada -------------------------------------------------
        block_in = self._make_block("1. Entrada")
        self.mode_sel = ctk.CTkSegmentedButton(
            block_in,
            values=["Archivo", "Directorio", "URL"],
            command=self._on_mode_change,
        )
        self.mode_sel.set("Archivo")
        self.mode_sel.pack(fill="x", pady=(0, 8))

        self._input_value_var = ctk.StringVar()
        self._input_value_var.trace_add("write", lambda *_: self._refresh_run_button())
        self.input_row = ctk.CTkFrame(block_in, fg_color="transparent")
        self.input_row.pack(fill="x")
        self.input_entry = ctk.CTkEntry(
            self.input_row,
            textvariable=self._input_value_var,
            placeholder_text="Selecciona un archivo...",
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.browse_btn = ctk.CTkButton(
            self.input_row, text="Examinar...", width=110, command=self._browse
        )
        self.browse_btn.pack(side="left")

        # Bloque LLM y salida -------------------------------------------
        block_llm = self._make_block("2. LLM y directorio de salida")

        row1 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row1, text="Proveedor", width=140, anchor="w").pack(side="left")
        self.provider_sel = ctk.CTkOptionMenu(
            row1,
            values=list(available_providers()),
            command=self._on_provider_change,
        )
        self.provider_sel.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row2, text="Modelo pipeline", width=140, anchor="w").pack(
            side="left"
        )
        self.model_cb = ctk.CTkComboBox(row2, values=[""])
        self.model_cb.pack(side="left", fill="x", expand=True)

        row3 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row3, text="Modelo agente", width=140, anchor="w").pack(
            side="left"
        )
        self.agent_model_cb = ctk.CTkComboBox(row3, values=[""])
        self.agent_model_cb.pack(side="left", fill="x", expand=True)

        row4 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row4.pack(fill="x")
        ctk.CTkLabel(row4, text="Directorio salida", width=140, anchor="w").pack(
            side="left"
        )
        self._out_dir_var = ctk.StringVar()
        ctk.CTkEntry(row4, textvariable=self._out_dir_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(
            row4, text="Examinar...", width=110, command=self._browse_out_dir
        ).pack(side="left")

        # Bloque credenciales -------------------------------------------
        block_keys = self._make_block("3. Credenciales del proveedor")
        self.key_label = ctk.CTkLabel(block_keys, text="", anchor="w")
        self.key_label.pack(fill="x", pady=(0, 4))

        key_row = ctk.CTkFrame(block_keys, fg_color="transparent")
        key_row.pack(fill="x")
        self._api_key_var = ctk.StringVar()
        self._api_key_var.trace_add("write", lambda *_: self._refresh_run_button())
        self.key_entry = ctk.CTkEntry(
            key_row,
            textvariable=self._api_key_var,
            show="*",
            placeholder_text="Pega aquí tu API key...",
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.change_key_btn = ctk.CTkButton(
            key_row, text="Cambiar", width=110, command=self._unlock_key
        )
        self.change_key_btn.pack(side="left")

        ctk.CTkLabel(
            block_keys,
            text=(
                "Si introduces una clave nueva, se guardará en .env "
                "(excluido del repositorio por .gitignore)."
            ),
            text_color="gray",
            anchor="w",
            wraplength=900,
        ).pack(fill="x", pady=(6, 0))

        # Botón ejecutar -------------------------------------------------
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", pady=(20, 0))
        self.error_label = ctk.CTkLabel(
            bottom, text="", text_color=("#b30000", "#ff7a7a"), anchor="w"
        )
        self.error_label.pack(side="left", fill="x", expand=True)
        self.run_btn = ctk.CTkButton(
            bottom, text="Ejecutar →", command=self._on_run, width=140
        )
        self.run_btn.pack(side="right")

    def _make_block(self, title: str) -> ctk.CTkFrame:
        block = ctk.CTkFrame(self)
        block.pack(fill="x", pady=(0, 12))
        inner = ctk.CTkFrame(block, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            inner, text=title, font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(fill="x", pady=(0, 8))
        return inner

    # ------------------------------------------------------------------
    # Sincronización con estado
    # ------------------------------------------------------------------

    def _sync_from_state(self) -> None:
        s = self.gui_state
        # Provider
        self.provider_sel.set(s.provider)
        self._on_provider_change(s.provider, refresh=False)
        # Mode + input
        mode_label = {"file": "Archivo", "dir": "Directorio", "url": "URL"}[
            s.input_mode
        ]
        self.mode_sel.set(mode_label)
        self._input_value_var.set(s.input_value)
        # out_dir
        if s.out_dir is None:
            s.out_dir = resolve_default_out_dir()
        self._out_dir_var.set(str(s.out_dir))
        # Models
        if s.model:
            self.model_cb.set(s.model)
        if s.agent_model:
            self.agent_model_cb.set(s.agent_model)
        self._refresh_agent_model_enabled()

    def _on_provider_change(self, value: str, refresh: bool = True) -> None:
        # Prerrellena modelos por defecto del proveedor seleccionado.
        default_pipeline = DEFAULT_MODELS.get(value, "")
        default_agent = DEFAULT_AGENT_MODELS.get(value, "")
        # Solo prerrellenamos si el campo está vacío o tenía el default del
        # proveedor anterior — no pisamos un valor que el usuario haya tecleado.
        if not self.model_cb.get() or self.model_cb.get() in DEFAULT_MODELS.values():
            self.model_cb.configure(values=[default_pipeline])
            self.model_cb.set(default_pipeline)
        if (
            not self.agent_model_cb.get()
            or self.agent_model_cb.get() in DEFAULT_AGENT_MODELS.values()
        ):
            self.agent_model_cb.configure(values=[default_agent])
            self.agent_model_cb.set(default_agent)
        self._sync_key_field()
        if refresh:
            self._refresh_run_button()

    def _on_mode_change(self, value: str) -> None:
        mode_map = {"Archivo": "file", "Directorio": "dir", "URL": "url"}
        self.gui_state.input_mode = mode_map[value]
        # Limpiar el input al cambiar de modo para evitar valores incompatibles.
        self._input_value_var.set("")
        if self.gui_state.input_mode == "url":
            self.input_entry.configure(placeholder_text="https://github.com/...")
            self.browse_btn.configure(state="disabled")
        elif self.gui_state.input_mode == "file":
            self.input_entry.configure(placeholder_text="Selecciona un archivo...")
            self.browse_btn.configure(state="normal")
        else:
            self.input_entry.configure(placeholder_text="Selecciona un directorio...")
            self.browse_btn.configure(state="normal")
        self._refresh_agent_model_enabled()
        self._refresh_run_button()

    def _refresh_agent_model_enabled(self) -> None:
        if self.gui_state.input_mode == "url":
            self.agent_model_cb.configure(state="normal")
        else:
            self.agent_model_cb.configure(state="disabled")

    def _sync_key_field(self) -> None:
        provider = self.provider_sel.get()
        env_key = ENV_KEY_BY_PROVIDER.get(provider, "")
        if not env_key:
            self.key_label.configure(text="(proveedor sin variable de entorno)")
            return
        if os.environ.get(env_key):
            self.key_label.configure(
                text=f"✓ {env_key} configurado en el entorno."
            )
            self._api_key_var.set("••••••••")
            self.key_entry.configure(state="disabled")
            self.change_key_btn.configure(state="normal")
        else:
            self.key_label.configure(
                text=f"⚠ Falta {env_key}. Introduce tu clave para continuar."
            )
            self._api_key_var.set("")
            self.key_entry.configure(state="normal")
            self.change_key_btn.configure(state="disabled")

    def _unlock_key(self) -> None:
        self._api_key_var.set("")
        self.key_entry.configure(state="normal")
        self.change_key_btn.configure(state="disabled")
        self.key_entry.focus()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        if self.gui_state.input_mode == "file":
            path = filedialog.askopenfilename(
                title="Selecciona archivo de entrada",
                filetypes=[("Todos", "*.*")],
            )
        elif self.gui_state.input_mode == "dir":
            path = filedialog.askdirectory(title="Selecciona directorio de entrada")
        else:
            return
        if path:
            self._input_value_var.set(path)

    def _browse_out_dir(self) -> None:
        path = filedialog.askdirectory(title="Selecciona directorio de salida")
        if path:
            self._out_dir_var.set(path)

    def _refresh_run_button(self) -> None:
        valid, reason = self._validate()
        if valid:
            self.error_label.configure(text="")
            self.run_btn.configure(state="normal")
        else:
            self.error_label.configure(text=reason)
            self.run_btn.configure(state="disabled")

    def _validate(self) -> tuple[bool, str]:
        value = self._input_value_var.get().strip()
        if not value:
            return False, "Falta la entrada."
        if self.gui_state.input_mode == "url":
            if not _is_url(value):
                return False, "La URL debe empezar por http://, https:// o git@."
        elif self.gui_state.input_mode == "file":
            if not Path(value).is_file():
                return False, "El archivo no existe."
        else:
            if not Path(value).is_dir():
                return False, "El directorio no existe."

        provider = self.provider_sel.get()
        env_key = ENV_KEY_BY_PROVIDER.get(provider, "")
        if env_key and not os.environ.get(env_key):
            typed = self._api_key_var.get().strip()
            if not typed:
                return False, f"Falta la clave {env_key}."

        if not self._out_dir_var.get().strip():
            return False, "Falta el directorio de salida."
        return True, ""

    def _on_run(self) -> None:
        # Persistir state desde widgets.
        s = self.gui_state
        s.provider = self.provider_sel.get()
        s.model = self.model_cb.get().strip()
        s.agent_model = self.agent_model_cb.get().strip()
        s.input_value = self._input_value_var.get().strip()
        s.out_dir = Path(self._out_dir_var.get().strip())

        # Persistir API key si el usuario la ha tecleado.
        env_key = ENV_KEY_BY_PROVIDER.get(s.provider, "")
        if env_key and not os.environ.get(env_key):
            typed = self._api_key_var.get().strip()
            if typed and typed != "••••••••":
                persist_api_key(env_key, typed)

        self.app.show_run()

    def _open_existing(self) -> None:
        # Carga un out_dir de una corrida previa y salta a la pantalla de
        # resultado sin re-ejecutar el pipeline. Útil cuando el usuario
        # quiere revisar el DDL o el diagrama ER de una ejecución antigua,
        # o cuando la GUI se cerró sin haber visto el resultado.
        path = filedialog.askdirectory(
            title="Selecciona el directorio de resultados (out-...)"
        )
        if not path:
            return
        out_dir = Path(path)
        ddl_path = out_dir / "04_ddl.sql"
        if not ddl_path.exists():
            messagebox.showerror(
                "Sin resultados",
                f"El directorio '{out_dir.name}' no contiene '04_ddl.sql'.\n\n"
                "Selecciona el directorio de una ejecucion que haya llegado "
                "hasta la fase de DDL.",
            )
            return

        s = self.gui_state
        s.reset_run()
        s.out_dir = out_dir
        s.finished_ok = True
        # Inferimos el modo de la ejecucion por la presencia de 00_discovery/:
        # solo se crea cuando el agente intervino (entrada URL).
        if (out_dir / "00_discovery").exists():
            s.input_mode = "url"
        else:
            s.input_mode = "dir"
        s.input_value = str(out_dir)
        self.app.show_result()
