"""Pure-function tests for live-service index normalization and cache timestamps."""

from datetime import datetime, timezone

from app.services.live import _cache_ts_to_epoch, _normalize_index_name


def test_normalize_keeps_nepse():
    assert _normalize_index_name("NEPSE") == "NEPSE"


def test_normalize_appends_index_suffix():
    assert _normalize_index_name("Sensitive") == "Sensitive Index"


def test_normalize_passes_names_with_index_through():
    assert _normalize_index_name("Sensitive Index") == "Sensitive Index"
    assert _normalize_index_name("Float Index") == "Float Index"
    assert _normalize_index_name("Banking") == "Banking Index"


def test_cache_ts_iso_parses():
    epoch = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    assert _cache_ts_to_epoch("2026-08-08T12:00:00+00:00") == epoch


def test_cache_ts_garbage_is_none():
    assert _cache_ts_to_epoch("not-a-date") is None
    assert _cache_ts_to_epoch("") is None
    assert _cache_ts_to_epoch(None) is None