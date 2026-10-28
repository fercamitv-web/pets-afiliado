"""scripts/distribute.py — Distribuição automática de conteúdo após cada artigo.

Canais suportados:
- Telegram (sempre, se houver token/chat_id)
- Pinterest (se houver PINTEREST_TOKEN e PINTEREST_BOARD_ID)
- Arquivo de prontidão para Reddit/Twitter/WhatsApp (sempre, para copiar-colar)

Todos os links ganham parâmetros UTM para rastrear de onde veio cada clique/venda.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

from common import DATA_DIR, config, esc, ler_json, salvar_json, telegram

PINS = DATA_DIR / "pins.json"
SOCIAL = DATA_DIR / "social_queue.json"


def _utm(url: str, fonte: str, meio: str = "social", campanha: str | None = None) -> str:
    """Adiciona parâmetros UTM para rastrear origem do tráfego."""
    params = {"utm_source": fonte, "utm_medium": meio}
    if campanha:
        params["utm_campaign"] = campanha
    separador = "&" if "?" in url else "?"
    return f"{url}{separador}{urlencode(params)}"


def _slug_id(meta: dict) -> str:
    return hashlib.md5(meta["slug"].encode()).hexdigest()[:8]


def _imagem_vertical(meta: dict) -> str:
    """Gera URL de imagem vertical 1000x1500 otimizada para Pinterest/Stories."""
    prompt = meta.get("capa_prompt") or meta["titulo"]
    semente = _slug_id(meta)
    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt + ", vertical composition, bright, clean, product photography")
        + f"?width=1000&height=1500&seed={semente}&nologo=true"
    )


def _legenda(meta: dict) -> str:
    tags = " ".join("#" + t.replace(" ", "") for t in (meta.get("palavras_chave") or [])[:4])
    return f"{meta['titulo']}\n\n{meta.get('descricao', '')}\n\n{tags}"


def _conteudo_social(meta: dict, cfg: dict, url_artigo: str) -> dict:
    """Gera textos prontos para cada rede social."""
    dominio = cfg["site"]["dominio"].rstrip("/")
    palavra = (meta.get("palavras_chave") or ["produto"])[0]
    chave_amazon = f"amz-{hashlib.md5(palavra.encode()).hexdigest()[:8]}"
    link_amazon = _utm(
        f"{dominio}/ir/{chave_amazon}/",
        "pinterest" if meta.get("tipo") in ("comparativo", "review") else "site",
    )
    return {
        "pinterest": {
            "titulo": meta["titulo"][:100],
            "descricao": _legenda(meta)[:500],
            "link": url_artigo,
            "imagem": _imagem_vertical(meta),
            "link_amazon": link_amazon,
        },
        "reddit": {
            "titulo": f"[Review] {meta['titulo']}",
            "corpo": (
                f"Acabei de publicar um guia completo sobre {meta['titulo']}.\n\n"
                f"{meta.get('descricao', '')}\n\n"
                f"Leia aqui: {url_artigo}\n\n"
                "Não sou dono de loja, apenas compartilho o que pesquisei. "
                "Links de afiliado podem gerar comissão sem custo para você."
            ),
            "subreddit": "pets",
        },
        "whatsapp": {
            "mensagem": (
                f"🐾 {meta['titulo']}\n\n"
                f"{meta.get('descricao', '')}\n\n"
                f"Leia completo: {url_artigo}\n\n"
                "#Pets #Cachorro #Gato #CuidadosComPet"
            )
        },
        "twitter": {
            "texto": (
                f"🐾 {meta['titulo']}\n\n"
                f"{meta.get('descricao', '')[:200]}\n\n"
                f"{url_artigo} #Pets #Cachorro #Gato"
            )
        },
    }


def enviar_telegram(meta: dict, cfg: dict, url_artigo: str) -> bool:
    """Envia aviso no Telegram com link direto e imagem."""
    texto = (
        f"<b>🐾 Novo artigo publicado</b>\n"
        f"{esc(meta['titulo'])}\n\n"
        f"{esc(meta.get('descricao', '')[:200])}\n\n"
        f"<a href='{url_artigo}'>Ler artigo completo</a>\n\n"
        f"Fila restante: {len(ler_json(DATA_DIR / 'pautas.json', []))}"
    )
    return telegram(texto)


def publicar_pinterest(meta: dict, conteudo: dict) -> bool:
    """Publica pin diretamente no Pinterest se houver token configurado."""
    token = os.getenv("PINTEREST_TOKEN", "").strip()
    board = os.getenv("PINTEREST_BOARD_ID", "").strip()
    if not token or not board:
        print("[pinterest] sem token/board, pulando publicação direta.")
        return False

    try:
        r = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "board_id": board,
                "link": conteudo["link"],
                "title": conteudo["titulo"],
                "description": conteudo["descricao"],
                "media_source": {"source_type": "image_url", "url": conteudo["imagem"]},
            },
            timeout=60,
        )
        if r.status_code in (200, 201):
            print(f"[pinterest] publicado: {meta['slug']}")
            return True
        print("[pinterest]", r.status_code, r.text[:200])
        return False
    except requests.RequestException as e:
        print("[pinterest] erro de rede:", e)
        return False


def salvar_fila_social(meta: dict, conteudo: dict) -> None:
    """Salva conteúdos prontos para o usuário copiar-colar em redes sociais."""
    fila = ler_json(SOCIAL, [])
    entrada = {
        "slug": meta["slug"],
        "titulo": meta["titulo"],
        "criado_em": dt.date.today().isoformat(),
        "postado": False,
        **conteudo,
    }
    fila.append(entrada)
    salvar_json(SOCIAL, fila)
    print(f"[social] fila atualizada: {len(fila)} itens pendentes")


def distribuir(meta: dict, cfg: dict | None = None) -> dict:
    """Função principal: chama após cada artigo publicado."""
    cfg = cfg or config()
    dominio = cfg["site"]["dominio"].rstrip("/")
    url_artigo = f"{dominio}/{meta['slug']}/"
    conteudo = _conteudo_social(meta, cfg, url_artigo)

    resultados = {"telegram": False, "pinterest": False, "social_salvo": False}

    # 1. Telegram sempre (se houver credencial)
    try:
        resultados["telegram"] = enviar_telegram(meta, cfg, url_artigo)
    except Exception as e:
        print("[distribute] telegram erro:", e)

    # 2. Pinterest direto (se houver token)
    try:
        resultados["pinterest"] = publicar_pinterest(meta, conteudo)
    except Exception as e:
        print("[distribute] pinterest erro:", e)

    # 3. Salva fila para redes sociais manuais
    try:
        salvar_fila_social(meta, conteudo)
        resultados["social_salvo"] = True
    except Exception as e:
        print("[distribute] fila social erro:", e)

    return resultados


def listar_pendentes(limite: int = 10) -> list[dict]:
    """Retorna itens da fila social ainda não postados."""
    fila = ler_json(SOCIAL, [])
    return [p for p in fila if not p.get("postado")][:limite]


def marcar_postado(slug: str) -> None:
    """Marca um item da fila social como postado."""
    fila = ler_json(SOCIAL, [])
    for p in fila:
        if p.get("slug") == slug:
            p["postado"] = True
    salvar_json(SOCIAL, fila)


if __name__ == "__main__":
    # Teste rápido: distribui o artigo mais recente
    import sys
    from common import CONTENT_DIR, separar_frontmatter

    arquivos = sorted(CONTENT_DIR.glob("*.md"))
    if not arquivos:
        print("Nenhum artigo encontrado.")
        sys.exit(0)
    artigo = arquivos[-1]
    meta, _ = separar_frontmatter(artigo.read_text(encoding="utf-8"))
    cfg = config()
    resultado = distribuir(meta, cfg)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
