"""Orquestrador: pesquisa -> escreve -> compila -> avisa."""
from __future__ import annotations

import argparse

import amazon
import build
import distribute
import indexar
import notify
import research
import write
from common import DATA_DIR, config, ler_json, salvar_json


def main() -> None:
    cfg = config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--artigos", type=int, default=cfg.get("artigos_por_rodada", 1))
    ap.add_argument("--so-pesquisar", action="store_true")
    args = ap.parse_args()

    fila = ler_json(DATA_DIR / "pautas.json", [])
    if len(fila) < max(3, args.artigos):
        try:
            fila = research.gerar_pautas(8)
        except SystemExit as e:
            # sem chave de LLM: segue com a fila que existe
            print(f"[run] pesquisa abortada (sem chave?): {e}")
            fila = ler_json(DATA_DIR / "pautas.json", [])

    if args.so_pesquisar:
        notify.aviso(f"Pautas na fila: {len(fila)}")
        return

    if not fila:
        notify.aviso("Fila vazia e pesquisa não retornou nada. Verifique a chave da API.")
        amazon.checar()
        return

    for _ in range(min(args.artigos, len(fila))):
        pauta = fila.pop(0)
        try:
            _, meta = write.gerar_artigo(pauta)
        except SystemExit as e:
            # ex.: LLM_API_KEY ausente — para limpo, fila preservada em disco
            print(f"[run] rodada abortada: {e}")
            fila.insert(0, pauta)
            salvar_json(DATA_DIR / "pautas.json", fila)
            return
        except Exception as e:
            print(f"[run] falha ao escrever '{pauta.get('titulo')}': {e}")
            fila.insert(0, pauta)
            salvar_json(DATA_DIR / "pautas.json", fila)
            continue
        salvar_json(DATA_DIR / "pautas.json", fila)
        build.compilar()
        notify.publicado(meta)
        distribute.enviar(meta)
        distribute.publicar_no_pinterest(1)

    # pós-rodada: reindexa o site e checa o ciclo do Amazon Associados
    indexar.indexar()
    amazon.checar()


if __name__ == "__main__":
    main()
