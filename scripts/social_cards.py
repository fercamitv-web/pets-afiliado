"""scripts/social_cards.py — Gera páginas HTML otimizadas para compartilhamento.

Cada artigo ganha uma página /social/<slug>/ com:
- Imagem de capa grande (1200x630)
- Título e descrição chamativos
- Botão "Ver preço" direto para o link de afiliado
- Meta tags Open Graph para Facebook/WhatsApp/LinkedIn

Uso:
    python scripts/social_cards.py          # gera todos os cards
    python scripts/social_cards.py --slug <slug>  # gera um específico
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import (CONTENT_DIR, DATA_DIR, PUBLIC_DIR, config, ler_json,
                    separar_frontmatter, slugify)


CSS = """
:root{--bg:#0f1115;--card:#171a21;--txt:#e8eaf0;--mut:#9aa3b2;--acc:#4ade80;--borda:#262b36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:18px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:620px;margin:0 auto;padding:32px 24px;text-align:center}
img.capa{width:100%;border-radius:16px;margin:24px 0;box-shadow:0 8px 24px rgba(0,0,0,.35)}
h1{font-size:28px;line-height:1.35;margin:.4em 0 1em}
p.mut{color:var(--mut);font-size:15px;margin:0 0 24px}
.btn{display:inline-block;background:var(--acc);color:#08110c;text-decoration:none;
font-weight:800;padding:14px 24px;border-radius:10px;font-size:17px;margin:8px 4px}
.btn:hover{filter:brightness(1.15)}
.tags{color:var(--mut);font-size:13px;margin-top:20px}
.tags span{display:inline-block;background:var(--card);border:1px solid var(--borda);
border-radius:6px;padding:4px 10px;margin:2px 4px}
footer{color:var(--mut);font-size:13px;margin-top:32px}
"""

BASE = """<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{titulo}} — Patinha Certa</title>
<meta name="description" content="{{descricao}}">
<meta property="og:type" content="website">
<meta property="og:title" content="{{titulo}}">
<meta property="og:description" content="{{descricao}}">
<meta property="og:image" content="{{imagem}}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>{{css}}</style></head><body>
<div class="wrap">
<img class="capa" src="{{imagem}}" alt="{{titulo}}">
<h1>{{titulo}}</h1>
<p class="mut">{{descricao}}</p>
<a class="btn" href="{{link_amazon}}" target="_blank" rel="sponsored nofollow noopener">Ver preço na Amazon</a>
<a class="btn" style="background:transparent;border:1px solid var(--acc);color:var(--txt)" href="{{link_artigo}}" target="_blank">Ler artigo completo</a>
<div class="tags">{{tags}}</div>
<footer>Patinha Certa · Reviews e comparativos para cães e gatos</footer>
</div></body></html>"""


def _imagem(meta: dict) -> str:
    from hashlib import md5
    from urllib.parse import quote
    prompt = meta.get("capa_prompt") or meta["titulo"]
    semente = int(md5(meta["slug"].encode()).hexdigest()[:8], 16) % 100000
    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt + ", product photography, bright, clean, vertical composition")
        + f"?width=1200&height=630&seed={semente}&nologo=true"
    )


def gerar_card(meta: dict, cfg: dict) -> str:
    """Gera o HTML do card social e retorna o caminho do arquivo."""
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    destino = PUBLIC_DIR / "social" / meta["slug"]
    destino.mkdir(parents=True, exist_ok=True)

    dominio = cfg["site"]["dominio"].rstrip("/")
    link_artigo = f"{dominio}/{meta['slug']}/"
    # Link direto de afiliado Amazon (primeira palavra-chave ou termo genérico)
    palavra = (meta.get("palavras_chave") or ["produto"])[0]
    from urllib.parse import quote
    link_amazon = f"{dominio}/ir/amz-{slugify(palavra)}/"

    tags = "".join(
        f'<span>{t}</span>' for t in (meta.get("palavras_chave") or [])[:5]
    )

    html = (BASE
            .replace("{{titulo}}", meta["titulo"])
            .replace("{{descricao}}", meta.get("descricao", ""))
            .replace("{{imagem}}", _imagem(meta))
            .replace("{{link_artigo}}", link_artigo)
            .replace("{{link_amazon}}", link_amazon)
            .replace("{{tags}}", tags)
            .replace("{{css}}", CSS))

    (destino / "index.html").write_text(html, encoding="utf-8")
    return str(destino / "index.html")


def gerar_todos() -> int:
    cfg = config()
    total = 0
    for arquivo in sorted(CONTENT_DIR.glob("*.md")):
        meta, _ = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
        if not meta.get("titulo"):
            continue
        gerar_card(meta, cfg)
        total += 1
        print(f"[social_cards] {meta['slug']}")
    return total


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="gerar card apenas para este slug")
    args = ap.parse_args()
    cfg = config()
    if args.slug:
        arquivo = CONTENT_DIR / f"{args.slug}.md"
        if not arquivo.exists():
            print(f"Artigo não encontrado: {args.slug}")
            sys.exit(1)
        meta, _ = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
        caminho = gerar_card(meta, cfg)
        print(f"Card gerado: {caminho}")
    else:
        n = gerar_todos()
        print(f"[social_cards] {n} cards gerados.")
