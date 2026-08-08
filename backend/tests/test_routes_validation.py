"""End-to-end input-validation tests through the ASGI app (no network, no lifespan)."""


def test_ipos_page_bounds(client):
    assert client.get("/api/ipos?page=0").status_code == 400
    assert client.get("/api/ipos?page=2001").status_code == 400
    assert client.get("/api/ipos?per_page=101").status_code == 400


def test_brokers_top_period_rejected(client):
    assert client.get("/api/brokers/top?period=quarterly").status_code == 400
    assert client.get("/api/brokers/top?period=weekly").status_code == 200


def test_unknown_sector_404(client):
    assert client.get("/api/sectors/Not-A-Sector/stocks").status_code == 404
    assert client.get("/api/sectors/Banking/stocks").status_code in (200, 404)


def test_stocks_history_reversed_dates_400(client):
    resp = client.get("/api/stocks/NABIL/history", params={"start": "2025-06-01", "end": "2024-01-01"})
    assert resp.status_code == 400


def test_stocks_compare_requires_two_symbols(client):
    assert client.get("/api/stocks/compare").status_code == 400
    assert client.get("/api/stocks/compare?symbols=NABIL").status_code == 400


def test_stocks_detail_overlong_symbol_400(client):
    assert client.get("/api/stocks/" + "X" * 31 + "/detail").status_code == 400


def test_portfolio_add_validation_query_params(client):
    base = "/api/portfolio/holdings"
    assert client.post(base, params={"symbol": "X", "quantity": 0, "avg_cost": 100}).status_code == 400
    assert client.post(base, params={"symbol": "Y", "quantity": 5, "avg_cost": -10}).status_code == 400
    assert client.post(base, params={"symbol": "Z", "quantity": 5, "avg_cost": 100, "buy_date": "not-a-date"}).status_code == 400
    assert client.post(base, params={"symbol": "Z", "quantity": 5, "avg_cost": 100, "notes": "n" * 2001}).status_code == 400
    assert client.post(base, params={"symbol": "W" * 31, "quantity": 5, "avg_cost": 100}).status_code == 400


def test_search_empty_query_short_circuit(client):
    resp = client.get("/api/search", params={"query": ""})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_guide_search_popular_entries_key(client):
    resp = client.get("/api/guide/search")
    assert resp.status_code == 200
    body = resp.json()
    assert "entries" in body
    assert body["entries"]  # non-empty popular entries


def test_health_check(client):
    assert client.get("/api/health").status_code == 200