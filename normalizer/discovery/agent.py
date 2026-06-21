"""Bucle del agente de descubrimiento.

Punto de entrada: `discover_from_url(url, agent_provider, out_dir)`.

Clona el repo, deja que el LLM use las tools de `tools.py` para localizar la
evidencia relevante, copia esa evidencia a `out_dir/00_discovery/evidence/` y
escribe la traza de decisiones en `out_dir/00_discovery/discovery.md`. Devuelve
la ruta al directorio de evidencia, que el pipeline existente consume como un
directorio curado.

El argumento opcional `cancel_event` permite cancelar el bucle desde fuera
(p. ej. desde la GUI) entre iteraciones: si está señalizado, el agente
escribe la traza con la evidencia recopilada hasta ese momento y levanta
`PipelineCancelled`.
"""

import threading
from pathlib import Path

from normalizer._log import log
from normalizer.discovery.filesystem import MAX_TREE_ENTRIES, build_tree_summary
from normalizer.discovery.repo import clone_repo
from normalizer.discovery.tools import (
    ALL_TOOLS,
    DiscoveryState,
    TurnTrace,
    dispatch,
)
from normalizer.pipeline import PipelineCancelled
from normalizer.prompts import DISCOVERY_SYSTEM
from normalizer.providers import LLMProvider, Message, ToolCall

MAX_ITERS = 30
MAX_FILES = 30


def discover_from_url(
    url: str,
    agent_provider: LLMProvider,
    out_dir: Path,
    *,
    max_iters: int = MAX_ITERS,
    max_files: int = MAX_FILES,
    max_tree_entries: int = MAX_TREE_ENTRIES,
    cancel_event: threading.Event | None = None,
) -> Path:
    repo_root = clone_repo(url)
    state = DiscoveryState(
        repo_root=repo_root,
        discovery_dir=out_dir / "00_discovery",
    )
    tree = build_tree_summary(repo_root, max_entries=max_tree_entries)
    # Persistimos el árbol que el agente recibe en su primer mensaje user.
    # Es la única "vista del mundo" que tiene de partida; saber exactamente
    # qué vio es imprescindible para diagnosticar runs donde el agente "no
    # encuentra" algo que sí está en el repo.
    (state.discovery_dir / "tree.txt").write_text(tree, encoding="utf-8")
    log(
        f"Agente arrancado (max_iters={max_iters}, max_files={max_files}, "
        f"max_tree={max_tree_entries}, árbol={len(tree.splitlines())} entradas)"
    )

    messages: list[Message] = [
        Message(role="system", content=DISCOVERY_SYSTEM),
        Message(
            role="user",
            content=(
                f"Repositorio clonado: {url}\n\n"
                f"Árbol del repositorio (filtrado):\n```\n{tree}\n```\n\n"
                "Localiza la evidencia relevante y termina con `done`."
            ),
        ),
    ]

    iters_used = 0
    cancelled = False
    for i in range(max_iters):
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            log("Agente cancelado por el usuario.")
            state.summary = (
                (state.summary or "")
                + "\n\n[Cancelado por el usuario tras "
                + f"{iters_used} iteración(es).]"
            )
            break
        iters_used = i + 1
        response = agent_provider.chat(messages, ALL_TOOLS)
        messages.append(response.assistant_message)

        if not response.tool_calls:
            # El modelo respondió sin tools — sin `done` no hay forma de
            # cerrar limpio. Lo forzamos como terminación con aviso.
            state.turns.append(
                TurnTrace(iter=iters_used, calls=["(respuesta sin tool_calls)"])
            )
            log(f"[iter {iters_used:02d}] -> (sin tool_calls — cerrando)")
            state.summary = (
                (state.summary or "")
                + "\n\n[WARN: el agente respondió sin llamar a tools; "
                "cerrando con la evidencia recopilada hasta ahora.]"
            )
            break

        state.turns.append(
            TurnTrace(
                iter=iters_used,
                calls=[_format_call(c) for c in response.tool_calls],
            )
        )
        log(
            f"[iter {iters_used:02d}] -> "
            f"{' , '.join(state.turns[-1].calls)}"
        )

        for call in response.tool_calls:
            # Chequeo dentro del bucle de tools: si el agente batchea N
            # `select_evidence`/`read_file`/etc. en una sola respuesta, sin
            # esto el cancel esperaría a despachar las N. Con esto, se
            # atiende entre tool y tool — usualmente <1s.
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                log("Agente cancelado por el usuario (mid-batch).")
                state.summary = (
                    (state.summary or "")
                    + f"\n\n[Cancelado por el usuario durante el batch "
                    + f"de la iteración {iters_used}.]"
                )
                break
            result = dispatch(call, state, max_files=max_files)
            messages.append(
                Message(
                    role="tool",
                    content=result,
                    tool_call_id=call.id,
                    tool_name=call.name,
                )
            )

        if cancelled:
            break

        if state.is_done:
            log(
                f"Agente done — {len(state.selected)} archivos seleccionados "
                f"en {iters_used} iter."
            )
            break

    if not state.is_done and iters_used >= max_iters:
        log(f"WARN: presupuesto de {max_iters} iter agotado sin done.")
        state.summary = (
            (state.summary or "")
            + f"\n\n[WARN: presupuesto de {max_iters} iteraciones agotado "
            "sin que el agente llamara a `done`.]"
        )

    _write_discovery_md(state, url=url, iters_used=iters_used)
    if cancelled:
        raise PipelineCancelled("Cancelado durante el descubrimiento")
    return state.evidence_dir


def _format_call(call: ToolCall) -> str:
    """Formato compacto de una ToolCall para la traza turno a turno.

    Renderiza solo lo que distingue una llamada de otra (paths, patrones); el
    `reason` de `select_evidence` y el `summary` de `done` se truncan porque
    son texto libre y harían ilegible la tabla.
    """
    args = call.arguments or {}
    if call.name == "select_evidence":
        path = args.get("path", "")
        reason = args.get("reason", "")
        if len(reason) > 40:
            reason = reason[:37] + "…"
        return f"select_evidence({path}, reason={reason!r})"
    if call.name == "grep":
        pattern = args.get("pattern", "")
        glob = args.get("glob", "")
        glob_part = f", glob={glob!r}" if glob else ""
        return f"grep({pattern!r}{glob_part})"
    if call.name == "done":
        return "done(summary=…)"
    if "path" in args:
        return f"{call.name}({args['path']})"
    return f"{call.name}({args})"


def _write_discovery_md(
    state: DiscoveryState, *, url: str, iters_used: int
) -> None:
    total_calls = sum(len(t.calls) for t in state.turns)
    if iters_used:
        calls_line = (
            f"- **Tool calls totales:** {total_calls} "
            f"(promedio {total_calls / iters_used:.1f}/iter)"
        )
    else:
        calls_line = f"- **Tool calls totales:** {total_calls}"
    tree_path = state.discovery_dir / "tree.txt"
    tree_lines = (
        len(tree_path.read_text(encoding="utf-8").splitlines())
        if tree_path.exists()
        else 0
    )
    lines: list[str] = [
        "# Descubrimiento del modelo documental",
        "",
        f"- **URL:** {url}",
        f"- **Repo local:** `{state.repo_root}`",
        f"- **Iteraciones del agente:** {iters_used}",
        calls_line,
        f"- **Archivos seleccionados:** {len(state.selected)}",
        f"- **Árbol entregado al agente:** `tree.txt` ({tree_lines} líneas)",
        "",
        "## Resumen del agente",
        "",
        state.summary or "(el agente no devolvió resumen)",
        "",
        "## Evidencia seleccionada",
        "",
    ]
    if not state.selected:
        lines.append("(ninguna)")
    else:
        for sel in state.selected:
            lines.append(f"### `{sel.rel_path}`")
            lines.append("")
            lines.append(sel.reason)
            lines.append("")

    lines.extend(
        [
            "## Traza turno a turno",
            "",
            "Cada fila es una iteración del bucle = una petición al LLM. "
            "Una fila con varias entradas significa que el modelo batcheó "
            "esos tool_calls en una sola respuesta (consume 1 RPM en vez de N).",
            "",
            "| Iter | Tool calls |",
            "| ---: | --- |",
        ]
    )
    if not state.turns:
        lines.append("| — | (sin turnos registrados) |")
    else:
        for turn in state.turns:
            calls_md = "<br>".join(f"`{c}`" for c in turn.calls)
            lines.append(f"| {turn.iter} | {calls_md} |")
    lines.append("")

    (state.discovery_dir / "discovery.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
