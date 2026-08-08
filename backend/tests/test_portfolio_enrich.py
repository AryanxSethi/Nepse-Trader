"""Pure-function tests for portfolio holding enrichment."""

from app.api.routers.portfolio import enrich_holding


BASE_HOLDING = {
    "symbol": "NABIL", "quantity": 10, "avg_cost": 500,
    "notes": "", "created_at": "2026-01-01T00:00:00",
}


def test_enrich_with_live_price():
    enriched = enrich_holding(BASE_HOLDING, {"symbol": "NABIL", "ltp": 600, "name": "Nabil Bank Limited"})
    assert enriched["invested"] == 5000.0
    assert enriched["current_value"] == 6000.0
    assert enriched["pl"] == 1000.0
    assert round(enriched["pl_percent"], 2) == 20.0
    assert enriched["ltp"] == 600
    assert enriched["name"] == "Nabil Bank Limited"


def test_enrich_with_missing_ltp_never_crashes():
    holding = enrich_holding(BASE_HOLDING, {})
    assert holding["ltp"] is None
    assert holding["current_value"] is None
    assert holding["pl"] is None
    assert holding["pl_percent"] is None
    assert holding["invested"] == 5000.0


def test_enrich_with_string_ltp_and_loss():
    holding = enrich_holding(BASE_HOLDING, {"ltp": "450", "name": "Nabil"})
    assert holding["ltp"] == 450.0
    assert holding["current_value"] == 4500.0
    assert holding["pl"] == -500.0
    assert round(holding["pl_percent"], 2) == -10.0


def test_enrich_with_garbage_ltp_never_crashes():
    holding = enrich_holding(BASE_HOLDING, {"ltp": "not-a-number"})
    assert holding["ltp"] is None
    assert holding["current_value"] is None
    assert holding["pl"] is None