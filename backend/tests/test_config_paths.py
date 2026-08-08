"""Config sanity: all persistent paths resolve under backend/data regardless of CWD."""

from app.core.config import BASE_DIR, DATA_DIR, DB_PATH

from app.providers.cache import CACHE_DIR as P_CACHE_DIR
from app.providers.ipos import IPO_JSON_PATH as P_IPO_JSON_PATH
from app.search.fuzzy import SECURITY_CACHE_PATH as P_SECURITY_PATH


def test_data_dir_is_backend_data():
    assert BASE_DIR.name == "backend"
    assert DATA_DIR.name == "data"
    assert DATA_DIR.parent == BASE_DIR


def test_resolved_paths_live_under_data_dir():
    assert DB_PATH.parent == DATA_DIR
    assert P_CACHE_DIR.parent == DATA_DIR
    assert P_IPO_JSON_PATH.parent == DATA_DIR
    assert P_SECURITY_PATH.parent == DATA_DIR