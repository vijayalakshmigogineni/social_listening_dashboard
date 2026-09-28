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

# LLM provider for Step 1 (ambiguous relevance) and Step 2 (semantic
# analysis): "ollama" (local, default), "bedrock", or "none". Only the
# selected provider's client is ever loaded, so an Ollama run never imports
# boto3 or contacts AWS.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
# The production database file is "sld 1.db" (the space is part of the name).
DATABASE_PATH = DATA_DIR / "sld 1.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
