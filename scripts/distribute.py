"""scripts/distribute.py - pin do Pinterest + digest no Telegram."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
from urllib.parse import quote

import requests

from common import DATA_DIR, config, esc, ler_json, salvar_json, telegram

PINS = DATA_DIR / "pins.json"


def _imagem(prompt: str, slug: str) -> str:
    semente = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16) % 100000
    return ("https://image.pollinations.ai/prompt/"
            + quote(prompt + ", vertical composition, bright, clean")
            + f"?width=1000&height=1500&seed={semente}&nologo=true")


def _legenda(meta: dict) -> str:
    tags = " ".join("#" + t.replace(" ", "") for t in (meta.get("palavras_chave") or [])[:4])
    return f"{meta['titulo']}\n\n{meta.get('descricao', '')}\n\n{tags}"


def enviar(meta: dict) -> None:
    cfg = config()
    url = f"{cfg['site']['dominio'].rstrip('/')}/{meta['slug']}/"
    imagem = _imagem(meta.get("capa_prompt") or meta["titulo"], meta["slug"])
    telegram(
        f"<b>Pin pronto</b>\n<a href=\"{imagem}\">imagem 1000x1500</a>\n\n"
        f"<b>Legenda</b>\n{esc(_legenda(meta))}\n\n<b>Link</b>\n{url}"
    )
    pins = ler_json(PINS, [])
    pins.append({"slug": meta["slug"], "url": url, "imagem": imagem,
                 "legenda": _legenda(meta), "data": dt.date.today().isoformat(),
                 "postado": False})
    salvar_json(PINS, pins)


def publicar_no_pinterest(limite: int = 3) -> None:
    """Publica direto no board. Precisa de PINTEREST_TOKEN e PINTEREST_BOARD_ID."""
    token = os.getenv("PINTEREST_TOKEN", "").strip()
    board = os.getenv("PINTEREST_BOARD_ID", "").strip()
    if not token or not board:
        print("[pinterest] sem token, pins ficam so no Telegram.")
        return
    pins = ler_json(PINS, [])
    pendentes = [p for p in pins if not p.get("postado")][:limite]
    for p in pendentes:
        r = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"board_id": board, "link": p["url"],
                  "title": p["legenda"].splitlines()[0][:100],
                  "description": p["legenda"][:500],
                  "media_source": {"source_type": "image_url", "url": p["imagem"]}},
            timeout=60,
        )
        if r.status_code in (200, 201):
            p["postado"] = True
            print(f"[pinterest] publicado: {p['slug']}")
        else:
            print("[pinterest]", r.status_code, r.text[:200])
    salvar_json(PINS, pins)


if __name__ == "__main__":
    publicar_no_pinterest()
