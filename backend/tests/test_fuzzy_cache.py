"""Tests for the on-disk securities cache fallback (search/fuzzy module)."""

import asyncio

from app.search import fuzzy


def test_security_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(fuzzy, "SECURITY_CACHE_PATH", tmp_path / "securities_cache.json")
    entries = [{"symbol": "NABIL", "name": "Nabil Bank Limited"}]
    asyncio.run(fuzzy.set_security_cache(entries))
    assert fuzzy.load_securities_cache() == entries


def test_security_cache_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(fuzzy, "SECURITY_CACHE_PATH", tmp_path / "nope.json")
    assert fuzzy.load_securities_cache() == []


def test_security_cache_corrupt_file_is_empty(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("{ not json !!!", encoding="utf-8")
    monkeypatch.setattr(fuzzy, "SECURITY_CACHE_PATH", path)
    assert fuzzy.load_securities_cache() == []


def test_fuzzy_search_exact_symbol_first(monkeypatch):
    monkeypatch.setattr(
        fuzzy, "SECURITY_CACHE",
        [{"symbol": "NABIL", "name": "Nabil Bank"}, {"symbol": "NABILP", "name": "Nabil Bank Promoter"}],
    )
    hits = asyncio.run(fuzzy.fuzzy_search("NABIL"))
    assert hits[0]["symbol"] == "NABIL"
    assert asyncio.run(fuzzy.fuzzy_search("zzz")) == []