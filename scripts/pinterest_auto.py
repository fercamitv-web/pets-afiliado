"""scripts/pinterest_auto.py — Publicação automática no Pinterest.

Requer:
- PINTEREST_TOKEN (access token da API do Pinterest)
- PINTEREST_BOARD_ID (ID do board onde os pins vão ser publicados)

Como obter:
1. Acesse https://developers.pinterest.com/
2. Crie um app e gere um Access Token
3. Acesse seu board de pets e copie o ID da URL
4. Adicione os dois valores como Secrets no GitHub Actions (ou .env local)

Uso:
    python scripts/pinterest_auto.py <slug>
"""
from __future__ import annotations

import os
import sys
import requests

from common import CONTENT_DIR, config, ler_json, separar_frontmatter
from distribute import _imagem_vertical, _legenda


def publicar(slug: str) -> bool:
    token = os.getenv("PINTEREST_TOKEN", "").strip()
    board = os.getenv("PINTEREST_BOARD_ID", "").strip()

    if not token or not board:
        print("[pinterest_auto] Token ou Board ID não configurado.")
        print("   Defina PINTEREST_TOKEN e PINTEREST_BOARD_ID como variáveis de ambiente.")
        return False

    arquivo = CONTENT_DIR / f"{slug}.md"
    if not arquivo.exists():
        print(f"[pinterest_auto] Artigo não encontrado: {slug}")
        return False

    meta, _ = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
    cfg = config()
    dominio = cfg["site"]["dominio"].rstrip("/")
    url_artigo = f"{dominio}/{meta['slug']}/"

    imagem = _imagem_vertical(meta)
    legenda = _legenda(meta)[:500]

    try:
        r = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "board_id": board,
                "link": url_artigo,
                "title": meta["titulo"][:100],
                "description": legenda,
                "media_source": {"source_type": "image_url", "url": imagem},
            },
            timeout=60,
        )
        if r.status_code in (200, 201):
            print(f"[pinterest_auto] ✓ Pin publicado: {meta['titulo']}")
            return True
        print(f"[pinterest_auto] ✗ Erro {r.status_code}: {r.text[:200]}")
        return False
    except requests.RequestException as e:
        print(f"[pinterest_auto] ✗ Erro de rede: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/pinterest_auto.py <slug>")
        sys.exit(1)
    sucesso = publicar(sys.argv[1])
    sys.exit(0 if sucesso else 1)
