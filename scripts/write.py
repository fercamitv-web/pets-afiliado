"""Escreve um artigo completo a partir de uma pauta."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from urllib.parse import quote

import yaml

from common import (CONTENT_DIR, DATA_DIR, config, ler_json, salvar_json,
                    separar_frontmatter, slugify)
from llm import chat

SISTEMA = """Você é redator SEO sênior, escreve em português do Brasil, tom direto e útil.
Regras:
- Nada de enrolação, nada de "no mundo de hoje".
- Frases curtas. Parágrafos de 2 a 4 linhas.
- Use H2 e H3. Use listas e uma tabela comparativa em markdown.
- Nunca invente números exatos de forma absoluta: use "na faixa de", "costuma ficar entre".
- Para links de produtos use os atalhos: [texto](amz:termo de busca), [texto](ml:termo), [texto](shopee:termo).
  O "termo de busca" deve ser o nome do produto como alguém digitaria no site.
- Termine com um bloco "Perguntas frequentes" com 5 perguntas e respostas curtas.
Responda em markdown puro, começando e terminando o frontmatter com três hífens."""


def _limpar(t: str) -> str:
    t = t.strip()
    t = re.sub(r"^```(?:markdown|md)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _capa(prompt: str, slug: str) -> str:
    cfg = config()
    modo = cfg.get("imagens", "nenhum")
    if modo == "pollinations":
        semente = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16) % 100000
        return (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
                f"?width=1200&height=630&seed={semente}&nologo=true")
    if modo == "loremflickr":
        termo = prompt.split()[0]
        return f"https://loremflickr.com/1200/630/{quote(termo)}"
    return ""


def gerar_artigo(pauta: dict) -> tuple:
    cfg = config()
    hoje = dt.date.today().isoformat()
    produtos = ", ".join(pauta.get("produtos") or []) or "os principais do nicho"

    prompt = f"""Escreva um artigo completo.

Nicho do site: {cfg['nicho']}
Título: {pauta['titulo']}
Palavra-chave principal: {pauta['palavra_chave']}
Tipo: {pauta.get('tipo', 'guia')}
Ângulo: {pauta.get('angulo', '')}
Produtos para citar: {produtos}

Extensão: 1400 a 1800 palavras.
Estrutura sugerida: introdução curta com a resposta, "Resumo rápido" em bullets,
"Como escolher" em H2, comparação dos produtos em H2 com H3 por produto e tabela,
"Erros comuns", "Vale a pena?", "Perguntas frequentes".

Frontmatter obrigatório (exatamente estas chaves):
---
titulo: "{pauta['titulo']}"
descricao: meta description de até 155 caracteres
palavras_chave: [termo1, termo2, termo3, termo4]
capa_prompt: prompt curto em inglês para gerar a imagem de capa
---

Depois do frontmatter, o corpo do artigo em markdown."""

    bruto = _limpar(chat(SISTEMA, prompt, temperatura=0.75, max_tokens=7000))
    meta, corpo = separar_frontmatter(bruto)

    slug = pauta.get("slug") or slugify(pauta["titulo"])
    meta.update({
        "titulo": meta.get("titulo") or pauta["titulo"],
        "slug": slug,
        "data": hoje,
        "tipo": pauta.get("tipo", "guia"),
        "capa": _capa(meta.get("capa_prompt") or f"realistic photo of {pauta['palavra_chave']}", slug),
        "descricao": (meta.get("descricao") or "")[:158],
        "palavras_chave": meta.get("palavras_chave") or [pauta["palavra_chave"]],
    })
    meta.pop("capa_prompt", None)
    meta["produtos"] = [{"nome": p, "termo": p} for p in (pauta.get("produtos") or [])]

    cabecalho = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    caminho = CONTENT_DIR / f"{slug}.md"
    caminho.write_text(f"---\n{cabecalho}\n---\n\n{corpo}\n", encoding="utf-8")

    publicados = ler_json(DATA_DIR / "publicados.json", [])
    publicados.append({"slug": slug, "titulo": meta["titulo"], "data": hoje,
                       "palavra_chave": pauta.get("palavra_chave", "")})
    salvar_json(DATA_DIR / "publicados.json", publicados)

    print(f"[write] artigo salvo: {caminho.name}")
    return caminho, meta
