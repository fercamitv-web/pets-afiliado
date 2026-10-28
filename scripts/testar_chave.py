"""Valida a chave do OpenRouter e devolve um modelo :free que realmente responde."""
from __future__ import annotations

import os
import sys

import requests

BASE = "https://openrouter.ai/api/v1"


def main() -> int:
    chave = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not chave:
        print("", end="")
        return 1

    r = requests.get(f"{BASE}/models", timeout=30)
    if r.status_code != 200:
        return 1

    gratuitos = [m["id"] for m in r.json().get("data", []) if m["id"].endswith(":free")]
    if not gratuitos:
        return 1

    ordem = ("deepseek", "qwen", "llama", "mistral", "gemma", "gemini")
    preferidos = [m for p in ordem for m in gratuitos if p in m.lower()]
    candidatos = preferidos or gratuitos

    for modelo in candidatos[:8]:
        try:
            resp = requests.post(
                f"{BASE}/chat/completions",
                headers={"Authorization": f"Bearer {chave}"},
                json={"model": modelo,
                      "messages": [{"role": "user", "content": "diga ok"}],
                      "max_tokens": 10},
                timeout=90,
            )
        except requests.RequestException:
            continue
        if resp.status_code == 200:
            print(modelo)
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
