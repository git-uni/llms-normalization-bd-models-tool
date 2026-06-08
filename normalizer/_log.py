"""Log mínimo a stderr con timestamp relativo desde el arranque.

Pensado para que una corrida del CLI sea observable en tiempo real sin
configurar `logging`: cada llamada a `log()` emite una línea `[mm:ss] mensaje`
por stderr. El reloj arranca al importar el módulo (efectivamente, al lanzar
el proceso).

Además del canal por stderr (consumido por la CLI), `log()` reenvía cada
línea a los *callbacks* registrados con `register_callback()`. Esto permite
que otra interfaz (la GUI) consuma el mismo flujo sin duplicar lógica de
observabilidad y sin parsear stderr.
"""

import time
from typing import Callable

import click

_START = time.monotonic()
_callbacks: list[Callable[[str], None]] = []


def register_callback(cb: Callable[[str], None]) -> None:
    """Registra un *callback* que recibirá cada línea ya formateada.

    Se invoca después de emitir por stderr. Las excepciones del *callback*
    se silencian para no afectar al pipeline.
    """
    _callbacks.append(cb)


def unregister_callback(cb: Callable[[str], None]) -> None:
    """Quita un *callback* previamente registrado. No falla si no está."""
    if cb in _callbacks:
        _callbacks.remove(cb)


def log(msg: str) -> None:
    elapsed = time.monotonic() - _START
    mm, ss = divmod(int(elapsed), 60)
    line = f"[{mm:02d}:{ss:02d}] {msg}"
    click.echo(line, err=True)
    for cb in list(_callbacks):
        try:
            cb(line)
        except Exception:
            pass
