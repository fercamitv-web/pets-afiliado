# Patinha Certa — motor de conteúdo com afiliados

Site estático gerado por agente (Hermes). Custo de infraestrutura: **R$ 0**.

**Status (2026-10-27):** repositório montado e testado localmente. Artigo #1 no ar
(`content/fonte-de-agua-para-gatos.md`, escrito como gabarito de qualidade) e fila
de 8 pautas semeada. Falta: as contas/keys do checklist abaixo — nenhuma existe ainda.

## Como funciona

1. GitHub Actions roda **seg/qua/sex às 06h (Brasília)**.
2. O agente tira a pauta do topo da fila, escreve o artigo via LLM grátis, compila o site e avisa no Telegram.
3. O push dispara o deploy no Cloudflare Pages.
4. Ritmo: 3 artigos/semana — calibrado para 2–3h/semana de revisão humana.
   **Todo artigo é revisado antes do push.** Conteúdo IA em escala sem revisão é o que o Google penaliza.

## Checklist de setup (~15–20 min, na ordem)

### 1. Chave de LLM grátis (2 min)
1. Crie conta em https://openrouter.ai e gere uma API key.
2. Confirme o slug do modelo em https://openrouter.ai/models (terminado em `:free`).
   Padrão já configurado: `deepseek/deepseek-chat-v3-0324:free`.
3. Limite da conta grátis: 50 chamadas/dia (1 artigo usa 2–4). Sobe para 1.000/dia com US$ 10 de crédito único.

### 2. Bot do Telegram (3 min)
1. Fale com @BotFather → `/newbot` → copie o token.
2. Mande um "oi" para o seu bot no Telegram.
3. Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` e copie o `chat.id`.

### 3. GitHub (5 min)
1. Crie um repositório **público** (Actions é grátis; em privado são 2.000 min/mês — também cabe).
2. Em **Settings > Secrets and variables > Actions**:
   - Secrets: `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `INDEXNOW_KEY`
     (gere a chave com `openssl rand -hex 16` — IndexNow aceita qualquer hex de 8-128 chars)
   - Variable: `LLM_MODEL` com o slug do modelo
3. Suba este repositório:
   ```
   git remote add origin https://github.com/SEUUSUARIO/pets-afiliado.git
   git push -u origin main
   ```

### 4. Cloudflare Pages (5 min)
1. Cloudflare Dashboard > Workers & Pages > Create > Pages > Connect to Git.
2. Build command: `exit 0` · Build output directory: `public`.
3. Após o primeiro deploy, copie a URL e atualize `dominio` em `config.yaml`.

### 5. Testar
Actions > Rodada de conteúdo > **Run workflow**. Se tudo certo, o Telegram avisa do artigo novo.

### 6. Amazon Associados — ciclo automatizado (Mês 2–3, NÃO agora)
Regra oficial: **180 dias para 3 vendas qualificadas após a inscrição**, senão a conta
é encerrada. O pipeline cuida da sequência inteira:

- Ao chegar em **20 artigos**, o agente manda o checklist de inscrição no Telegram
  (as páginas obrigatórias /sobre, /privacidade e /contato já são geradas pelo build).
- Você se inscreve, roda `python scripts/amazon.py --aprovado` e cola a tag em
  `config.yaml` (`afiliados.amazon.tag`) — o rebuild aplica a tag a TODOS os artigos
  antigos de uma vez, e `python scripts/indexar.py` pede recrawl imediato.
- O agente avisa em 60/30/15/7/3 dias; você registra cada venda com `--venda`.
- Em paralelo, links de afiliado passam por `/ir/` (com `rel="sponsored"`) para o
  Cloudflare Web Analytics contar cliques por artigo — configure `cloudflare_token`
  no config quando criar o site lá.

Status do ciclo: `python scripts/amazon.py --status`.
Depois repita o fluxo para Mercado Livre (`ml_matt_word`) e Shopee (`shopee_af_id`).

## Rodar localmente (Windows / git-bash)

    cd ~/pets-afiliado
    .venv/Scripts/python.exe scripts/build.py          # compila o site em public/
    LLM_API_KEY=sk-... .venv/Scripts/python.exe scripts/run.py --artigos 1

Sem `LLM_API_KEY`, o pipeline usa a fila semeada e falha graciosamente na pesquisa nova.
Para testar o Telegram: `.venv/Scripts/python.exe scripts/notify.py`.

## Expectativa honesta de dinheiro

Comissão média ~5%, CTR ~4%, conversão ~6%, ticket ~R$ 130 → **~R$ 0,016 por visita**.
Ou seja: 5.000 visitas/mês ≈ R$ 78; R$ 500/mês exige ~32 mil visitas/mês.
Os primeiros 4–6 meses são para construir tráfego. Quem promete R$ 3.000 no primeiro
mês está vendendo curso.

## Rotina semanal (2–3h)

1. Seg/qua/sex: revisar o artigo que o agente escreveu (skill "artigo" tem o checklist).
2. Sexta: olhar Search Console + `python scripts/notify.py semanal` para o relatório.
3. Fila abaixo de 3 pautas: `python scripts/research.py`.

## Trocar de nicho ou ritmo

- Nicho: edite `nicho`, `site` e `afiliados` em `config.yaml`. Nada mais muda.
- Ritmo: mude o cron em `.github/workflows/daily.yml` (ex.: `0 9 * * *` para diário).
