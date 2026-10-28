"""Gera novas pautas e enfileira em data/pautas.json."""
from __future__ import annotations

import json

from common import DATA_DIR, config, ler_json, salvar_json, slugify
from llm import chat

SISTEMA = """Você é estrategista de SEO para um site brasileiro de afiliados.
Gera pautas realistas de baixa concorrência, com intenção de compra clara.
Nunca repita pautas já publicadas. Responda SEMPRE com JSON válido."""

MODELO_JSON = """{
  "pautas": [
    {
      "titulo": "título chamativo com a palavra-chave no início",
      "palavra_chave": "termo principal de busca",
      "tipo": "comparativo" | "guia" | "review",
      "angulo": "por que esse artigo é melhor que o resto",
      "produtos": ["produto 1", "produto 2", "produto 3"]
    }
  ]
}"""


def _tom() -> str:
    """Viés editorial conforme a fase do ciclo Amazon Associados."""
    import amazon
    return {
        "pre": "priorize guias amplos e listas que constroem autoridade no nicho",
        "corrida": "priorize COMPARATIVOS e 'melhor X' com intenção de compra imediata",
        "ok": "equilibre comparativos com conteúdo de topo de funil para ampliar o público",
    }[amazon.fase()]


def gerar_pautas(quantidade: int = 8) -> list[dict]:
    cfg = config()
    publicados = {p.get("slug") for p in ler_json(DATA_DIR / "publicados.json", [])}
    fila = ler_json(DATA_DIR / "pautas.json", [])
    ja_existe = {p.get("slug") for p in fila} | publicados

    prompt = f"""Nicho: {cfg['nicho']}
Orientação editorial: {_tom()}
Público: brasileiro, compra pelo celular.
Gere {quantidade} pautas inéditas.

Evite estes temas (já usados): {sorted(ja_existe) or 'nenhum'}

Formato exato:
{MODELO_JSON}"""

    bruto = chat(SISTEMA, prompt, temperatura=0.9, max_tokens=2500)
    bruto = bruto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        print("[research] JSON inválido, abortando esta rodada.")
        return fila

    novas = []
    for p in dados.get("pautas", []):
        titulo = (p.get("titulo") or "").strip()
        if not titulo:
            continue
        slug = slugify(titulo)
        if slug in ja_existe:
            continue
        ja_existe.add(slug)
        p["slug"] = slug
        novas.append(p)

    fila.extend(novas)
    salvar_json(DATA_DIR / "pautas.json", fila)
    print(f"[research] +{len(novas)} pautas na fila.")
    return fila


if __name__ == "__main__":
    gerar_pautas(8)
