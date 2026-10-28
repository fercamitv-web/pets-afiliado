"""Suite de testes do sistema. Rode com: pytest tests -q"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import amazon  # noqa: E402
import build  # noqa: E402
import common  # noqa: E402

CONFIG = """
site:
  nome: "Teste Pets"
  dominio: "https://teste.pages.dev"
  descricao: "desc de teste"
  contato_email: "a@b.com"
  cloudflare_token: ""
nicho: "pets"
artigos_por_dia: 1
imagens: "nenhum"
rastrear_cliques: true
afiliados:
  amazon:
    tag: ""
    meta_vendas: 3
    prazo_dias: 180
    artigos_minimos: 2
  disclosure: "disclosure de teste"
"""

ARTIGO = """---
titulo: "Melhor cama para cachorro"
slug: "melhor-cama-cachorro"
descricao: "Comparativo das melhores camas para cachorro."
data: "2026-10-01"
tipo: "comparativo"
capa: ""
palavras_chave: [cama, cachorro]
produtos:
  - nome: "Cama ortopedica G"
    termo: "cama ortopedica cachorro"
---

## Resumo

Veja a [melhor opcao](amz:cama ortopedica cachorro) e a [opcao barata](shopee:cama cachorro).

| Produto | Nota |
|---|---|
| A | 9 |
"""


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    for modulo in (common, amazon, build):
        monkeypatch.setattr(modulo, "telegram", lambda *a, **k: True, raising=False)


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    (tmp_path / "content").mkdir()
    (tmp_path / "data").mkdir()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")

    monkeypatch.setattr(common, "CONFIG_PATH", cfg)
    monkeypatch.setattr(common, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(common, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(common, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(build, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(build, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(amazon, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(amazon, "ESTADO", tmp_path / "data" / "amazon.json")
    common.config.cache_clear()
    yield tmp_path
    if hasattr(common.config, "cache_clear"):
        common.config.cache_clear()


def _publicar(projeto, texto=ARTIGO):
    (projeto / "content" / "artigo.md").write_text(texto, encoding="utf-8")
    build.compilar()


# ---------- utilitarios ----------

def test_slugify_remove_acento():
    assert common.slugify("Cama Ortopédica para Cachorro!") == "cama-ortopedica-para-cachorro"


def test_frontmatter_separado():
    meta, corpo = common.separar_frontmatter(ARTIGO)
    assert meta["titulo"].startswith("Melhor cama")
    assert corpo.startswith("## Resumo")


def test_frontmatter_ausente():
    meta, corpo = common.separar_frontmatter("# so markdown")
    assert meta == {}


# ---------- links de afiliado ----------

def test_link_amazon_sem_tag(projeto):
    assert common.link_afiliado("amz", "cama cachorro") == \
        "https://www.amazon.com.br/s?k=cama+cachorro"


def test_link_amazon_com_tag(projeto, monkeypatch):
    monkeypatch.setattr(common, "config", lambda: {
        "afiliados": {"amazon": {"tag": "teste-20"}}})
    assert "tag=teste-20" in common.link_afiliado("amz", "cama cachorro")


def test_links_ml_e_shopee():
    assert "mercadolivre" in common.link_afiliado("ml", "racao")
    assert "shopee" in common.link_afiliado("shopee", "racao")


def test_shortcode_convertido(projeto):
    saida = build._converter("[x](amz:cama cachorro)", common.config(), {})
    assert saida == "[x](/ir/amz-cama-cachorro/)"


def test_converter_registra_url_real(projeto):
    mapa = {}
    build._converter("[x](amz:cama cachorro)", common.config(), mapa)
    assert "amazon.com.br" in mapa["amz-cama-cachorro"]


# ---------- build ----------

def test_build_gera_artigo(projeto):
    _publicar(projeto)
    assert (projeto / "public" / "melhor-cama-cachorro" / "index.html").exists()


def test_paginas_obrigatorias_da_amazon(projeto):
    _publicar(projeto)
    for p in ("sobre", "privacidade", "contato"):
        assert (projeto / "public" / p / "index.html").exists(), p


def test_paginas_ir_geradas(projeto):
    _publicar(projeto)
    assert (projeto / "public" / "ir" / "amz-cama-ortopedica-cachorro" / "index.html").exists()


def test_pagina_ir_e_noindex(projeto):
    _publicar(projeto)
    html = (projeto / "public" / "ir" / "amz-cama-ortopedica-cachorro" / "index.html").read_text("utf-8")
    assert "noindex" in html and "amazon.com.br" in html


def test_rel_sponsored_no_link(projeto):
    _publicar(projeto)
    html = (projeto / "public" / "melhor-cama-cachorro" / "index.html").read_text("utf-8")
    assert 'rel="sponsored nofollow' in html


def test_disclosure_presente(projeto):
    _publicar(projeto)
    html = (projeto / "public" / "melhor-cama-cachorro" / "index.html").read_text("utf-8")
    assert "disclosure de teste" in html


def test_cta_aparece_em_comparativo(projeto):
    _publicar(projeto)
    html = (projeto / "public" / "melhor-cama-cachorro" / "index.html").read_text("utf-8")
    assert 'class="btn"' in html


def test_cta_ausente_em_guia(projeto):
    texto = ARTIGO.replace('tipo: "comparativo"', 'tipo: "guia"')
    _publicar(projeto, texto)
    html = (projeto / "public" / "melhor-cama-cachorro" / "index.html").read_text("utf-8")
    assert 'class="btn"' not in html


def test_sitemap_inclui_paginas_e_exclui_ir(projeto):
    _publicar(projeto)
    sitemap = (projeto / "public" / "sitemap.xml").read_text("utf-8")
    assert "/privacidade/" in sitemap and "/sobre/" in sitemap
    assert "/ir/" not in sitemap


def test_robots_aponta_sitemap(projeto):
    _publicar(projeto)
    assert "sitemap.xml" in (projeto / "public" / "robots.txt").read_text("utf-8")


def test_jsonld_presente(projeto):
    _publicar(projeto)
    html = (projeto / "public" / "melhor-cama-cachorro" / "index.html").read_text("utf-8")
    assert "application/ld+json" in html and "schema.org" in html


def test_indexnow_key_file(projeto, monkeypatch):
    monkeypatch.setenv("INDEXNOW_KEY", "abc123")
    _publicar(projeto)
    assert (projeto / "public" / "abc123.txt").read_text("utf-8") == "abc123"


# ---------- ciclo amazon ----------

def test_fase_pre_sem_tag(projeto):
    assert amazon.fase() == "pre"


def test_gatilho_ao_atingir_minimo(projeto):
    (projeto / "content" / "a.md").write_text("---\ntitulo: A\n---\n", encoding="utf-8")
    (projeto / "content" / "b.md").write_text("---\ntitulo: B\n---\n", encoding="utf-8")
    amazon.checar()
    assert amazon.estado()["gatilho_enviado"] is True


def test_fase_corrida_com_tag(projeto, monkeypatch):
    monkeypatch.setattr(amazon, "config", lambda: {
        "afiliados": {"amazon": {"tag": "t-20", "meta_vendas": 3, "prazo_dias": 180}}})
    amazon.salvar({"aprovado_em": "2026-10-01", "vendas": 0, "avisos": []})
    assert amazon.fase() == "corrida"


def test_fase_ok_ao_bater_meta(projeto):
    amazon.salvar({"aprovado_em": "2026-10-01", "vendas": 3, "avisos": []})
    assert amazon.fase() == "ok"


def test_dias_restantes_diminuem(projeto):
    amazon.salvar({"aprovado_em": "2026-10-01", "vendas": 0, "avisos": []})
    assert 0 < amazon.dias_restantes() <= 180


def test_status_texto_contem_fase(projeto):
    assert "fase=" in amazon.status_texto()
