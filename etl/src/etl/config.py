from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ETLSettings:
    source_database_url: str
    warehouse_database_url: str
    http_port: str


def load_settings() -> ETLSettings:
    source_database_url = os.getenv(
        "DATABASE_URL", "postgresql://equisentinel:equisentinel@localhost:5432/equisentinel"
    )
    return ETLSettings(
        source_database_url=source_database_url,
        warehouse_database_url=os.getenv("WAREHOUSE_DATABASE_URL", source_database_url),
        http_port=os.getenv("ETL_HTTP_PORT", "8083"),
    )
