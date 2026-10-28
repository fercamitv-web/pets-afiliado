"""Envia todas as URLs para o IndexNow (Bing/Yandex aceitam na hora, sem custo)."""
from __future__ import annotations

import os

import requests

from common import PUBLIC_DIR, config


def indexar() -> None:
    chave = os.getenv("INDEXNOW_KEY", "").strip()
    if not chave:
        print("[indexnow] INDEXNOW_KEY não definida, pulando.")
        return
    cfg = config()
    dominio = cfg["site"]["dominio"].rstrip("/")
    urls = []
    for p in PUBLIC_DIR.rglob("index.html"):
        rel = p.parent.relative_to(PUBLIC_DIR)
        rel_s = str(rel)
        # não indexamos as páginas de redirecionamento /ir/
        if rel_s == "ir" or rel_s.startswith("ir/") or rel_s.startswith("ir\\"):
            continue
        urls.append(f"{dominio}/" + ("" if rel_s == "." else f"{rel_s.replace(chr(92), '/')}/"))
    r = requests.post("https://api.indexnow.org/indexnow", json={
        "host": dominio.replace("https://", "").replace("http://", ""),
        "key": chave,
        "keyLocation": f"{dominio}/{chave}.txt",
        "urlList": urls[:10000],
    }, timeout=60)
    print(f"[indexnow] {len(urls)} URLs enviadas, status {r.status_code}")


if __name__ == "__main__":
    indexar()
