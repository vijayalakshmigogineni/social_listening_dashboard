"""
Central config. Reads secrets from the repo-root .env (per project convention:
"use .env for apify token"), not from backend/.env, so collectors share the
same credentials the existing testing/ scripts use.
"""

from pathlib import Path

from dotenv import load_dotenv
import os

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(REPO_ROOT / ".env")

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_TOKEN1 = os.getenv("APIFY_TOKEN1")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'sld.db').as_posix()}"
