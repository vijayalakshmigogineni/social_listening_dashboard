"""
llm_fallback.py in isolation: no real network call is made in these tests --
requests (Ollama) and the Bedrock client are mocked throughout. Confirms the
module never raises out of classify_stance_llm/classify_seeking_llm regardless
of API/network outcome, since Step 4 depends on that to keep the pipeline from
crashing on an optional enrichment call, and that only the selected provider
is ever called.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests as real_requests
from botocore.exceptions import ClientError, EndpointConnectionError

from app.analysis import llm_fallback


@pytest.fixture(autouse=True)
def _fresh_stats():
    llm_fallback.reset_call_stats()
    yield
    llm_fallback.reset_call_stats()


def _provider(name: str, enabled: bool = True):
    """Patch both switches together, as the module sets them at import."""
    return (patch.object(llm_fallback, "PROVIDER", name),
            patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", enabled))


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
def _ollama_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"message": {"role": "assistant", "content": content}}
    return resp


def test_ollama_stance_call_returns_label_and_confidence():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama_response('{"label": "seeking", "confidence": 0.82}')) as post:
        result = llm_fallback.classify_stance_llm("Does anyone know how to fix this denial?")
    assert result == {"label": "seeking", "confidence": 0.82}
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == llm_fallback.OLLAMA_MODEL
    assert payload["format"]["properties"]["label"]["enum"] == llm_fallback.STANCE_LABELS
    assert payload["options"]["temperature"] == 0.0
    assert llm_fallback.CALL_STATS == {"attempted": 1, "succeeded": 1, "failed": 0}


def test_ollama_seeking_call_returns_label_and_confidence():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama_response('{"label": "L3", "confidence": 0.91}')):
        result = llm_fallback.classify_seeking_llm("Looking for a billing vendor for our clinic.")
    assert result == {"label": "L3", "confidence": 0.91}


def test_ollama_never_touches_bedrock():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama_response('{"label": "L1", "confidence": 0.7}')), \
         patch.object(llm_fallback, "_get_client") as get_client:
        llm_fallback.classify_seeking_llm("How do you handle this?")
    get_client.assert_not_called()


def test_ollama_connection_failure_returns_none_and_counts_failure():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              side_effect=real_requests.ConnectionError("boom")):
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None
    assert llm_fallback.CALL_STATS == {"attempted": 1, "succeeded": 0, "failed": 1}


def test_ollama_malformed_json_returns_none():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post", return_value=_ollama_response("not json")):
        assert llm_fallback.classify_stance_llm("some text") is None


def test_ollama_unexpected_label_returns_none():
    p1, p2 = _provider("ollama")
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama_response('{"label": "nope", "confidence": 0.9}')):
        assert llm_fallback.classify_stance_llm("some text") is None


def test_ollama_model_available_checks_tags():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"models": [{"name": "llama3.1:latest"}, {"name": "qwen3:8b"}]}
    with patch.object(llm_fallback.requests, "get", return_value=resp):
        assert llm_fallback.ollama_model_available("llama3.1")
        assert not llm_fallback.ollama_model_available("llama3.2")
    with patch.object(llm_fallback.requests, "get", side_effect=real_requests.ConnectionError()):
        assert not llm_fallback.ollama_model_available("llama3.1")


# ---------------------------------------------------------------------------
# Disabled
# ---------------------------------------------------------------------------
def test_disabled_returns_none_and_makes_no_call():
    p1, p2 = _provider("none", enabled=False)
    with p1, p2, patch.object(llm_fallback.requests, "post") as post, \
         patch.object(llm_fallback, "_get_client") as get_client:
        result = llm_fallback.classify_stance_llm("some text")
    assert result is None
    post.assert_not_called()
    get_client.assert_not_called()
    assert llm_fallback.CALL_STATS["attempted"] == 0


# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------
def _converse_response(tool_input) -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "t1", "name": llm_fallback.TOOL_NAME, "input": tool_input}}
        ]}},
        "stopReason": "tool_use",
    }


def _mock_client(return_value=None, side_effect=None) -> MagicMock:
    client = MagicMock()
    client.converse.return_value = return_value
    client.converse.side_effect = side_effect
    return client


def test_bedrock_stance_call_returns_label_and_confidence():
    client = _mock_client(_converse_response({"label": "seeking", "confidence": 0.82}))
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=client), \
         patch.object(llm_fallback.requests, "post") as post:
        result = llm_fallback.classify_stance_llm("Does anyone know how to fix this denial?")
    assert result == {"label": "seeking", "confidence": 0.82}
    post.assert_not_called()


def test_bedrock_request_forces_the_classification_tool_with_label_enum():
    client = _mock_client(_converse_response({"label": "L1", "confidence": 0.7}))
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=client):
        llm_fallback.classify_seeking_llm("How do you handle this?")
    kwargs = client.converse.call_args.kwargs
    assert kwargs["toolConfig"]["toolChoice"] == {"tool": {"name": llm_fallback.TOOL_NAME}}
    schema = kwargs["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"]
    assert schema["properties"]["label"]["enum"] == llm_fallback.SEEKING_LABELS
    assert kwargs["inferenceConfig"]["temperature"] == 0.0


def test_bedrock_network_failure_returns_none():
    client = _mock_client(side_effect=EndpointConnectionError(endpoint_url="https://bedrock"))
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=client):
        assert llm_fallback.classify_stance_llm("some text") is None


def test_bedrock_access_denied_returns_none():
    error = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "no"}}, "Converse")
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=_mock_client(side_effect=error)):
        assert llm_fallback.classify_stance_llm("some text") is None


def test_bedrock_text_reply_without_tool_use_returns_none():
    resp = {"output": {"message": {"role": "assistant", "content": [{"text": "seeking"}]}}}
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=_mock_client(resp)):
        assert llm_fallback.classify_stance_llm("some text") is None


def test_non_numeric_confidence_returns_none():
    client = _mock_client(_converse_response({"label": "seeking", "confidence": "high"}))
    p1, p2 = _provider("bedrock")
    with p1, p2, patch.object(llm_fallback, "_get_client", return_value=client):
        assert llm_fallback.classify_stance_llm("some text") is None
