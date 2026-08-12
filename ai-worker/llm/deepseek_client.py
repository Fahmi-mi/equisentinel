from __future__ import annotations

from langchain_openai import ChatOpenAI

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def build_deepseek_client(api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        timeout=10,
        max_retries=2,
    )
