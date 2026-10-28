"""scripts/auto_publish.py — Orquestrador de divulgação automática.

Chama todos os canais de distribuição após cada artigo publicado.
Roda sozinho: não precisa de intervenção humana.

Canais:
- Telegram: aviso direto no seu chat (sempre ativo)
- Pinterest: publica pin direto no board (se houver PINTEREST_TOKEN)
- Social Cards: gera páginas /social/<slug>/ para compartilhamento com 1 clique
- Fila social: salva conteúdo pronto para Reddit/Twitter/WhatsApp (copiar-colar opcional)
- IndexNow: avisa Bing/Yandex instantaneamente

Uso:
    python scripts/auto_publish.py <slug_do_artigo>
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import CONTENT_DIR, config, ler_json, separar_frontmatter
import distribute
import social_cards
import indexar


def publicar(slug: str) -> dict:
    """Executa divulgação completa para um artigo."""
    cfg = config()
    arquivo = CONTENT_DIR / f"{slug}.md"
    if not arquivo.exists():
        raise FileNotFoundError(f"Artigo não encontrado: {slug}")

    meta, _ = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
    if not meta.get("titulo"):
        raise ValueError(f"Artigo {slug} sem título no frontmatter")

    print(f"[auto_publish] Iniciando divulgação de: {meta['titulo']}")

    # 1. Distribuição (Telegram + Pinterest + fila social)
    res = distribute.distribuir(meta, cfg)
    print(f"[auto_publish] Distribuição: {res}")

    # 2. Social Cards (páginas de compartilhamento otimizadas)
    try:
        caminho_card = social_cards.gerar_card(meta, cfg)
        print(f"[auto_publish] Card social gerado: {caminho_card}")
        res["social_card"] = caminho_card
    except Exception as e:
        print(f"[auto_publish] Erro no card social: {e}")
        res["social_card"] = None

    # 3. IndexNow (Bing/Yandex)
    try:
        indexar.indexar()
        res["indexnow"] = "enviado"
    except Exception as e:
        print(f"[auto_publish] Erro no IndexNow: {e}")
        res["indexnow"] = None

    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/auto_publish.py <slug>")
        sys.exit(1)
    resultado = publicar(sys.argv[1])
    print("\n=== DIVULGAÇÃO CONCLUÍDA ===")
    for k, v in resultado.items():
        print(f"  {k}: {v}")
