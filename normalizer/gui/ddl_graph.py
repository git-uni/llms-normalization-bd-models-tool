"""Generador de diagrama ER a partir del DDL Oracle producido por el pipeline.

Parsea `04_ddl.sql` con un parser por regex deliberadamente sencillo (el DDL
que el pipeline emite tiene una estructura predecible: `CREATE TABLE name (...)`
con columnas y `CONSTRAINT ... FOREIGN KEY (col) REFERENCES other(col)`), monta
un grafo Graphviz con un nodo por tabla y una arista por FK, y delega el
render al binario Graphviz vía `graphviz` lib.

Si Graphviz no está en el PATH del sistema, `render_to_png` devuelve `None`
y la GUI muestra un mensaje accionable con instrucciones de instalación.
Las demás pestañas del resultado siguen funcionando.
"""

import os
import platform
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import graphviz

# Tiempo máximo del render de Graphviz. Un layout patológico (grafos grandes
# tipo Habitica) podía colgar el proceso indefinidamente; al expirar, la GUI
# muestra el mensaje accionable (mismo camino que cuando falta el binario).
_RENDER_TIMEOUT_S = 30

_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_FK_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(\s*(\w+)\s*\)\s*REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
    re.IGNORECASE,
)
_PK_RE = re.compile(r"PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE)


def _strip_fences(ddl: str) -> str:
    """El pipeline a veces envuelve el DDL en ```sql ... ```."""
    s = ddl.strip()
    s = re.sub(r"^```sql\s*\n", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^```\s*\n", "", s)
    s = re.sub(r"\n```\s*$", "", s)
    return s


def _split_table_body(body: str) -> list[str]:
    """Divide el cuerpo de CREATE TABLE por comas a profundidad 0."""
    items: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return items


def parse_ddl(ddl: str) -> tuple[
    dict[str, list[tuple[str, str, bool]]],  # tabla → [(col, tipo, is_pk)]
    list[tuple[str, str, str, str]],  # FKs (from_t, from_c, to_t, to_c)
]:
    """Devuelve (tablas, fks).

    Cada tabla mapea a una lista de tuplas (columna, tipo, es_pk).
    """
    ddl = _strip_fences(ddl)
    tables: dict[str, list[tuple[str, str, bool]]] = {}
    fks: list[tuple[str, str, str, str]] = []

    for m in _CREATE_RE.finditer(ddl):
        tname = m.group(1)
        body = m.group(2)
        items = _split_table_body(body)
        pk_cols: set[str] = set()
        cols: list[tuple[str, str, bool]] = []
        for raw in items:
            item = raw.strip().rstrip(",")
            if not item:
                continue
            upper = item.upper()
            if upper.startswith("CONSTRAINT") or upper.startswith("PRIMARY KEY") or upper.startswith("FOREIGN KEY"):
                fk = _FK_RE.search(item)
                if fk:
                    fks.append((tname, fk.group(1), fk.group(2), fk.group(3)))
                pk = _PK_RE.search(item)
                if pk:
                    for c in pk.group(1).split(","):
                        pk_cols.add(c.strip())
                continue
            tokens = item.split()
            if not tokens:
                continue
            cname = tokens[0]
            ctype = tokens[1] if len(tokens) > 1 else ""
            cols.append((cname, ctype, False))
        # Re-marcar PKs ahora que ya hemos visto los constraints.
        cols = [(c, t, c in pk_cols) for (c, t, _) in cols]
        tables[tname] = cols
    return tables, fks


def _pick_layout(
    n_tables: int, fks: list[tuple[str, str, str, str]]
) -> tuple[str, dict[str, str]]:
    """Selecciona engine y atributos de grafo según la topología.

    Si el grafo tiene un *hub* (una tabla con muchas FKs entrantes,
    típicamente `Users` en aplicaciones reales) el engine jerárquico `dot`
    apila todas las aristas en paralelo y produce un caos ilegible. En esos
    casos `sfdp` (force-directed) coloca el hub en el centro y distribuye
    los demás nodos alrededor, mucho más legible.

    Para grafos modestos sin hub, `dot` con curvas suaves y `concentrate`
    es lo más limpio y predecible.
    """
    max_incoming = max(
        Counter(to_t for _, _, to_t, _ in fks).values(), default=0
    )
    # `size`+`dpi` acotan el PNG resultante (Graphviz solo *reduce* el dibujo si
    # excede `size`): 40x40 a 100 dpi => ~4000 px máx por lado. Sin esta cota,
    # un esquema grande generaba un PNG enorme que desbordaba la memoria del
    # PhotoImage y podía chocar con el límite anti-bomba de PIL.
    if max_incoming > 10 or n_tables > 20:
        return "sfdp", {
            "overlap": "prism",
            "nodesep": "1.0",
            "ranksep": "1.0",
            "splines": "spline",
            "bgcolor": "transparent",
            "pad": "0.4",
            "size": "40,40",
            "dpi": "100",
        }
    return "dot", {
        "rankdir": "LR",
        "splines": "spline",
        "concentrate": "true",
        "nodesep": "0.4",
        "ranksep": "0.7",
        "bgcolor": "transparent",
        "pad": "0.4",
        "size": "40,40",
        "dpi": "100",
    }


def build_dot(ddl: str) -> tuple[str, str]:
    """Devuelve `(source DOT, engine)` con el layout adecuado al grafo."""
    tables, fks = parse_ddl(ddl)
    engine, graph_attr = _pick_layout(len(tables), fks)
    g = graphviz.Digraph(
        "ER",
        engine=engine,
        node_attr={
            "shape": "plaintext",
            "fontname": "Helvetica",
            "fontsize": "10",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "9",
            "color": "#555555",
        },
        graph_attr=graph_attr,
    )
    for tname, cols in tables.items():
        rows = [
            f'<TR><TD BGCOLOR="#e8f0fe"><B>{_xml(tname)}</B></TD></TR>'
        ]
        for cname, ctype, is_pk in cols:
            # Marcador ASCII de PK para evitar problemas de codificación en
            # consolas Windows; el render del PNG usa unicode sin problema
            # pero los logs/depuración pueden caer en cp1252.
            mark = "[PK] " if is_pk else ""
            type_part = (
                f' <FONT COLOR="#888888">{_xml(ctype)}</FONT>' if ctype else ""
            )
            rows.append(
                f'<TR><TD ALIGN="LEFT">{mark}{_xml(cname)}{type_part}</TD></TR>'
            )
        label = (
            '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
            + "".join(rows)
            + "</TABLE>>"
        )
        g.node(tname, label=label)
    for from_t, from_c, to_t, to_c in fks:
        if to_t not in tables:
            continue
        g.edge(from_t, to_t, xlabel=f"{from_c} → {to_c}")
    return g.source, engine


def _xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _ensure_graphviz_in_path() -> bool:
    """Localiza el binario `dot` y lo añade al PATH del proceso si hace falta.

    En Windows, `winget install Graphviz.Graphviz` actualiza el PATH del
    sistema pero el proceso ya corriendo conserva el PATH antiguo, el
    usuario tiene que reabrir la terminal o sufrirá un `ExecutableNotFound`
    pese a tener Graphviz instalado. Aquí miramos rutas estándar y, si el
    binario aparece, lo enganchamos al PATH del proceso sin esperar a un
    reinicio del shell.
    """
    if shutil.which("dot"):
        return True
    if platform.system() != "Windows":
        return False
    # Rutas típicas donde winget o el instalador oficial dejan Graphviz.
    candidates: list[Path] = [
        Path(r"C:\Program Files\Graphviz\bin"),
        Path(r"C:\Program Files (x86)\Graphviz\bin"),
    ]
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        packages = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        if packages.exists():
            candidates.extend(packages.glob("Graphviz.Graphviz*/bin"))
    for c in candidates:
        if (c / "dot.exe").exists():
            os.environ["PATH"] = str(c) + os.pathsep + os.environ.get("PATH", "")
            return True
    return False


def render_to_png(ddl: str, out_path_no_ext: Path) -> Path | None:
    """Renderiza el ER a PNG. Devuelve la ruta o None.

    Devuelve None si Graphviz no está, si el render excede el timeout o si
    falla por cualquier motivo; la GUI ya trata None mostrando el mensaje
    accionable. `out_path_no_ext` se pasa sin la extensión `.png`; aquí se añade.

    Se invoca el binario del engine con `subprocess.run(..., timeout=...)` en
    vez de `graphviz.Source(...).render()` porque la lib no expone timeout y un
    layout patológico podía colgar el proceso. El DOT se pasa por stdin, así que
    no se escribe ningún fichero `.gv` intermedio.
    """
    dot, engine = build_dot(ddl)
    _ensure_graphviz_in_path()
    engine_bin = shutil.which(engine)
    if engine_bin is None:
        return None
    png_path = out_path_no_ext.with_suffix(".png")
    try:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [engine_bin, "-Tpng", "-o", str(png_path)],
            input=dot.encode("utf-8"),
            capture_output=True,
            timeout=_RENDER_TIMEOUT_S,
            check=True,
        )
    except Exception:
        # TimeoutExpired, CalledProcessError, OSError, etc.: degradar a None.
        return None
    return png_path if png_path.exists() else None
