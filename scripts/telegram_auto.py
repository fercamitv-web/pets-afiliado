"""scripts/telegram_auto.py — Publicação automática no Telegram.

Envia aviso direto no seu chat pessoal após cada artigo publicado.

Requer:
- TELEGRAM_BOT_TOKEN (do @BotFather)
- TELEGRAM_CHAT_ID (seu chat.id)

Uso:
    python scripts/telegram_auto.py <slug>
"""
from __future__ import annotations

import sys

from common import CONTENT_DIR, config, esc, ler_json, separar_frontmatter, telegram


def publicar(slug: str) -> bool:
    token = os_getenv("TELEGRAM_BOT_TOKEN")
    chat = os_getenv("TELEGRAM_CHAT_ID")

    if not token or not chat:
        print("[telegram_auto] Token ou Chat ID não configurado.")
        return False

    arquivo = CONTENT_DIR / f"{slug}.md"
    if not arquivo.exists():
        print(f"[telegram_auto] Artigo não encontrado: {slug}")
        return False

    meta, _ = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
    cfg = config()
    dominio = cfg["site"]["dominio"].rstrip("/")
    url_artigo = f"{dominio}/{meta['slug']}/"

    texto = (
        f"🐾 <b>Novo artigo publicado</b>\n"
        f"{esc(meta['titulo'])}\n\n"
        f"{esc(meta.get('descricao', '')[:200])}\n\n"
        f"🔗 <a href='{url_artigo}'>Ler artigo completo</a>\n\n"
        f"📋 Fila restante: {len(ler_json(CONTENT_DIR.parent / 'data' / 'pautas.json', []))}"
    )

    try:
        ok = telegram(texto)
        if ok:
            print(f"[telegram_auto] ✓ Mensagem enviada: {meta['titulo']}")
        else:
            print("[telegram_auto] ✗ Falha ao enviar mensagem")
        return ok
    except Exception as e:
        print(f"[telegram_auto] ✗ Erro: {e}")
        return False


def os_getenv(chave: str) -> str:
    import os
    return os.getenv(chave, "").strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/telegram_auto.py <slug>")
        sys.exit(1)
    sucesso = publicar(sys.argv[1])
    sys.exit(0 if sucesso else 1)
