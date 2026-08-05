"""Application configuration loaded from environment variables and defaults.

The ``.env`` file at the project root is loaded automatically on import.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "nepse.db"

load_dotenv(Path(__file__).resolve().parent / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_k_m")

# --- Data source base URLs ---
YONEPSE_BASE = "https://shubhamnpk.github.io/yonepse"
MEROLAGANI_BASE = "https://merolagani.com"
SHARESANSAR_BASE = "https://www.sharesansar.com"
NEPALIPAISA_BASE = "https://nepalipaisa.com"
NEPSEMAN_BASE = "https://nepseman-api-production.up.railway.app"
GITHUB_NEPSE_DATA = "https://raw.githubusercontent.com/Aabishkar2/nepse-data/main/data/company-wise"

# --- HTTP timeouts (seconds) ---
HTTP_TIMEOUT = 15
SHARESANSAR_TIMEOUT = 20
MEROLAGANI_TIMEOUT = 20

# --- User agents ---
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

os.makedirs(DATA_DIR, exist_ok=True)
