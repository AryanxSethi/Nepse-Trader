"""Pure-function tests for backtest parameter validation."""

import pytest
from fastapi import HTTPException

from app.api.routers.backtest import validate_params


def test_valid_params_pass():
    assert validate_params(symbol="NABIL", fast_ma=5, slow_ma=20, days=365) is None


@pytest.mark.parametrize("kwargs", [
    {"symbol": "", "fast_ma": 5, "slow_ma": 20, "days": 365},
    {"symbol": "X" * 31, "fast_ma": 5, "slow_ma": 20, "days": 365},
    {"symbol": "NABIL", "fast_ma": 0, "slow_ma": 20, "days": 365},
    {"symbol": "NABIL", "fast_ma": 21, "slow_ma": 20, "days": 365},
    {"symbol": "NABIL", "fast_ma": 5, "slow_ma": 4, "days": 365},
    {"symbol": "NABIL", "fast_ma": 5, "slow_ma": 251, "days": 365},
    {"symbol": "NABIL", "fast_ma": 5, "slow_ma": 20, "days": 29},
    {"symbol": "NABIL", "fast_ma": 5, "slow_ma": 20, "days": 5001},
])
def test_invalid_params_raise_400(kwargs):
    with pytest.raises(HTTPException) as exc:
        validate_params(**kwargs)
    assert exc.value.status_code == 400