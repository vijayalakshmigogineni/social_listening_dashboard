"""
Step 4 regression + new NLI-primary/LLM-fallback behavior.

run_zero_shot and the Gemini fallback are mocked throughout -- these tests
must not download the DeBERTa model or make a network call.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.analysis import step4_speaker_stance_seeking as step4


def _nli_result(label: str, top_score: float, margin: float) -> dict:
    second_score = top_score - margin
    return {
        "label": label,
        "top_score": top_score,
        "second_label": "other",
        "second_score": second_score,
        "margin": margin,
        "all_scores": {label: top_score, "other": second_score},
    }


def fake_run_zero_shot_factory(stance_result: dict | None, seeking_result: dict | None):
    """Dispatches on which label set was passed, so stance and seeking calls
    (both routed through the same run_zero_shot function) can be controlled
    independently within one test."""

    def _fake(text: str, labels: dict) -> dict:
        if set(labels.keys()) == set(step4.STANCE_LABELS.keys()):
            assert stance_result is not None, "stance NLI should not have been called"
            return stance_result
        if set(labels.keys()) == set(step4.SEEKING_LABELS.keys()):
            assert seeking_result is not None, "seeking NLI should not have been called"
            return seeking_result
        raise AssertionError(f"unexpected label set: {labels}")

    return _fake


# ---------------------------------------------------------------------------
# Speaker Type regression -- must remain rule-based and unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_speaker",
    [
        ("We offer a full RCM solution -- book a demo today!", "vendor"),
        ("I work for the insurance company processing claims all day.", "payer_side"),
        ("Our billing team can't keep up with prior auths this month.", "practice_side"),
        ("My insurance denied my claim for my surgery again.", "patient"),
        ("Here's how we solved denial management: 5 tips for practices.", "educator_media"),
        ("What is a CPT code?", "unknown"),
    ],
)
def test_speaker_type_regression(text, expected_speaker):
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(
        _nli_result("neutral", 0.9, 0.5), _nli_result("L0", 0.9, 0.5)
    )):
        result = step4.classify_context(text)
    assert result.speaker_type == expected_speaker


# ---------------------------------------------------------------------------
# Content stance -- NLI primary, confidence/margin gated, LLM fallback.
# ---------------------------------------------------------------------------


def test_stance_confident_nli_is_accepted_without_llm_call():
    stance = _nli_result("seeking", 0.9, 0.5)
    seeking = _nli_result("L1", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)), \
         patch.object(step4, "classify_stance_llm") as mock_llm:
        result = step4.classify_context("How do you handle CO-16 denials?")
    mock_llm.assert_not_called()
    assert result.content_stance == "seeking"
    assert result.stance_source == "nli"
    assert result.stance_confidence is not None


def test_stance_ambiguous_calls_llm_fallback():
    stance = _nli_result("neutral", 0.55, 0.05)  # below both thresholds
    seeking = _nli_result("L0", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)), \
         patch.object(step4, "classify_stance_llm", return_value={"label": "seeking", "confidence": 0.8}) as mock_llm:
        result = step4.classify_context("Some ambiguous RCM-adjacent text about billing.")
    mock_llm.assert_called_once()
    assert result.content_stance == "seeking"
    assert result.stance_source == "llm"
    assert result.stance_confidence == 0.8


def test_stance_ambiguous_llm_disabled_keeps_nli_result():
    stance = _nli_result("neutral", 0.55, 0.05)
    seeking = _nli_result("L0", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)), \
         patch.object(step4, "classify_stance_llm", return_value=None) as mock_llm:
        result = step4.classify_context("Some ambiguous RCM-adjacent text about billing.")
    mock_llm.assert_called_once()
    assert result.content_stance == "neutral"
    assert result.stance_source == "nli"


def test_mixed_stance_is_rule_based_and_skips_nli_entirely():
    # "does anyone know" -> seeking marker; "here's how" / "we solved" -> supplying marker.
    text = "Does anyone know a fix? Here's how we solved it for another client."

    def _fake(text, labels):
        if set(labels.keys()) == set(step4.SEEKING_LABELS.keys()):
            return _nli_result("L2", 0.9, 0.5)
        raise AssertionError("stance NLI must not be called when the mixed rule fires")

    with patch.object(step4, "run_zero_shot", _fake):
        result = step4.classify_context(text)
    assert result.content_stance == "mixed"
    assert result.stance_source == "rule"
    assert result.stance_confidence is None


# ---------------------------------------------------------------------------
# Seeking level -- NLI primary, confidence/margin gated, LLM fallback.
# ---------------------------------------------------------------------------


def test_seeking_confident_nli_is_accepted_without_llm_call():
    stance = _nli_result("seeking", 0.9, 0.5)
    seeking = _nli_result("L3", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)), \
         patch.object(step4, "classify_seeking_llm") as mock_llm:
        result = step4.classify_context("Looking for an RCM vendor for our pain clinic.")
    mock_llm.assert_not_called()
    assert result.seeking_level == "L3"
    assert result.seeking_source == "nli"


def test_seeking_ambiguous_calls_llm_fallback():
    stance = _nli_result("seeking", 0.9, 0.5)
    seeking = _nli_result("L1", 0.55, 0.05)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)), \
         patch.object(step4, "classify_seeking_llm", return_value={"label": "L2", "confidence": 0.7}) as mock_llm:
        result = step4.classify_context("How do you handle this recurring denial issue?")
    mock_llm.assert_called_once()
    assert result.seeking_level == "L2"
    assert result.seeking_source == "llm"
    assert result.seeking_confidence == 0.7


def test_seeking_level_null_when_stance_is_supplying():
    stance = _nli_result("supplying", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, None)), \
         patch.object(step4, "classify_seeking_llm") as mock_llm:
        result = step4.classify_context("Here is an explainer on how CPT modifiers work.")
    mock_llm.assert_not_called()
    assert result.content_stance == "supplying"
    assert result.seeking_level is None
    assert result.seeking_source is None


def test_seeking_level_can_be_non_null_when_stance_is_neutral():
    # Regression: seeking_level is not gated on content_stance == "seeking"
    # (step6_scoring.py reads seeking_level unconditionally).
    stance = _nli_result("neutral", 0.9, 0.5)
    seeking = _nli_result("L0", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)):
        result = step4.classify_context("Our denials are up this quarter.")
    assert result.content_stance == "neutral"
    assert result.seeking_level == "L0"


def test_empty_text_short_circuits_without_any_model_call():
    with patch.object(step4, "run_zero_shot") as mock_nli, \
         patch.object(step4, "classify_stance_llm") as mock_stance_llm, \
         patch.object(step4, "classify_seeking_llm") as mock_seeking_llm:
        result = step4.classify_context("")
    mock_nli.assert_not_called()
    mock_stance_llm.assert_not_called()
    mock_seeking_llm.assert_not_called()
    assert result.content_stance == "neutral"
    assert result.speaker_type == "unknown"
    assert result.seeking_level is None
