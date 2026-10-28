---
name: artigo
description: Escreve um artigo a partir da pauta do topo da fila e compila o site.
---

# Skill: escrever artigo

Quando o usuário pedir "escreva um artigo", "publique" ou "rode a rodada":

1. Rode `python scripts/run.py --artigos 1`.
2. Depois, abra o markdown gerado em `content/` e faça uma revisão crítica —
   TODOS os artigos passam por revisão humana antes do push (barra de qualidade
   mais alta que "1 a cada 10"; conteúdo IA em escala sem revisão é o que o
   Google penaliza):
   - o título tem a palavra-chave?
   - a meta description tem menos de 155 caracteres?
   - existem pelo menos 4 links de afiliado no corpo?
   - a tabela comparativa está presente?
   - tem algum preço exato inventado? (proibido — use "na faixa de")
3. Se algo faltar, corrija o arquivo diretamente e rode `python scripts/build.py`.
4. Reporte ao usuário: título, link e fila restante.

Regras:
- Nunca invente preços exatos nem especificações de produtos específicos.
- Mantenha o disclosure de afiliado visível (o build injeta automaticamente).
- Só faça commit/push depois da revisão humana.
