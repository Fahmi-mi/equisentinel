from __future__ import annotations

from datetime import datetime

import pandas as pd
import structlog

log = structlog.get_logger()

EXTERNAL_COLUMNS = ["ticker", "open", "high", "low", "close", "volume", "timestamp"]


def fetch_external_history(
    ticker: str,
    start: datetime,
    end: datetime,
    source: str | None = None,
) -> pd.DataFrame:
    log.info("external_history_not_configured", ticker=ticker, source=source)
    return pd.DataFrame(columns=EXTERNAL_COLUMNS)
