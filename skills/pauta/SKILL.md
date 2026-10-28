---
name: pauta
description: Pesquisa e enfileira novas pautas de conteúdo para o site de afiliados.
---

# Skill: gerar pautas

Quando o usuário pedir "mais pautas", "pesquise temas" ou quando a fila estiver abaixo de 3:

1. Rode `python scripts/research.py` a partir da raiz do projeto.
2. Leia `data/pautas.json` e mostre ao usuário as 5 primeiras pautas em bullets curtos.
3. Se o usuário aprovar, responda apenas "fila atualizada".
4. Se o usuário pedir ajuste de nicho, edite `config.yaml` no campo `nicho` antes de rodar.

Regras:
- Nunca duplique pauta já presente em `data/publicados.json` ou na própria fila.
- Prefira temas com intenção de compra (comparativos, "melhor X", "X vale a pena").
- A fila já vem semeada com 8 pautas; a pesquisa só precisa rodar quando ela baixar de 3.
