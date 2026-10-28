"""Avisos no Telegram."""
from __future__ import annotations

import sys

from common import DATA_DIR, config, esc, ler_json, telegram


def publicado(meta: dict) -> None:
    cfg = config()
    url = f"{cfg['site']['dominio'].rstrip('/')}/{meta['slug']}/"
    telegram(
        f"<b>Novo artigo no ar</b>\n{esc(meta['titulo'])}\n{url}\n\n"
        f"Fila restante: {len(ler_json(DATA_DIR / 'pautas.json', []))}"
    )


def relatorio_semanal() -> None:
    publicados = ler_json(DATA_DIR / "publicados.json", [])
    fila = ler_json(DATA_DIR / "pautas.json", [])
    ultimos = publicados[-7:]
    linhas = "\n".join(f"· {esc(p['titulo'])}" for p in ultimos) or "nenhum"
    telegram(
        f"<b>Relatório semanal</b>\nTotal publicado: {len(publicados)}\n"
        f"Na fila: {len(fila)}\n\nÚltimos 7:\n{linhas}\n\n"
        f"Abra o Search Console e veja quais páginas estão sendo indexadas."
    )


def aviso(texto: str) -> None:
    telegram(f"<b>Agente</b>\n{esc(texto)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "semanal":
        relatorio_semanal()
    else:
        aviso("Teste do bot: se você está lendo isso no Telegram, está tudo certo.")
