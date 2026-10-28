"""Compila content/*.md em um site estático em public/.

Extras desta versão:
- Links de afiliado passam por /ir/ (redirecionamento com 1s de espera, para o
  beacon do Cloudflare contar o clique) e ganham rel="sponsored nofollow noopener".
- Gera as páginas obrigatórias para aprovação no Amazon Associados
  (/sobre, /privacidade, /contato).
- Gera o arquivo de verificação do IndexNow quando INDEXNOW_KEY está definida.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import shutil

import markdown

from common import (CONTENT_DIR, PUBLIC_DIR, SHORTCODE, config, link_afiliado,
                    separar_frontmatter, slugify)

CSS = """
:root{--bg:#0f1115;--card:#171a21;--txt:#e8eaf0;--mut:#9aa3b2;--acc:#4ade80;--borda:#262b36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:17px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}.wrap{max-width:760px;margin:0 auto;padding:28px 20px}
header.top{border-bottom:1px solid var(--borda);padding:18px 0;margin-bottom:36px;
display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
header.top a{text-decoration:none;font-weight:700;font-size:20px;color:var(--txt)}
nav a{margin-left:14px;font-size:14px;color:var(--mut)}
h1{font-size:34px;line-height:1.25;margin:.2em 0}
h2{font-size:25px;margin-top:2em;border-bottom:1px solid var(--borda);padding-bottom:.3em}
h3{font-size:20px;margin-top:1.6em}
img.capa{width:100%;border-radius:12px;margin:18px 0}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:15px}
th,td{border:1px solid var(--borda);padding:10px;text-align:left}
th{background:var(--card)}
.card{background:var(--card);border:1px solid var(--borda);border-radius:12px;
padding:18px;margin:14px 0}.card h2{margin:0 0 6px;font-size:21px;border:0}
.mut{color:var(--mut);font-size:14px}
.disclosure{background:#1b2430;border-left:3px solid var(--acc);padding:12px 14px;
font-size:14px;color:var(--mut);border-radius:6px;margin:22px 0}
.cta{background:var(--card);border:1px solid var(--acc);border-radius:12px;
padding:16px;margin:22px 0;display:flex;flex-direction:column;gap:10px}
.cta p{margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.btn{display:block;background:var(--acc);color:#08110c;text-decoration:none;
font-weight:700;padding:11px 14px;border-radius:8px;text-align:center}
.btn:hover{filter:brightness(1.1)}
footer{border-top:1px solid var(--borda);margin-top:50px;padding:24px 0;color:var(--mut);font-size:14px}
ul li{margin:.35em 0}
"""

BASE = """<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{titulo}}</title>
<meta name="description" content="{{descricao}}">
<link rel="canonical" href="{{url}}">
<meta property="og:type" content="article"><meta property="og:title" content="{{titulo}}">
<meta property="og:description" content="{{descricao}}">
<meta property="og:url" content="{{url}}">
{{og_imagem}}
<link rel="alternate" type="application/rss+xml" href="/rss.xml" title="{{site}}">
<script type="application/ld+json">{{jsonld}}</script>
{{beacon}}
<style>{{css}}</style></head><body>
<div class="wrap">
<header class="top"><a href="/">{{site}}</a>
<nav><a href="/sobre/">Sobre</a><a href="/privacidade/">Privacidade</a><a href="/contato/">Contato</a></nav>
</header>
{{conteudo}}
<footer>© {{ano}} {{site}} · {{disclosure}} · <a href="/rss.xml">RSS</a></footer>
</div></body></html>"""

# Redirecionamento com 1s de espera: dá tempo ao beacon do Cloudflare disparar
# (com refresh instantâneo, o navegador sai antes de contar o clique).
REDIRECT = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Indo para o parceiro…</title>
<meta name="robots" content="noindex,follow">
<meta http-equiv="refresh" content="1;url={{destino}}">
<script>setTimeout(function(){location.replace({{destino_json}});},700)</script>{{beacon}}</head>
<body><p>Indo para o parceiro… <a rel="nofollow sponsored" href="{{destino}}">clique aqui</a> se não for redirecionado.</p></body></html>"""

HTML_IR = re.compile(r'<a href="(/ir/[^"]+)"')


def _render(meta: dict, corpo_html: str, cfg: dict, estatica: bool = False,
            ir_map: dict | None = None) -> str:
    dominio = cfg["site"]["dominio"].rstrip("/")
    slug = meta.get("slug", "")
    # home: canonical limpo, sem a barra dupla do slug vazio
    url = f"{dominio}/{slug}/" if slug else f"{dominio}/"
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": meta["titulo"], "description": meta.get("descricao", ""),
        "datePublished": meta.get("data", ""), "dateModified": meta.get("data", ""),
        "mainEntityOfPage": url, "image": meta.get("capa", ""),
        "author": {"@type": "Organization", "name": cfg["site"]["nome"]},
        "publisher": {"@type": "Organization", "name": cfg["site"]["nome"]},
    }, ensure_ascii=False)
    capa = f'<img class="capa" src="{meta["capa"]}" alt="{html.escape(meta["titulo"])}">' if meta.get("capa") else ""
    if estatica:
        corpo_final = f"<article>{corpo_html}</article>"
    elif slug:
        corpo_final = (
            f'<article><h1>{html.escape(meta["titulo"])}</h1>'
            f'<p class="mut">{meta.get("data", "")} · leitura de ~7 min</p>{capa}'
            f'<div class="disclosure">{html.escape(cfg["afiliados"]["disclosure"])}</div>'
            f'{_cta(meta, cfg, ir_map or {})}{corpo_html}</article>'
        )
    else:
        corpo_final = corpo_html
    return (BASE
            .replace("{{titulo}}", html.escape(meta["titulo"]))
            .replace("{{descricao}}", html.escape(meta.get("descricao", "")))
            .replace("{{url}}", url)
            .replace("{{og_imagem}}", f'<meta property="og:image" content="{meta["capa"]}">' if meta.get("capa") else "")
            .replace("{{jsonld}}", jsonld)
            .replace("{{css}}", CSS)
            .replace("{{site}}", html.escape(cfg["site"]["nome"]))
            .replace("{{disclosure}}", html.escape(cfg["afiliados"]["disclosure"]))
            .replace("{{beacon}}", cfg.get("_beacon", ""))
            .replace("{{conteudo}}", corpo_final)
            .replace("{{ano}}", str(dt.date.today().year)))


def _cta(meta: dict, cfg: dict, ir_map: dict) -> str:
    """Caixa de ofertas no topo, so para conteudo de intencao de compra."""
    if meta.get("tipo") not in ("comparativo", "review") or not meta.get("produtos"):
        return ""
    botoes = []
    for p in meta["produtos"][:3]:
        termo = p["termo"] if isinstance(p, dict) else p
        nome = p.get("nome", termo) if isinstance(p, dict) else p
        chave = f"amz-{slugify(termo)}"
        ir_map[chave] = link_afiliado("amz", termo)
        href = f"/ir/{chave}/" if cfg.get("rastrear_cliques") else ir_map[chave]
        botoes.append(
            f'<a class="btn" rel="sponsored nofollow noopener" target="_blank" '
            f'href="{href}">Ver preco: {html.escape(nome)}</a>'
        )
    return ('<div class="cta"><p class="mut">Ofertas citadas neste artigo</p>'
            + "".join(botoes) + "</div>")


def _converter(corpo: str, cfg: dict, ir_map: dict) -> str:
    """Troca [texto](amz:termo) pelo link real — ou por /ir/ quando o rastreio está ligado."""
    def troca(m):
        texto, rede, termo = m.group(1), m.group(2), m.group(3).strip()
        real = link_afiliado(rede, termo)
        if not cfg.get("rastrear_cliques", True):
            return f"[{texto}]({real})"
        chave = f"{rede}-{slugify(termo)}"
        ir_map[chave] = real
        return f"[{texto}](/ir/{chave}/)"
    return SHORTCODE.sub(troca, corpo)


def _paginas_estaticas(cfg: dict) -> dict:
    nome = cfg["site"]["nome"]
    dominio = cfg["site"]["dominio"].rstrip("/").replace("https://", "").replace("http://", "")
    email = (cfg["site"].get("contato_email") or "").strip() or f"contato@{dominio}"
    return {
        "sobre": ("Sobre o " + nome, f"""O {nome} publica reviews, comparativos e guias de
compra de produtos para cães e gatos. Cada artigo é produzido com apoio de IA,
revisado por humano e atualizado periodicamente.

Não vendemos produtos: indicamos onde encontrar os melhores itens pelo melhor
preço. Quando você compra por um link nosso, recebemos uma pequena comissão,
sem custo extra para você."""),
        "privacidade": ("Política de Privacidade", f"""Este site não coleta dados pessoais
diretamente. Usamos o Cloudflare Web Analytics (sem cookies) e links de afiliado,
que podem definir cookies próprios do parceiro para atribuição de comissão.

Programas de afiliado: Amazon Associados, Mercado Livre e Shopee. Cada parceiro
tem sua própria política de privacidade.

Contato para dúvidas sobre privacidade: {email}."""),
        "contato": ("Contato", f"""Dúvidas, sugestões de pauta ou pedidos de correção:

**{email}**

Respondemos em até 3 dias úteis."""),
    }


def compilar() -> int:
    cfg = config()
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    PUBLIC_DIR.mkdir(parents=True)

    # beacon do Cloudflare Web Analytics (contagem de cliques nas páginas /ir/)
    token = (cfg["site"].get("cloudflare_token") or "").strip()
    beacon = (f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
              f'data-cf-beacon=\'{{"token": "{token}"}}\'></script>') if token else ""
    cfg = dict(cfg)
    cfg["_beacon"] = beacon

    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])
    ir_map: dict[str, str] = {}
    posts = []

    for arquivo in sorted(CONTENT_DIR.glob("*.md")):
        meta, corpo = separar_frontmatter(arquivo.read_text(encoding="utf-8"))
        if not meta.get("titulo"):
            continue
        meta.setdefault("slug", arquivo.stem)
        md.reset()
        corpo_html = md.convert(_converter(corpo, cfg, ir_map))
        corpo_html = HTML_IR.sub(r'<a rel="sponsored nofollow noopener" target="_blank" href="\1"', corpo_html)
        destino = PUBLIC_DIR / meta["slug"]
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(_render(meta, corpo_html, cfg), encoding="utf-8")
        posts.append(meta)

    posts.sort(key=lambda p: p.get("data", ""), reverse=True)

    # páginas de redirecionamento /ir/ (uma por rede+termo, compartilhada entre artigos)
    for chave, real in ir_map.items():
        pasta = PUBLIC_DIR / "ir" / chave
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "index.html").write_text(
            REDIRECT.replace("{{destino_json}}", json.dumps(real))
                    .replace("{{destino}}", html.escape(real, quote=True))
                    .replace("{{beacon}}", beacon), encoding="utf-8")

    # páginas obrigatórias para aprovação no Amazon Associados
    for slug, (titulo, texto) in _paginas_estaticas(cfg).items():
        pasta = PUBLIC_DIR / slug
        pasta.mkdir(parents=True, exist_ok=True)
        meta = {"titulo": titulo, "descricao": texto[:150].replace("\n", " "),
                "slug": slug, "data": dt.date.today().isoformat()}
        md.reset()
        corpo = f"<h1>{html.escape(titulo)}</h1>\n{md.convert(texto)}"
        (pasta / "index.html").write_text(_render(meta, corpo, cfg, estatica=True, ir_map={}), encoding="utf-8")

    # home
    itens = "".join(
        f'<div class="card"><h2><a href="/{p["slug"]}/">{html.escape(p["titulo"])}</a></h2>'
        f'<p class="mut">{p.get("data","")} · {html.escape(p.get("descricao","")[:120])}</p></div>'
        for p in posts[:40]
    )
    home_meta = {"titulo": cfg["site"]["nome"], "descricao": cfg["site"]["descricao"],
                 "slug": "", "data": dt.date.today().isoformat()}
    (PUBLIC_DIR / "index.html").write_text(
        _render(home_meta, f'<h1>{html.escape(cfg["site"]["descricao"])}</h1>{itens}', cfg, ir_map={}),
        encoding="utf-8")

    dominio = cfg["site"]["dominio"].rstrip("/")
    urls = [f"<url><loc>{dominio}/</loc></url>"]
    urls += [f"<url><loc>{dominio}/{p['slug']}/</loc><lastmod>{p.get('data','')}</lastmod></url>"
             for p in posts]
    urls += [f"<url><loc>{dominio}/{s}/</loc></url>" for s in ("sobre", "privacidade", "contato")]
    (PUBLIC_DIR / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls) + "</urlset>", encoding="utf-8")

    itens_rss = "".join(
        f"<item><title>{html.escape(p['titulo'])}</title>"
        f"<link>{dominio}/{p['slug']}/</link>"
        f"<guid>{dominio}/{p['slug']}/</guid>"
        f"<description>{html.escape(p.get('descricao',''))}</description></item>"
        for p in posts[:30])
    (PUBLIC_DIR / "rss.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f'<title>{html.escape(cfg["site"]["nome"])}</title>'
        f'<link>{dominio}</link><description>{html.escape(cfg["site"]["descricao"])}</description>'
        f'{itens_rss}</channel></rss>', encoding="utf-8")

    (PUBLIC_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /ir/\nSitemap: {dominio}/sitemap.xml\n",
        encoding="utf-8")

    # arquivo de verificação do IndexNow (a chave é pública por design)
    chave_indexnow = os.getenv("INDEXNOW_KEY", "").strip()
    if chave_indexnow:
        (PUBLIC_DIR / f"{chave_indexnow}.txt").write_text(chave_indexnow, encoding="utf-8")

    print(f"[build] {len(posts)} artigos, {len(ir_map)} links de afiliado.")
    return len(posts)


if __name__ == "__main__":
    compilar()
