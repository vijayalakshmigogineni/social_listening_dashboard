"""
Tests never talk to a real LLM: the client is disabled by default for every
test, so an Ollama server that happens to be running cannot change results.
Tests that exercise an LLM path either mock the stage-level call
(analyze_semantics_llm / classify_relevance_llm / classify_*_llm) or, in
test_llm_fallback.py, re-enable the client explicitly with a mocked transport.
"""

from __future__ import annotations

import os

# Tests never touch the production database (Neon): an empty DATABASE_URL
# makes app.config fall back to SQLite, and load_dotenv never overrides a
# variable that is already set. Must run before any `app` import.
os.environ["DATABASE_URL"] = ""

from unittest.mock import patch  # noqa: E402

import pytest

from app.analysis import llm_fallback


@pytest.fixture(autouse=True)
def _llm_disabled():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", False):
        yield
