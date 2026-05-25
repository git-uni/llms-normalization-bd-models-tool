"""Log mínimo a stderr con timestamp relativo desde el arranque.

Pensado para que una corrida del CLI sea observable en tiempo real sin
configurar `logging`: cada llamada a `log()` emite una línea `[mm:ss] mensaje`
por stderr. El reloj arranca al importar el módulo (efectivamente, al lanzar
el proceso).
"""

import time

import click

_START = time.monotonic()


def log(msg: str) -> None:
    elapsed = time.monotonic() - _START
    mm, ss = divmod(int(elapsed), 60)
    click.echo(f"[{mm:02d}:{ss:02d}] {msg}", err=True)
