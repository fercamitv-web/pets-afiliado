# Guia de Recebimento — Programas de Afiliado

Este arquivo explica onde preencher cada ID de rastreamento no `config.yaml` e como receber o dinheiro no seu banco.

## Onde colocar cada ID no `config.yaml`

Edite o arquivo `config.yaml` na raiz do projeto. Procure a seção `afiliados`:

```yaml
afiliados:
  amazon:
    tag: "SUATAG-20"           # Ex: patinhacerta-20
    meta_vendas: 3
    prazo_dias: 180
    artigos_minimos: 20

  ml_matt_word: "SEU_ID_ML"   # Ex: camp12345
  shopee_af_id: "SEU_ID_SH"   # Ex: af_123456

  disclosure: "Como Associado da Amazon, ganhamos comissão por compras qualificadas. Você paga o mesmo preço."
```

### Amazon Associados (Brasil)

1. Acesse https://associados.amazon.com.br e faça login com sua conta da Amazon.
2. Solicite participação no programa.
3. Quando aprovado, no painel acesse: **Ferramentas de Produto > Gerenciamento de IDs de Rastreamento**.
4. Crie um ID de rastreamento (ex: `patinhacerta-20`).
5. No `config.yaml`, preencha `afiliados.amazon.tag` com esse ID.
6. Faça commit e push — todos os artigos antigos passam a usar sua tag automaticamente.

**Regra dos 180 dias:** Após a aprovação, você tem 180 dias para gerar 3 vendas qualificadas. O agente avisa no Telegram em 60/30/15/7/3 dias. Registre cada venda com `python scripts/amazon.py --venda`.

---

### Mercado Livre Afiliados

1. Acesse https://afiliados.mercadolivre.com.br e cadastre-se.
2. Após a aprovação, no painel procure a seção de **IDs de rastreamento** ou **parâmetros**.
3. Copie o seu `matt_word` (algo como `camp12345`).
4. No `config.yaml`, preencha `afiliados.ml_matt_word` com esse valor.

---

### Shopee Afiliados

1. Acesse https://afiliados.shopee.com.br e cadastre-se.
2. Após a aprovação, no painel procure seu **af_id** ou **ID de afiliado**.
3. No `config.yaml`, preencha `afiliados.shopee_af_id` com esse valor.

---

## Como receber o dinheiro no seu banco

### Amazon Associados

| Item | Como funciona |
|---|---|
| **Forma de pagamento** | Transferência bancária (TED) para conta corrente ou poupança em seu nome |
| **Cadastro** | Painel Amazon Associados > Configurações de pagamento > Informações bancárias |
| **Mínimo** | Consulte o painel (geralmente R$ 50–100) |
| **Prazo** | Cerca de 60 dias após o fim do mês da venda |

### Mercado Livre Afiliados

| Item | Como funciona |
|---|---|
| **Forma de pagamento** | Mercado Pago → depois você transfere para sua conta bancária |
| **Cadastro** | Painel Mercado Livre Afiliados > Dados bancários / Mercado Pago |
| **Prazo** | Mensal, após validação das vendas |

### Shopee Afiliados

| Item | Como funciona |
|---|---|
| **Forma de pagamento** | Transferência bancária (TED) |
| **Cadastro** | Painel Shopee Afiliados > Configurações > Método de pagamento |
| **Prazo** | Mensal, após validação |

---

## Obrigações fiscais (Brasil)

- A comissão de afiliado é considerada **prestação de serviço**.
- Quando começar a receber com regularidade, considere abrir um **MEI** (custo baixo, permite nota fiscal se necessário).
- Declare esses ganhos no seu **Imposto de Renda anual** como rendimentos tributáveis de pessoa jurídica.

---

## Checklist rápido

- [ ] Me inscrevi na Amazon Associados após ter ~20 artigos no ar
- [ ] Preenchi `afiliados.amazon.tag` no `config.yaml`
- [ ] Fiz push para o GitHub
- [ ] Cadastrei meus dados bancários no painel de cada programa
- [ ] Registrei cada venda com `python scripts/amazon.py --venda`
- [ ] Abri MEI (quando o dinheiro começar a entrar)

---

## Comandos úteis

```bash
# Ver onde você está no ciclo Amazon
python scripts/amazon.py --status

# Registrar uma venda qualificada
python scripts/amazon.py --venda

# Ver o histórico de vendas
cat data/amazon.json
```
