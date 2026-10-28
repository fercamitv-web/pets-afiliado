---
name: publicar
description: Compila o site e envia o relatório para o Telegram.
---

# Skill: publicar e reportar

1. Rode `python scripts/build.py`.
2. Confirme que `public/sitemap.xml`, `public/rss.xml` e `public/robots.txt` existem.
3. Envie o relatório semanal com `python scripts/notify.py semanal`
   (ou teste o bot com `python scripts/notify.py`).
4. Se estiver rodando localmente, faça commit e push:

       git add -A && git commit -m "conteudo: $(date +%F)" && git push

Regras:
- Se o build falhar, mostre o erro exato ao usuário e NÃO faça push.
- Nunca faça push de artigo que não passou pela revisão crítica da skill "artigo".
