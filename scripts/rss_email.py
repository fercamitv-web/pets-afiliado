"""scripts/rss_email.py — Prepara RSS para disparo automático de email (Mailchimp grátis).

Como funciona:
1. Este script gera/atualiza o feed RSS em public/rss.xml (já existe via build.py)
2. Você conecta esse RSS no Mailchimp (plano grátis) ou em outro serviço de email
3. Toda vez que um artigo novo é publicado, o serviço envia email automaticamente para sua lista

Passos para ativar (feito por você, uma única vez):
1. Crie conta grátis no Mailchimp (ou Brevo, etc.)
2. Conecte o RSS: https://seusite.pages.dev/rss.xml
3. Crie uma campanha "RSS-to-Email" semanal
4. Adicione um formulário de inscrição no seu site (opcional)

O script apenas verifica se o RSS está válido.
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import PUBLIC_DIR, config


def verificar_rss() -> bool:
    rss = PUBLIC_DIR / "rss.xml"
    if not rss.exists():
        print("[rss_email] RSS não encontrado em public/rss.xml")
        return False

    conteudo = rss.read_text(encoding="utf-8")
    if "<item>" not in conteudo:
        print("[rss_email] RSS sem itens (sem artigos publicados ainda)")
        return False

    print(f"[rss_email] RSS válido com artigos: {rss}")
    return True


if __name__ == "__main__":
    ok = verificar_rss()
    sys.exit(0 if ok else 1)
