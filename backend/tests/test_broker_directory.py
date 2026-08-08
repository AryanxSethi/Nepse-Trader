"""Tests for broker-directory transforms: weekly turnover key and ordering."""

from app.guide.broker_directory import get_top_brokers, search_brokers

SAMPLE = [
    {
        "code": "01", "name": "A Broker", "districts": ["Kathmandu"],
        "latest_turnover": 100, "thirty_days_turnover": 900, "address": "",
    },
    {
        "code": "02", "name": "B Broker", "districts": ["Kathmandu"],
        "latest_turnover": 300, "thirty_days_turnover": 300, "address": "",
    },
]


def test_get_top_brokers_weekly_key_and_sorting(monkeypatch):
    monkeypatch.setattr("app.guide.broker_directory._broker_cache", SAMPLE)
    top = get_top_brokers(period="weekly")
    assert len(top) == 2
    assert "weekly_turnover" in top[0]
    # sorted descending by weekly turnover: 900/4.333 > 300/4.333
    assert top[0]["code"] == "01"
    assert top[1]["code"] == "02"
    assert top[0]["weekly_turnover"] >= top[1]["weekly_turnover"]


def test_get_top_brokers_monthly_uses_thirty_days_turnover(monkeypatch):
    monkeypatch.setattr("app.guide.broker_directory._broker_cache", SAMPLE)
    top = get_top_brokers(period="monthly", limit=1)
    assert top[0]["code"] == "01"
    assert "thirty_days_turnover" in top[0]


def test_get_top_brokers_with_missing_keys_never_crashes(monkeypatch):
    monkeypatch.setattr("app.guide.broker_directory._broker_cache", [{"code": "99", "name": "Z"}])
    top = get_top_brokers(period="weekly", limit=5)
    assert top[0]["weekly_turnover"] == 0


def test_search_brokers_matches_name_or_code(monkeypatch):
    monkeypatch.setattr("app.guide.broker_directory._broker_cache", SAMPLE)
    assert [h["code"] for h in search_brokers("a b")] == ["01"]
    assert [h["code"] for h in search_brokers("02")] == ["02"]
    assert search_brokers("") == SAMPLE
    assert search_brokers("zzz") == []