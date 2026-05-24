"""Bucle del agente de descubrimiento.

Punto de entrada: `discover_from_url(url, agent_provider, out_dir)`.

Clona el repo, deja que el LLM use las tools de `tools.py` para localizar la
evidencia relevante, copia esa evidencia a `out_dir/00_discovery/evidence/` y
escribe la traza de decisiones en `out_dir/00_discovery/discovery.md`. Devuelve
la ruta al directorio de evidencia, que el pipeline existente consume como un
directorio curado.
"""

from pathlib import Path

from normalizer.discovery.filesystem import build_tree_summary
from normalizer.discovery.repo import clone_repo
from normalizer.discovery.tools import (
    ALL_TOOLS,
    DiscoveryState,
    dispatch,
)
from normalizer.prompts import DISCOVERY_SYSTEM
from normalizer.providers import LLMProvider, Message

MAX_ITERS = 20
MAX_FILES = 15


def discover_from_url(
    url: str,
    agent_provider: LLMProvider,
    out_dir: Path,
    *,
    max_iters: int = MAX_ITERS,
    max_files: int = MAX_FILES,
) -> Path:
    repo_root = clone_repo(url)
    state = DiscoveryState(
        repo_root=repo_root,
        discovery_dir=out_dir / "00_discovery",
    )
    tree = build_tree_summary(repo_root)

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
    for i in range(max_iters):
        iters_used = i + 1
        response = agent_provider.chat(messages, ALL_TOOLS)
        messages.append(response.assistant_message)

        if not response.tool_calls:
            # El modelo respondió sin tools — sin `done` no hay forma de
            # cerrar limpio. Lo forzamos como terminación con aviso.
            state.summary = (
                (state.summary or "")
                + "\n\n[WARN: el agente respondió sin llamar a tools; "
                "cerrando con la evidencia recopilada hasta ahora.]"
            )
            break

        for call in response.tool_calls:
            result = dispatch(call, state, max_files=max_files)
            messages.append(
                Message(
                    role="tool",
                    content=result,
                    tool_call_id=call.id,
                    tool_name=call.name,
                )
            )

        if state.is_done:
            break

    if not state.is_done and iters_used >= max_iters:
        state.summary = (
            (state.summary or "")
            + f"\n\n[WARN: presupuesto de {max_iters} iteraciones agotado "
            "sin que el agente llamara a `done`.]"
        )

    _write_discovery_md(state, url=url, iters_used=iters_used)
    return state.evidence_dir


def _write_discovery_md(
    state: DiscoveryState, *, url: str, iters_used: int
) -> None:
    lines: list[str] = [
        "# Descubrimiento del modelo documental",
        "",
        f"- **URL:** {url}",
        f"- **Repo local:** `{state.repo_root}`",
        f"- **Iteraciones del agente:** {iters_used}",
        f"- **Archivos seleccionados:** {len(state.selected)}",
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

    (state.discovery_dir / "discovery.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
