"""Utilidades compartilhadas: config, JSON, slugs, afiliados e Telegram."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, quote_plus

import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG_PATH = RAIZ / "config.yaml"
CONTENT_DIR = RAIZ / "content"
DATA_DIR = RAIZ / "data"
PUBLIC_DIR = RAIZ / "public"


@lru_cache(maxsize=1)
def config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return re.sub(r"-{2,}", "-", texto)[:70] or "artigo"


def ler_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return padrao


def salvar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def separar_frontmatter(texto: str):
    linhas = texto.splitlines()
    if not linhas or linhas[0].strip() != "---":
        return {}, texto
    for i in range(1, len(linhas)):
        if linhas[i].strip() == "---":
            bloco = "\n".join(linhas[1:i])
            try:
                meta = yaml.safe_load(bloco) or {}
            except yaml.YAMLError:
                # fallback: envolve valores que contenham ':' em aspas duplas
                corrigido = []
                for ln in bloco.splitlines():
                    if ": " in ln and not ln.strip().startswith("#"):
                        chave, _, valor = ln.partition(": ")
                        if valor and not valor.startswith('"') and not valor.startswith("'"):
                            corrigido.append(f'{chave}: "{valor}"')
                        else:
                            corrigido.append(ln)
                    else:
                        corrigido.append(ln)
                meta = yaml.safe_load("\n".join(corrigido)) or {}
            return meta, "\n".join(linhas[i + 1:]).strip()
    return {}, texto


# ---------- links de afiliado ----------

SHORTCODE = re.compile(r"\[([^\]]+)\]\((amz|amazon|ml|mercadolivre|shopee):\s*([^)]+)\)")


def link_afiliado(rede: str, termo: str) -> str:
    termo = termo.strip()
    q = quote_plus(termo)
    cfg = config().get("afiliados", {}) or {}
    if rede in ("amz", "amazon"):
        tag = ((cfg.get("amazon") or {}).get("tag") or "").strip()
        base = f"https://www.amazon.com.br/s?k={q}"
        return f"{base}&tag={quote_plus(tag)}" if tag else base
    if rede in ("ml", "mercadolivre"):
        url = f"https://lista.mercadolivre.com.br/{quote(termo)}"
        matt = (cfg.get("ml_matt_word") or "").strip()
        # Mercado Livre Afiliados rastreia via parâmetros próprios (matt_word/matt_tool).
        # Enquanto vazio, o link de busca simples não gera comissão.
        return f"{url}?matt_word={quote_plus(matt)}" if matt else url
    if rede == "shopee":
        url = f"https://shopee.com.br/search?keyword={q}"
        af = (cfg.get("shopee_af_id") or "").strip()
        # Shopee Afiliados rastreia via af_id (+utm_content).
        return f"{url}?af_id={quote_plus(af)}&utm_content={quote_plus(af)}" if af else url
    return f"https://www.google.com/search?q={q}"


def aplicar_afiliados(md: str) -> str:
    return SHORTCODE.sub(
        lambda m: f"[{m.group(1)}]({link_afiliado(m.group(2), m.group(3))})", md
    )


# ---------- telegram ----------

def esc(texto: str) -> str:
    return texto.replace("&", "&" + "amp;").replace("<", "&" + "lt;").replace(">", "&" + "gt;")


def telegram(mensagem: str, silencioso: bool = False) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[telegram] sem credenciais, pulando.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_notification": silencioso,
            },
            timeout=30,
        )
    except requests.RequestException as e:
        print("[telegram] falha de rede:", e)
        return False
    if r.status_code != 200:
        print("[telegram] erro:", r.text[:300])
    return r.status_code == 200
