from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIWorkerSettings:
    nats_url: str
    database_url: str
    redis_url: str
    deepseek_api_key: str
    deepseek_model: str
    http_port: str


def load_settings() -> AIWorkerSettings:
    return AIWorkerSettings(
        nats_url=os.getenv("NATS_URL", "nats://localhost:4222"),
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://equisentinel:equisentinel@localhost:5432/equisentinel"
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        http_port=os.getenv("AI_WORKER_HTTP_PORT", "8081"),
    )
