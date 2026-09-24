"""
Tests never talk to a real LLM: the client is disabled by default for every
test, so an Ollama server that happens to be running cannot change results.
Tests that exercise an LLM path either mock the stage-level call
(analyze_semantics_llm / classify_relevance_llm / classify_*_llm) or, in
test_llm_fallback.py, re-enable the client explicitly with a mocked transport.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.analysis import llm_fallback


@pytest.fixture(autouse=True)
def _llm_disabled():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", False):
        yield
