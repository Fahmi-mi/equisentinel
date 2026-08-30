from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import structlog
from sqlalchemy import Connection, Engine, create_engine

from etl.config import ETLSettings

log = structlog.get_logger()


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


class WarehouseDB:
    def __init__(self, settings: ETLSettings) -> None:
        self._source_engine = make_engine(settings.source_database_url)
        self._warehouse_engine = (
            self._source_engine
            if settings.warehouse_database_url == settings.source_database_url
            else make_engine(settings.warehouse_database_url)
        )
        log.info(
            "warehouse_db_initialized",
            shared_engine=self._warehouse_engine is self._source_engine,
        )

    @property
    def source_engine(self) -> Engine:
        return self._source_engine

    @property
    def warehouse_engine(self) -> Engine:
        return self._warehouse_engine

    @contextmanager
    def source_connection(self) -> Iterator[Connection]:
        with self._source_engine.connect() as conn:
            yield conn

    @contextmanager
    def warehouse_connection(self) -> Iterator[Connection]:
        with self._warehouse_engine.connect() as conn:
            yield conn

    def dispose(self) -> None:
        self._source_engine.dispose()
        if self._warehouse_engine is not self._source_engine:
            self._warehouse_engine.dispose()
        log.info("warehouse_db_disposed")
