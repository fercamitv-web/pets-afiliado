"""Escuta o Telegram e imprime o seu chat.id assim que voce manda um 'oi' ao bot."""
from __future__ import annotations

import os
import sys
import time

import requests

LIMITE_SEGUNDOS = 120


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return 1

    offset = None
    fim = time.time() + LIMITE_SEGUNDOS
    while time.time() < fim:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=25,
            )
        except requests.RequestException:
            time.sleep(1)
            continue

        dados = r.json()
        if not dados.get("ok"):
            print("", end="")
            return 1

        for upd in dados.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat") or {}
            if chat.get("id") is not None:
                print(chat["id"])
                return 0
        time.sleep(1)
    return 1


if __name__ == "__main__":
    sys.exit(main())
