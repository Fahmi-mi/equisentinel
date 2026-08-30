from __future__ import annotations

from datetime import datetime, timezone

from etl.extract.external_source import EXTERNAL_COLUMNS, fetch_external_history


def test_fetch_external_history_returns_empty_frame_with_standard_columns():
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 2, tzinfo=timezone.utc)

    result = fetch_external_history("BBCA", start, end, source="bei-historical")

    assert result.empty
    assert list(result.columns) == EXTERNAL_COLUMNS
