"""Cliente para qualquer API compatível com OpenAI (OpenRouter por padrão)."""
from __future__ import annotations

import os
import time

import requests

BASE = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
CHAVE = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")


def _modelo() -> str:
    if os.getenv("LLM_MODEL"):
        return os.environ["LLM_MODEL"]
    from common import config
    return config().get("modelo", {}).get("nome", "deepseek/deepseek-chat-v3-0324:free")


def chat(sistema: str, usuario: str, temperatura: float = 0.7, max_tokens: int = 6000) -> str:
    if not CHAVE:
        raise SystemExit("Defina LLM_API_KEY (ou OPENROUTER_API_KEY).")
    payload = {
        "model": _modelo(),
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        "temperature": temperatura,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {CHAVE}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "agente-afiliado",
    }
    erro = ""
    for tentativa in range(4):
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=headers, json=payload, timeout=240)
        except requests.RequestException as e:
            erro = str(e)
        else:
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            erro = f"{r.status_code} {r.text[:400]}"
        time.sleep(2 ** tentativa * 3)
    raise RuntimeError(f"LLM falhou após 4 tentativas: {erro}")
