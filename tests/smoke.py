"""Teste de fumaça do pipeline — roda completo, sem nenhuma chave de API.

Cobre o ciclo Amazon Associados: fases, /ir/, páginas obrigatórias, sitemap.
Uso (a partir da raiz do projeto):
    .venv/Scripts/python.exe tests/smoke.py     (Windows/git-bash)
    .venv/bin/python tests/smoke.py             (Linux/macOS, GitHub Actions)
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import yaml

import amazon
import build
import common
import write

FALHAS = []


def checar(nome, cond, detalhe=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {nome}" + (f"  -> {detalhe}" if not cond and detalhe else ""))
    if not cond:
        FALHAS.append(nome)


# ---------- 1. utilidades ----------
checar("slugify remove acentos/pontuacao",
       common.slugify("Fonte de Água para Gatos!") == "fonte-de-agua-para-gatos")

artigo_path = RAIZ / "content" / "fonte-de-agua-para-gatos.md"
meta, corpo = common.separar_frontmatter(artigo_path.read_text(encoding="utf-8"))
checar("frontmatter parseia titulo", bool(meta.get("titulo")))
checar("frontmatter tem palavra-chave", "fonte de água para gatos" in meta.get("palavras_chave", []))

# esc() precisa produzir entidades de verdade (regressao do bug do no-op)
LT, GT, AMPE = "&" + "lt;", "&" + "gt;", "&" + "amp;"
checar("esc() escapa < > &",
       common.esc("a<b>c&d") == "a" + LT + "b" + GT + "c" + AMPE + "d")

# ---------- 2. links de afiliado (config vazia = busca simples) ----------
checar("amz sem tag vira busca simples",
       common.link_afiliado("amz", "fonte de agua") == "https://www.amazon.com.br/s?k=fonte+de+agua")
checar("ml sem matt_word vira busca simples",
       common.link_afiliado("ml", "bebedouro gatos") == "https://lista.mercadolivre.com.br/bebedouro%20gatos")
checar("shopee sem af_id vira busca simples",
       common.link_afiliado("shopee", "fonte gatos") == "https://shopee.com.br/search?keyword=fonte+gatos")

# ---------- 3. links de afiliado (config preenchida = com rastreio) ----------
config_original = common.config
common.config = lambda: {"afiliados": {"amazon": {"tag": "minhatag-20"},
                                       "ml_matt_word": "camp1",
                                       "shopee_af_id": "af123"}}
checar("amz com tag (bloco aninhado)", "tag=minhatag-20" in common.link_afiliado("amz", "fonte"))
checar("ml com matt_word", "matt_word=camp1" in common.link_afiliado("ml", "bebedouro"))
checar("shopee com af_id", "af_id=af123" in common.link_afiliado("shopee", "fonte"))
common.config = config_original

# ---------- 4. shortcodes -> links no markdown ----------
saida = common.aplicar_afiliados(
    "veja [fonte](amz:fonte de agua), [bebedouro](ml:bebedouro gatos) e [fonte](shopee:fonte pet)")
checar("shortcode amz expandido", "](https://www.amazon.com.br/s?k=" in saida)
checar("shortcode ml expandido", "](https://lista.mercadolivre.com.br/" in saida)
checar("shortcode shopee expandido", "](https://shopee.com.br/search?keyword=" in saida)
checar("nenhum shortcode residual", "amz:" not in saida and "ml:" not in saida and "shopee:" not in saida)

# ---------- 5. capa pelo caminho real do pipeline (idempotente) ----------
meta_final = dict(meta)
meta_final.pop("capa_prompt", None)
if not meta_final.get("capa"):
    meta_final["capa"] = write._capa("realistic photo of pet water fountain", meta["slug"])
    cabecalho = yaml.safe_dump(meta_final, allow_unicode=True, sort_keys=False).strip()
    artigo_path.write_text(f"---\n{cabecalho}\n---\n\n{corpo}\n", encoding="utf-8")
capa = meta_final.get("capa", "")
checar("capa pollinations gerada", capa.startswith("https://image.pollinations.ai/prompt/"))

# ---------- 6. build de verdade ----------
n = build.compilar()
checar("build compilou 1 artigo", n == 1, f"compilou {n}")

pub = RAIZ / "public"
checar("index.html existe", (pub / "index.html").exists())
checar("sitemap.xml existe", (pub / "sitemap.xml").exists())
checar("rss.xml existe", (pub / "rss.xml").exists())
checar("robots.txt existe", (pub / "robots.txt").exists())

dominio = common.config()["site"]["dominio"].rstrip("/")
home = (pub / "index.html").read_text(encoding="utf-8")
checar("canonical da home sem // (bug corrigido)",
       f'href="{dominio}/"' in home and f'href="{dominio}//"' not in home)
checar("home tem nav para /sobre/", 'href="/sobre/"' in home)

art = (pub / meta["slug"] / "index.html").read_text(encoding="utf-8")
checar("artigo usa links /ir/", 'href="/ir/amz-' in art)
checar("artigo tem rel sponsored nofollow noopener", 'rel="sponsored nofollow noopener"' in art)
checar("artigo NAO expoe link de afiliado direto", "https://www.amazon.com.br/s?k=" not in art)
checar("artigo tem disclosure Amazon", "Associado da Amazon" in art)
checar("artigo tem tabela comparativa", "<table" in art)
checar("artigo tem capa pollinations", "image.pollinations.ai" in art)
checar("artigo tem json-ld", "application/ld" + "+json" in art)

# ---------- 7. redirecionamentos /ir/ ----------
ir = pub / "ir"
paginas_ir = list(ir.glob("*/index.html")) if ir.exists() else []
checar("paginas /ir/ geradas", len(paginas_ir) >= 3, f"{len(paginas_ir)} paginas")
conteudo_ir = [p.read_text(encoding="utf-8") for p in paginas_ir]
checar("/ir/ redireciona pra Amazon", any("www.amazon.com.br/s?k=" in c for c in conteudo_ir))
checar("/ir/ redireciona pra Mercado Livre", any("lista.mercadolivre.com.br" in c for c in conteudo_ir))
checar("/ir/ redireciona pra Shopee", any("shopee.com.br/search" in c for c in conteudo_ir))
checar("/ir/ e noindex", all('name="robots" content="noindex,follow"' in c for c in conteudo_ir))
checar("/ir/ espera 1s (beacon do Cloudflare conta o clique)",
       all('content="1;url=' in c for c in conteudo_ir))

# ---------- 8. páginas obrigatórias de aprovação ----------
for slug_pag, trecho in (("sobre", "revisado por humano"),
                         ("privacidade", "Cloudflare Web Analytics"),
                         ("contato", "contato@patinhacerta.pages.dev")):
    cam = pub / slug_pag / "index.html"
    ok = cam.exists() and trecho in cam.read_text(encoding="utf-8")
    checar(f"pagina /{slug_pag}/ existe e tem conteudo", ok)

sitemap = (pub / "sitemap.xml").read_text(encoding="utf-8")
checar("sitemap lista o artigo", f"{dominio}/{meta['slug']}/" in sitemap)
checar("sitemap lista paginas obrigatorias",
       all(f"{dominio}/{s}/" in sitemap for s in ("sobre", "privacidade", "contato")))
checar("sitemap NAO lista /ir/", "/ir/" not in sitemap)
checar("robots bloqueia /ir/", "Disallow: /ir/" in (pub / "robots.txt").read_text(encoding="utf-8"))

# ---------- 9. ciclo Amazon Associados ----------
checar("fase inicial = pre", amazon.fase() == "pre")
checar("contagem de artigos = 1", amazon.total_artigos() == 1)
checar("status menciona fase pre", "fase=pre" in amazon.status_texto())
checar("sem data/amazon.json antes da aprovacao", not (RAIZ / "data" / "amazon.json").exists())

# ---------- 10. estado dos dados ----------
pautas = common.ler_json(RAIZ / "data" / "pautas.json", [])
checar("fila com 8 pautas", len(pautas) == 8, f"tem {len(pautas)}")
slugs = [p.get("slug") for p in pautas]
checar("nenhuma pauta duplicada", len(slugs) == len(set(slugs)))
publicados = common.ler_json(RAIZ / "data" / "publicados.json", [])
checar("artigo semente no historico", any(p["slug"] == meta["slug"] for p in publicados))

print()
if FALHAS:
    print(f"RESULTADO: {len(FALHAS)} FALHA(S): {FALHAS}")
    sys.exit(1)
print("RESULTADO: todos os testes passaram.")
