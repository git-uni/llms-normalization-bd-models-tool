#!/usr/bin/env bash
# Reconstruye MemoriaTFG.v1.docx desde los borradores cap0X.md.
#
# Dependencias:
#   - pandoc >= 3.x (https://pandoc.org)
#   - @mermaid-js/mermaid-cli (npm i -g) — solo si se quieren re-renderizar diagramas
#
# Uso: ./build.sh        (re-renderiza diagramas + construye docx)
#      ./build.sh --no-mmd   (omite mermaid, asume PNGs ya generados)

set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" != "--no-mmd" ]]; then
  echo "[1/3] Extrayendo bloques mermaid..."
  mkdir -p assets/mmd assets/png
  python - <<'PY'
import re, pathlib
# Los diagramas mermaid (Gantt/WBS) viven en el capítulo de Planificación,
# que tras insertar el capítulo de Definiciones es cap03.md. Sus figuras
# conservan el prefijo de archivo fig-02-* (identificador de build estable,
# desacoplado del número de capítulo) que el propio cap03.md referencia.
for ch in ['cap03.md']:
    text = pathlib.Path(ch).read_text(encoding='utf-8')
    num = '02'
    blocks = re.findall(r'\x60\x60\x60mermaid\n(.*?)\n\x60\x60\x60', text, re.DOTALL)
    for i, b in enumerate(blocks, 1):
        pathlib.Path(f'assets/mmd/fig-{num}-{i}.mmd').write_text(b, encoding='utf-8')
    print(f'  {ch}: {len(blocks)} bloques')
PY

  echo "[2/3] Renderizando diagramas con mmdc..."
  for f in assets/mmd/*.mmd; do
    base=$(basename "$f" .mmd)
    mmdc -i "$f" -o "assets/png/${base}.png" -b white -w 1200 >/dev/null 2>&1
  done
fi

echo "[3/3] Construyendo MemoriaTFG.v1.docx con pandoc..."
pandoc \
  --reference-doc=../PlantillaTFGEII.DesarrolloV2ESP.docx \
  --toc --toc-depth=3 \
  --resource-path=. \
  -f markdown+pipe_tables+grid_tables+raw_html+fenced_code_blocks \
  -t docx \
  cap01.md cap02.md cap03.md cap04.md cap05.md cap06.md cap07.md cap08.md cap09.md cap10.md cap11.md \
  -o MemoriaTFG.v1.docx

ls -lh MemoriaTFG.v1.docx
echo "OK."
