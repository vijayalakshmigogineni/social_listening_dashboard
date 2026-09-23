"""
llm_fallback.py in isolation: no real network call is made in these tests --
requests.post is mocked throughout. Confirms the module never raises out of
classify_stance_llm/classify_seeking_llm regardless of API/network outcome,
since Step 4 depends on that to keep the pipeline from crashing on an
optional enrichment call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.analysis import llm_fallback


def _mock_response(label: str, confidence: float, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "message": {"role": "assistant", "content": f'{{"label": "{label}", "confidence": {confidence}}}'}
    }
    return resp


def test_disabled_without_model_returns_none_and_makes_no_call():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", False), \
         patch.object(llm_fallback, "requests") as mock_requests:
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None
    mock_requests.post.assert_not_called()


def test_successful_stance_call_returns_label_and_confidence():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True), \
         patch.object(llm_fallback.requests, "post", return_value=_mock_response("seeking", 0.82)):
        result = llm_fallback.classify_stance_llm("Does anyone know how to fix this denial?")
    assert result == {"label": "seeking", "confidence": 0.82}


def test_successful_seeking_call_returns_label_and_confidence():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True), \
         patch.object(llm_fallback.requests, "post", return_value=_mock_response("L3", 0.91)):
        result = llm_fallback.classify_seeking_llm("Looking for a billing vendor for our clinic.")
    assert result == {"label": "L3", "confidence": 0.91}


def test_network_failure_returns_none_not_an_exception():
    import requests as real_requests

    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True), \
         patch.object(llm_fallback.requests, "post", side_effect=real_requests.ConnectionError("boom")):
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None


def test_malformed_json_body_returns_none_not_an_exception():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"message": {"role": "assistant", "content": "not json"}}
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True), \
         patch.object(llm_fallback.requests, "post", return_value=resp):
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None


def test_unexpected_label_returns_none():
    with patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True), \
         patch.object(llm_fallback.requests, "post", return_value=_mock_response("not_a_real_label", 0.9)):
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None
