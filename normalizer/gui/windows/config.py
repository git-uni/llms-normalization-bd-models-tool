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

# Paleta para inputs: surface-container-low (un nivel por debajo del
# bloque que los contiene, surface-container, para que se "hundan"
# sutilmente como campos editables) + outline-variant para bordes.
# Sustituye el default beige cálido de CTk que chocaba con la paleta azul.
_INPUT_FG = ("#e7eef8", "#181c20")
_INPUT_BORDER = ("#a8bcd9", "#3a4456")
_INPUT_BUTTON = ("#1f6aa5", "#3a8fd6")  # primary para botones de combo

from normalizer.gui.components.tooltip import attach_tooltip
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
    build_provider,
)


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@"))


class ConfigScreen(ctk.CTkFrame):
    def __init__(self, app: ctk.CTk) -> None:
        # transparent para heredar el azul del root: sin esto, el marco usa el
        # gris neutro por defecto de CTk (#dbdbdb), el único elemento sin azul,
        # que desentona con la paleta tonal de la herramienta.
        super().__init__(app, fg_color="transparent")
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

        # --- Barra inferior fija: el botón "Ejecutar" siempre visible -----
        # Se crea y empaqueta ANTES del área scrollable para que ésta (con
        # expand=True) ocupe solo el espacio central y el botón quede siempre
        # accesible aunque el formulario no quepa entero.
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        self.error_label = ctk.CTkLabel(
            bottom, text="",
            text_color=("#ba1a1a", "#ffb4ab"),  # error M3
            anchor="w",
        )
        self.error_label.pack(side="left", fill="x", expand=True)
        self.run_btn = ctk.CTkButton(
            bottom, text="Ejecutar →", command=self._on_run, width=140
        )
        self.run_btn.pack(side="right")

        # --- Contenido scrollable: los bloques del formulario -------------
        # Scrollable para que el formulario completo (cuatro bloques en modo
        # URL) quede accesible aunque la ventana esté a su tamaño mínimo.
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(side="top", fill="both", expand=True)

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
            fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
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
        self.model_cb = ctk.CTkComboBox(
            row2, values=[""],
            fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
            button_color=_INPUT_BUTTON, button_hover_color=_INPUT_BUTTON,
        )
        self.model_cb.pack(side="left", fill="x", expand=True)

        row3 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row3, text="Modelo agente", width=140, anchor="w").pack(
            side="left"
        )
        self.agent_model_cb = ctk.CTkComboBox(
            row3, values=[""],
            fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
            button_color=_INPUT_BUTTON, button_hover_color=_INPUT_BUTTON,
        )
        self.agent_model_cb.pack(side="left", fill="x", expand=True)

        # Texto auxiliar sobre el estado del catálogo (vacío si listado OK,
        # mensaje gris si no se pudo conectar al proveedor).
        self.models_status_label = ctk.CTkLabel(
            block_llm, text="", text_color="gray", anchor="w", wraplength=900,
        )
        self.models_status_label.pack(fill="x", pady=(0, 8))

        row4 = ctk.CTkFrame(block_llm, fg_color="transparent")
        row4.pack(fill="x")
        ctk.CTkLabel(row4, text="Directorio salida", width=140, anchor="w").pack(
            side="left"
        )
        self._out_dir_var = ctk.StringVar()
        ctk.CTkEntry(
            row4, textvariable=self._out_dir_var,
            fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
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
            fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.change_key_btn = ctk.CTkButton(
            key_row, text="Cambiar", width=110, command=self._unlock_key
        )
        self.change_key_btn.pack(side="left")

        ctk.CTkLabel(
            block_keys,
            text=(
                "Si introduces una clave nueva, se guardará en .env"
                
            ),
            text_color="gray",
            anchor="w",
            wraplength=900,
        ).pack(fill="x", pady=(6, 0))

        # Bloque agente (solo modo URL): se crea aquí pero se muestra u oculta
        # por completo según el modo de entrada (ver
        # _refresh_agent_block_visibility), porque solo es relevante en URL.
        self._block_agent = ctk.CTkFrame(
            self._scroll, corner_radius=12, fg_color=("#dfe7f2", "#1c2024"),
        )
        block_agent = ctk.CTkFrame(self._block_agent, fg_color="transparent")
        block_agent.pack(fill="x", padx=18, pady=16)
        ctk.CTkLabel(
            block_agent,
            text="4. Agente de descubrimiento (modo URL)",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(0, 12))
        # wraplength fijo y conservador: cabe a tamaño mínimo de ventana dentro
        # del frame scrollable, y justify a la izquierda evita el centrado raro
        # de las líneas envueltas. (Un wrap dinámico vía <Configure> recursaba:
        # cambiar wraplength altera la altura -> nuevo <Configure> -> bucle.)
        ctk.CTkLabel(
            block_agent,
            text=(
                "Presupuesto del agente que explora el repositorio.\n"
                "Limita cuánto explora (iteraciones y archivos seleccionados) y "
                "cuánto contexto recibe de partida (tamaño del árbol del "
                "repositorio), para ajustar el consumo de cuota del proveedor. "
            ),
            text_color="gray", anchor="w", justify="left", wraplength=760,
        ).pack(fill="x", pady=(0, 8))

        self._max_iters_var = ctk.StringVar()
        self._max_files_var = ctk.StringVar()
        self._max_tree_var = ctk.StringVar()
        for _var in (self._max_iters_var, self._max_files_var, self._max_tree_var):
            _var.trace_add("write", lambda *_: self._refresh_run_button())

        self._agent_budget_entries: list[ctk.CTkEntry] = []
        for label_text, var, tip in (
            (
                "Máx. iteraciones",
                self._max_iters_var,
                "Número máximo de turnos (una petición al LLM por turno) que el "
                "agente puede dar explorando el repositorio antes de abortar. "
                "Más iteraciones permiten una exploración más exhaustiva, pero "
                "consumen más cuota. Por defecto: 30.",
            ),
            (
                "Máx. archivos",
                self._max_files_var,
                "Número máximo de archivos que el agente puede marcar como "
                "evidencia relevante. Acota el tamaño de la entrada que luego "
                "recibe el pipeline. Por defecto: 30.",
            ),
            (
                "Máx. entradas del árbol",
                self._max_tree_var,
                "Número máximo de archivos y carpetas que se listan en el árbol "
                "del repositorio que el agente recibe en su primer mensaje. "
                "Bajarlo reduce el tamaño de ese mensaje (útil cuando el "
                "proveedor tiene un límite de tokens estrecho, p. ej. Groq); "
                "subirlo da más contexto inicial. Por defecto: 2000.",
            ),
        ):
            row = ctk.CTkFrame(block_agent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 8))
            # Icono "ⓘ" delante del texto del parámetro: pista visible de que
            # hay ayuda. El tooltip se asocia solo al icono (no al campo ni a la
            # etiqueta) para que aparezca de forma intencional al posar el
            # cursor sobre él.
            info = ctk.CTkLabel(
                row, text="ⓘ", width=18,
                text_color=("#1f6aa5", "#5aa0e0"),  # primary
                font=ctk.CTkFont(size=15),
                cursor="hand2",
            )
            info.pack(side="left", padx=(0, 6))
            attach_tooltip(info, tip)
            label = ctk.CTkLabel(row, text=label_text, width=182, anchor="w")
            label.pack(side="left")
            entry = ctk.CTkEntry(
                row, textvariable=var, width=120,
                fg_color=_INPUT_FG, border_color=_INPUT_BORDER,
            )
            entry.pack(side="left")
            self._agent_budget_entries.append(entry)

    def _make_block(self, title: str) -> ctk.CTkFrame:
        block = ctk.CTkFrame(
            self._scroll, corner_radius=12,
            fg_color=("#dfe7f2", "#1c2024"),  # surface-container
        )
        block.pack(fill="x", pady=(0, 12))
        inner = ctk.CTkFrame(block, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)
        ctk.CTkLabel(
            inner, text=title,
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(0, 12))
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
        # Presupuesto del agente
        self._max_iters_var.set(str(s.max_iters))
        self._max_files_var.set(str(s.max_files))
        self._max_tree_var.set(str(s.max_tree_entries))
        self._refresh_agent_model_enabled()
        self._refresh_agent_block_visibility()

    def _on_provider_change(self, value: str, refresh: bool = True) -> None:
        # Prerrellena los combos: si la API key del proveedor está
        # configurada, listamos su catálogo dinámicamente; si no, caemos al
        # default conocido y avisamos al usuario.
        default_pipeline = DEFAULT_MODELS.get(value, "")
        default_agent = DEFAULT_AGENT_MODELS.get(value, "")
        pipeline_models, agent_models, status_text = self._fetch_models(value)

        previous_pipeline = self.model_cb.get()
        previous_agent = self.agent_model_cb.get()
        all_defaults = set(DEFAULT_MODELS.values()) | set(DEFAULT_AGENT_MODELS.values())

        # Modelo pipeline: respetamos lo que el usuario haya escogido a mano
        # (cualquier valor que no sea un default conocido); si no, default.
        self.model_cb.configure(values=pipeline_models or [default_pipeline])
        if previous_pipeline and previous_pipeline not in all_defaults and previous_pipeline in pipeline_models:
            self.model_cb.set(previous_pipeline)
        elif default_pipeline and default_pipeline in (pipeline_models or [default_pipeline]):
            self.model_cb.set(default_pipeline)
        elif pipeline_models:
            self.model_cb.set(pipeline_models[0])
        else:
            self.model_cb.set(default_pipeline)

        # Modelo agente: misma lógica. `CTkComboBox.set()` no surte efecto
        # si el widget está disabled, así que lo habilitamos durante el
        # update y restauramos el estado correcto después.
        previous_state = self.agent_model_cb.cget("state")
        self.agent_model_cb.configure(state="normal", values=agent_models or [default_agent])
        if previous_agent and previous_agent not in all_defaults and previous_agent in agent_models:
            self.agent_model_cb.set(previous_agent)
        elif default_agent and default_agent in (agent_models or [default_agent]):
            self.agent_model_cb.set(default_agent)
        elif agent_models:
            self.agent_model_cb.set(agent_models[0])
        else:
            self.agent_model_cb.set(default_agent)
        self.agent_model_cb.configure(state=previous_state)

        self.models_status_label.configure(text=status_text)
        self._sync_key_field()
        self._refresh_agent_model_enabled()
        if refresh:
            self._refresh_run_button()

    def _fetch_models(
        self, provider_name: str
    ) -> tuple[list[str], list[str], str]:
        """Lista modelos del proveedor o devuelve fallback con mensaje.

        Crea un provider temporal (solo para listar; la corrida real construye
        otro en el controller). Si falla — falta de API key o error de red —
        devuelve listas vacías y un mensaje para mostrar al usuario.
        """
        env_key = ENV_KEY_BY_PROVIDER.get(provider_name, "")
        if env_key and not os.environ.get(env_key):
            return [], [], (
                f"Configura la {env_key} para listar el catálogo de modelos "
                "del proveedor. Mientras tanto, se muestra el modelo por defecto."
            )
        try:
            tmp = build_provider(name=provider_name, model=None)
            pipeline_models = tmp.list_models(for_agent=False)
            agent_models = tmp.list_models(for_agent=True)
        except Exception as e:
            return [], [], (
                f"No se pudo listar el catálogo de modelos del proveedor: {e}. "
                "Se muestra el modelo por defecto."
            )
        return pipeline_models, agent_models, ""

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
        self._refresh_agent_block_visibility()
        self._refresh_run_button()

    def _refresh_agent_model_enabled(self) -> None:
        # El modelo del agente solo aplica en modo URL.
        new_state = "normal" if self.gui_state.input_mode == "url" else "disabled"
        self.agent_model_cb.configure(state=new_state)

    def _refresh_agent_block_visibility(self) -> None:
        # El bloque del presupuesto del agente solo es relevante en modo URL:
        # se muestra u oculta por completo (no solo deshabilitado) según el modo.
        if getattr(self, "_block_agent", None) is None:
            return
        if self.gui_state.input_mode == "url":
            self._block_agent.pack(fill="x", pady=(0, 12))
        else:
            self._block_agent.pack_forget()

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

        if self.gui_state.input_mode == "url":
            ok, reason = self._validate_budget()
            if not ok:
                return False, reason
        return True, ""

    def _validate_budget(self) -> tuple[bool, str]:
        for label, var in (
            ("máx. iteraciones", self._max_iters_var),
            ("máx. archivos", self._max_files_var),
            ("máx. entradas del árbol", self._max_tree_var),
        ):
            raw = var.get().strip()
            if not raw.isdigit() or int(raw) < 1:
                return False, f"El campo «{label}» del agente debe ser un entero positivo."
        return True, ""

    def _on_run(self) -> None:
        # Persistir state desde widgets.
        s = self.gui_state
        s.provider = self.provider_sel.get()
        s.model = self.model_cb.get().strip()
        s.agent_model = self.agent_model_cb.get().strip()
        s.input_value = self._input_value_var.get().strip()
        s.out_dir = Path(self._out_dir_var.get().strip())

        # Presupuesto del agente: parseo defensivo. En modo no-URL los campos
        # están deshabilitados y se ignoran; si el valor no es un entero válido
        # conservamos el del estado (su default).
        for var, attr in (
            (self._max_iters_var, "max_iters"),
            (self._max_files_var, "max_files"),
            (self._max_tree_var, "max_tree_entries"),
        ):
            raw = var.get().strip()
            if raw.isdigit() and int(raw) >= 1:
                setattr(s, attr, int(raw))

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
