"""Ciclo de vida do Amazon Associados: pre -> corrida -> qualificado.

Comandos:
    python scripts/amazon.py --status
    python scripts/amazon.py --aprovado    # marca hoje como data de aprovação
    python scripts/amazon.py --venda       # registra 1 venda
    python scripts/amazon.py --vendas 2    # define o total
"""
from __future__ import annotations

import argparse
import datetime as dt

from common import CONTENT_DIR, DATA_DIR, config, esc, ler_json, salvar_json, telegram

ESTADO = DATA_DIR / "amazon.json"
MARCOS = (60, 30, 15, 7, 3)

CHECKLIST = """1. Acesse https://associados.amazon.com.br e clique em "Cadastre-se"
2. Cole a URL do site e escolha a categoria "Pets"
3. Informe o perfil: site de conteúdo com reviews e comparativos
4. Cadastre o ID de rastreamento (ex.: patinhacerta-20) e use sempre o mesmo
5. Confirme que /sobre, /privacidade e /contato existem no site (o build já gera)
6. Quando aprovado, rode: python scripts/amazon.py --aprovado
7. Cole a tag em config.yaml (afiliados.amazon.tag) e faça push
8. Rode python scripts/indexar.py para recrawl rápido dos artigos antigos"""


def _cfg() -> dict:
    return (config().get("afiliados", {}) or {}).get("amazon", {}) or {}


def estado() -> dict:
    return ler_json(ESTADO, {"aprovado_em": "", "vendas": 0, "avisos": []})


def salvar(e: dict) -> None:
    salvar_json(ESTADO, e)


def fase() -> str:
    cfg, e = _cfg(), estado()
    if e.get("vendas", 0) >= cfg.get("meta_vendas", 3):
        return "ok"
    if cfg.get("tag", "").strip() and e.get("aprovado_em"):
        return "corrida"
    return "pre"


def total_artigos() -> int:
    return len(list(CONTENT_DIR.glob("*.md")))


def dias_restantes() -> int:
    e = estado()
    if not e.get("aprovado_em"):
        return _cfg().get("prazo_dias", 180)
    fim = dt.date.fromisoformat(e["aprovado_em"]) + dt.timedelta(days=_cfg().get("prazo_dias", 180))
    return (fim - dt.date.today()).days


def checar() -> None:
    """Chamado a cada rodada do agente.

    Flags só são marcadas quando o Telegram CONFIRMA o envio — assim nenhum
    aviso (gatilho, marco de prazo, parabéns) se perde quando o bot está
    sem credencial; ele simplesmente tenta de novo na próxima rodada.
    """
    cfg, e = _cfg(), estado()
    f = fase()

    if f == "pre":
        if total_artigos() >= cfg.get("artigos_minimos", 20) and not e.get("gatilho_enviado"):
            if telegram(
                "<b>Hora de pedir aprovação no Amazon Associados</b>\n\n"
                f"Você tem {total_artigos()} artigos publicados e links prontos.\n"
                "Os links só passam a comissionar depois da tag no config.\n\n"
                f"{esc(CHECKLIST)}"
            ):
                e["gatilho_enviado"] = True
                salvar(e)
        return

    if f == "corrida":
        d = dias_restantes()
        if d in MARCOS and d not in e.get("avisos", []):
            if telegram(
                f"<b>Amazon: faltam {d} dias</b>\n\n"
                f"Vendas registradas: {e.get('vendas', 0)}/{cfg.get('meta_vendas', 3)}\n"
                "Confira o painel de Associados e registre com: "
                "<code>python scripts/amazon.py --venda</code>\n\n"
                "Se estiver apertado, priorize os artigos de comparativo "
                "('melhor X', 'qual comprar'), que convertem mais."
            ):
                e.setdefault("avisos", []).append(d)
                salvar(e)
        if d <= 0 and not e.get("expirado_enviado"):
            if telegram("<b>Amazon: prazo estourado</b>\nA conta pode ter sido fechada. "
                        "Faça o cadastro de novo em associados.amazon.com.br e rode --aprovado de novo."):
                e["expirado_enviado"] = True
                salvar(e)
        return

    if f == "ok" and not e.get("parabens_enviado"):
        if telegram("<b>Conta qualificada</b>\n3 vendas batidas em 180 dias. "
                    "Pode reduzir o ritmo de conteúdo comercial e investir em topo de funil."):
            e["parabens_enviado"] = True
            salvar(e)


def status_texto() -> str:
    e = estado()
    return (f"Amazon: fase={fase()} · artigos={total_artigos()} · "
            f"vendas={e.get('vendas', 0)}/{_cfg().get('meta_vendas', 3)} · "
            f"dias_restantes={dias_restantes() if fase() == 'corrida' else '-'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--aprovado", action="store_true")
    ap.add_argument("--venda", action="store_true")
    ap.add_argument("--vendas", type=int)
    args = ap.parse_args()

    e = estado()
    if args.aprovado:
        e["aprovado_em"] = dt.date.today().isoformat()
        e["avisos"] = []
        e.pop("expirado_enviado", None)
        salvar(e)
        telegram(f"<b>Data de aprovação registrada</b>\nContador de "
                 f"{_cfg().get('prazo_dias', 180)} dias iniciado. "
                 "Preencha a tag no config e faça push agora.")
    if args.venda:
        e["vendas"] = e.get("vendas", 0) + 1
        salvar(e)
    if args.vendas is not None:
        e["vendas"] = args.vendas
        salvar(e)

    checar()
    print(status_texto())


if __name__ == "__main__":
    main()
