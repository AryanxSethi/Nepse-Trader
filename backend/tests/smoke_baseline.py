"""Baseline smoke test — exercises every public route through FastAPI TestClient.

Used as the safety net for the production-restructure refactor: after each
refactor phase this script must print ALL ROUTES PASSED.

Requires network for data sources (yonepse/merolagani/sharesansar). For the
network-free pytest suite see ``app/tests`` (Phase 5 of the restructure).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)
results: list[tuple[str, int]] = []


def check(name: str, resp, expect_status: int = 200) -> None:
    results.append((name, resp.status_code))
    assert resp.status_code == expect_status, f"{name}: expected {expect_status}, got {resp.status_code}: {resp.text[:300]}"


# --- reference / search ---
check("companies", client.get("/api/companies"))
check("securities", client.get("/api/securities"))
check("securities?search=NAB", client.get("/api/securities", params={"search": "NAB"}))
check("search", client.get("/api/search", params={"query": "NABIL"}))
check("search empty", client.get("/api/search"))

# --- market ---
check("market/overview", client.get("/api/market/overview"))
check("market/index-history", client.get("/api/market/index-history"))
check("market/live", client.get("/api/market/live"))
check("market/status", client.get("/api/market/status"))

# --- stocks ---
check("stocks/history", client.get("/api/stocks/NABIL/history"))
check("stocks/history range", client.get(
    "/api/stocks/NABIL/history", params={"start": "2026-01-01", "end": "2026-08-08"}))
check("stocks/history bad date", client.get(
    "/api/stocks/NABIL/history", params={"start": "not-a-date"}), expect_status=400)
check("stocks/detail", client.get("/api/stocks/NABIL/detail"))
check("stocks/compare", client.get("/api/stocks/compare", params={"symbols": "NABIL,SCB"}))
check("stocks/compare single", client.get("/api/stocks/compare", params={"symbols": "NABIL"}), expect_status=400)

# --- signals ---
check("signals", client.get("/api/signals"))
check("signals generate", client.post("/api/signals/generate"))

# --- backtest ---
check("backtest", client.post("/api/backtest", params={"symbol": "NABIL", "fast_ma": 20, "slow_ma": 50, "days": 120}))

# --- portfolio (CRUD with cleanup) ---
check("portfolio get", client.get("/api/portfolio"))
r = client.post("/api/portfolio/holdings", params={"symbol": "NABIL", "quantity": 10, "avg_cost": 500, "notes": "smoke"})
assert r.status_code == 200, f"portfolio create failed: {r.text[:300]}"
hold_id = r.json().get("id")
results.append(("portfolio create", 200))
check("portfolio update", client.put(f"/api/portfolio/holdings/{hold_id}", params={"quantity": 12}))
check("portfolio delete", client.delete(f"/api/portfolio/holdings/{hold_id}"))
check("portfolio update 404", client.put("/api/portfolio/holdings/999999", params={"quantity": 1}), expect_status=404)

# --- ipos / brokers / sectors ---
check("ipos", client.get("/api/ipos"))
check("brokers top", client.get("/api/brokers/top"))
check("brokers search", client.get("/api/brokers/search", params={"q": "Nabil"}))
check("sectors", client.get("/api/sectors"))
check("sectors stocks", client.get("/api/sectors/Microfinance/stocks"))
check("sectors unknown", client.get("/api/sectors/NotARealSector/stocks"), expect_status=404)

# --- guide ---
check("guide search", client.get("/api/guide/search", params={"q": "ipo"}))
check("guide brokers", client.get("/api/guide/brokers"))

# --- chat (streaming; small talk should not hit the LLM) ---
with client.stream("POST", "/api/ask", json={"question": "hi", "history": []}) as resp:
    assert resp.status_code == 200, f"ask failed: {resp.status_code}"
    body = "".join(resp.iter_text())
    assert '"type": "done"' in body, f"ask stream missing done event: {body[:300]}"
    results.append(("ask", 200))

# --- health ---
check("health", client.get("/api/health"))

print(f"\n\nALL {len(results)} ROUTES PASSED")
for name, status in results:
    print(f"  ok  {status}  {name}")