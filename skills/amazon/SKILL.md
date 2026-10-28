---
name: amazon
description: Gerencia o ciclo de vida do programa Amazon Associados, da espera até a qualificação.
---

# Skill: ciclo Amazon Associados

Contexto: só vale pedir aprovação depois de 20 artigos no ar, porque após aprovar
começa um prazo de 180 dias para fazer 3 vendas ou a conta é fechada.

Fases (veja com `python scripts/amazon.py --status`):

- `pre` — tag vazia. O script avisa no Telegram sozinho ao chegar em 20 artigos.
  Antes de o usuário se cadastrar, confirme que /sobre, /privacidade e /contato
  existem em `public/` (o build gera automaticamente — rode `python scripts/build.py`).
- `corrida` — aprovado. Ao usuário preencher a tag:
  1. edite `config.yaml` (`afiliados.amazon.tag`)
  2. rode `python scripts/build.py` e confirme que os redirecionamentos /ir/ agora
     carregam a tag no destino
  3. rode `python scripts/indexar.py` para recrawl rápido dos artigos antigos
  4. `git add -A && git commit -m "amazon: tag ativa" && git push`
  5. rode `python scripts/amazon.py --status` e mostre o contador de dias
- `ok` — 3 vendas batidas. Avise o usuário e sugira conteúdo de topo de funil.

Regras:
- Nunca preencha a tag antes da aprovação.
- Registre cada venda com `--venda` assim que o usuário avisar.
- Avisos de prazo são automáticos em 60/30/15/7/3 dias.
- As flags internas só são marcadas quando o Telegram CONFIRMA o envio — sem
  credencial, o aviso simplesmente repete na próxima checagem, nunca se perde.
