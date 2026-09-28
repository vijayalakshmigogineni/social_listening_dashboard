"""
The semantic pipeline architecture: Step 1 rule gate + LLM resolution of
ambiguous records only, Step 2 as one semantic LLM call, reply/parent
separation, validation, legacy fallback, and unchanged scoring inputs.
Every LLM call is mocked at the stage level; no network, no NLI model.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.analysis import llm_fallback, step1_relevance, step2_semantic
from app.analysis import pipeline as pipeline_module
from app.analysis.scoring_opportunity import SEEKING_POINTS
from app.schemas.analysis import Step2ProblemEvidence, Step4Context

CLEAR_TEXT = "We keep getting claim denials from Aetna for this procedure. Has anyone else seen this?"
ZERO_HIT_TEXT = "Our 835s stopped posting after the update. Anyone else?"
OFF_TOPIC = "I love hiking on weekends."


@pytest.fixture(autouse=True)
def _fresh_stats():
    llm_fallback.reset_call_stats()
    yield
    llm_fallback.reset_call_stats()


def _semantic(**overrides) -> dict:
    base = {
        "problem_evidence": True, "problem_current": True, "problem_recurring": True,
        "first_person": True, "operational_impact": False,
        "speaker_type": "practice_side", "content_stance": "seeking", "seeking_level": "L1",
        "evidence_quote": "We keep getting claim denials from Aetna for this procedure.",
        "problem_confidence": 0.94, "first_person_confidence": 0.9,
        "operational_impact_confidence": 0.8, "speaker_confidence": 0.9,
        "stance_confidence": 0.95, "seeking_confidence": 0.89,
        "pain_severity": "moderate", "business_impact": "moderate", "probeps_fit": "high",
        "opportunity_type": "denial_management",
        "opportunity_reasoning": "A practice reports recurring Aetna denials it cannot resolve.",
        "pain_confidence": 0.8, "impact_confidence": 0.7, "fit_confidence": 0.85,
    }
    base.update(overrides)
    return base


_LLM_NAMES = {"pain_confidence": "pain_severity_confidence",
              "impact_confidence": "business_impact_confidence",
              "fit_confidence": "probeps_fit_confidence"}


def _raw(**overrides) -> dict:
    """_semantic() as the LLM itself returns it: the opportunity confidences
    carry their field-named keys (the client maps them back)."""
    return {_LLM_NAMES.get(k, k): v for k, v in _semantic(**overrides).items()}


def _run(text, relevance=None, semantic=None, parent_text=None, source="reddit", title=""):
    """Runs the traced pipeline with both LLM calls mocked; returns
    (v3 row, trace, relevance_mock, semantic_mock)."""
    with patch.object(step1_relevance, "classify_relevance_llm", return_value=relevance) as rel, \
         patch.object(step2_semantic, "analyze_semantics_llm", return_value=semantic) as sem:
        row, trace = pipeline_module.run_pipeline_traced(
            source_item_id="x1", title=title, text=text, created_at=None,
            parent_text=parent_text, source=source,
        )
    return row, trace, rel, sem


# ---------------------------------------------------------------------------
# Step 1 routing and call pattern
# ---------------------------------------------------------------------------
def test_clearly_relevant_bypasses_relevance_llm_and_makes_one_semantic_call():
    results, trace, rel, sem = _run(CLEAR_TEXT, semantic=_semantic())
    rel.assert_not_called()
    sem.assert_called_once()
    s1 = trace["step1_rcm_relevance"]
    assert s1["relevance_status"] == "clearly_relevant"
    assert s1["relevance_method"] == "rules"
    assert s1["rcm_relevant"] is True
    assert trace["step2_semantic"]["semantic_source"] == "llm"


def test_single_keyword_hit_is_clearly_relevant():
    step1 = step1_relevance.classify_rcm_relevance("x", matched_keywords=["billing"])
    assert (step1.rcm_relevant, step1.relevance_status, step1.relevance_method) == (
        True, "clearly_relevant", "rules")


def test_zero_hit_relevant_is_resolved_by_llm_then_proceeds():
    results, trace, rel, sem = _run(ZERO_HIT_TEXT, relevance={"relevant": True, "confidence": 0.91},
                                    semantic=_semantic(evidence_quote="Our 835s stopped posting"))
    rel.assert_called_once()
    sem.assert_called_once()
    s1 = trace["step1_rcm_relevance"]
    assert (s1["relevance_status"], s1["relevance_method"], s1["rcm_relevant"]) == ("ambiguous", "llm", True)
    assert s1["rcm_relevance_confidence"] == 0.91


def test_zero_hit_not_relevant_stops_after_one_call():
    results, trace, rel, sem = _run(OFF_TOPIC, relevance={"relevant": False, "confidence": 0.88})
    rel.assert_called_once()
    sem.assert_not_called()
    s1 = trace["step1_rcm_relevance"]
    # No third status: it stays "ambiguous", resolved to not relevant.
    assert (s1["relevance_status"], s1["relevance_method"], s1["rcm_relevant"]) == ("ambiguous", "llm", False)
    assert trace["step2_semantic"] is None
    assert results.rcm_relevant is False and results.final_score == 0.0


def test_relevance_llm_unavailable_falls_back_to_nli():
    nli = {"label": "not_rcm_relevant", "top_score": 0.9, "margin": 0.8}
    with patch.object(step1_relevance, "run_zero_shot", return_value=nli) as zs:
        results, trace, rel, sem = _run(OFF_TOPIC, relevance=None)
    zs.assert_called_once()
    s1 = trace["step1_rcm_relevance"]
    assert (s1["relevance_status"], s1["relevance_method"], s1["rcm_relevant"]) == ("ambiguous", "fallback", False)


def test_empty_text_makes_no_call():
    results, trace, rel, sem = _run("", relevance={"relevant": True, "confidence": 1.0})
    rel.assert_not_called()
    sem.assert_not_called()
    assert trace["step1_rcm_relevance"]["rcm_relevant"] is False


# ---------------------------------------------------------------------------
# Step 2 fields, validation and backward-compatible projection
# ---------------------------------------------------------------------------
def test_semantic_fields_reach_the_persisted_row():
    results, trace, _, _ = _run(CLEAR_TEXT, semantic=_semantic(speaker_type="practice_side",
                                                              seeking_level="L3"))
    v1 = results
    assert v1.problem_evidence is True and v1.first_person is True
    assert v1.speaker_type == "practice_side"
    assert v1.content_stance == "seeking"
    assert v1.seeking_level == "L3"
    assert v1.evidence_quote == "We keep getting claim denials from Aetna for this procedure."
    sem = trace["step2_semantic"]
    for field in ("problem_current", "problem_recurring", "operational_impact"):
        assert field in sem
    assert (sem["probeps_fit"], sem["opportunity_type"]) == ("high", "denial_management")
    # The LLM output is persisted with the score, for offline re-scoring.
    assert v1.score_breakdown["llm_assessment"]["probeps_fit"] == "high"
    assert v1.score_breakdown["llm_source"] == "llm"


def test_supplying_forces_null_seeking_level():
    results, trace, _, _ = _run(CLEAR_TEXT, semantic=_semantic(content_stance="supplying", seeking_level="L1"))
    assert results.seeking_level is None
    assert trace["step5_evidence_confidence"]["seeking_confidence"] is None


def test_semantic_llm_unavailable_uses_legacy_stages():
    legacy_problem = Step2ProblemEvidence(problem_evidence=True, first_person=False,
                                          problem_confidence=0.7, evidence_candidate=None)
    legacy_context = Step4Context(speaker_type="unknown", content_stance="neutral", seeking_level="L0",
                                  stance_confidence=0.6, seeking_confidence=0.6)
    with patch.object(step2_semantic, "classify_problem_evidence", return_value=legacy_problem) as p, \
         patch.object(step2_semantic, "classify_context", return_value=legacy_context) as c:
        results, trace, _, sem = _run(CLEAR_TEXT, semantic=None)
    sem.assert_called_once()
    p.assert_called_once()
    c.assert_called_once()
    assert trace["step2_semantic"]["semantic_source"] == "fallback"
    assert results.seeking_level == "L0"
    # The fallback cannot judge opportunity value: those fields are None and
    # contribute nothing.
    assert trace["step2_semantic"]["probeps_fit"] is None
    assert results.score_breakdown["llm_points"]["probeps_fit"] == 0.0
    assert results.score_breakdown["llm_source"] == "fallback"


# ---------------------------------------------------------------------------
# Replies: parent is context, never evidence
# ---------------------------------------------------------------------------
PARENT = "Our claims keep getting denied by Aetna."
REPLY = "We have the same issue with the billing office."


def test_reply_and_parent_are_sent_separately():
    _, trace, _, sem = _run(REPLY, semantic=_semantic(evidence_quote=REPLY), parent_text=PARENT, source="aapc")
    args = sem.call_args.args
    assert args[0] == REPLY          # current post alone
    assert args[1] == PARENT         # parent as separate context
    assert PARENT not in args[0]
    assert trace["parent_text"] == PARENT


def test_parent_sentence_is_rejected_as_evidence_quote():
    results, _, _, _ = _run(REPLY, semantic=_semantic(evidence_quote=PARENT), parent_text=PARENT)
    assert results.evidence_quote != PARENT
    assert results.evidence_quote in REPLY


def test_embedded_forum_quote_is_stripped_and_used_as_context():
    text = f"bob said:\n{PARENT}\nClick to expand...\n{REPLY}"
    _, _, _, sem = _run(text, semantic=_semantic(evidence_quote=REPLY), source="aapc")
    post_arg, parent_arg = sem.call_args.args[0], sem.call_args.args[1]
    assert post_arg.strip() == REPLY
    assert PARENT in parent_arg


def test_quote_is_matched_whitespace_and_case_insensitively_to_exact_span():
    assert step2_semantic.verbatim_span("we  keep getting CLAIM denials", CLEAR_TEXT) == \
        "We keep getting claim denials"
    assert step2_semantic.verbatim_span("totally paraphrased", CLEAR_TEXT) is None


# ---------------------------------------------------------------------------
# Opportunity scoring receives the semantic seeking_level (and its confidence)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("level", ["L0", "L1", "L2", "L3"])
def test_scoring_receives_semantic_seeking_level(level):
    row, _, _, _ = _run(CLEAR_TEXT, semantic=_semantic(seeking_level=level))
    assert row.seeking_level == level
    assert row.score_breakdown["llm_points"]["seeking"] == pytest.approx(SEEKING_POINTS[level] * 0.89)


def test_stage_numbers_match_stage_names():
    stages: list[int] = []
    with patch.object(step2_semantic, "analyze_semantics_llm", return_value=_semantic()):
        pipeline_module.run_pipeline(
            source_item_id="x", title="", text=CLEAR_TEXT, created_at=None, on_stage=stages.append)
    assert stages == list(range(1, len(pipeline_module.STAGE_NAMES) + 1))


# ---------------------------------------------------------------------------
# LLM client: structured output validation
# ---------------------------------------------------------------------------
def _ollama(content: dict | str):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"message": {"content": content if isinstance(content, str) else json.dumps(content)}}
    return resp


def _enabled():
    return (patch.object(llm_fallback, "PROVIDER", "ollama"),
            patch.object(llm_fallback, "LLM_FALLBACK_ENABLED", True))


def test_semantic_client_validates_and_normalizes():
    p1, p2 = _enabled()
    raw = _raw(seeking_level="none", problem_confidence=1.7)
    with p1, p2, patch.object(llm_fallback.requests, "post", return_value=_ollama(raw)) as post:
        out = llm_fallback.analyze_semantics_llm(REPLY, PARENT, "aapc")
    assert out["seeking_level"] is None
    assert out["problem_confidence"] == 1.0
    assert (out["probeps_fit"], out["opportunity_type"]) == ("high", "denial_management")
    assert out["fit_confidence"] == 0.85
    user_msg = post.call_args.kwargs["json"]["messages"][1]["content"]
    assert user_msg.index("PARENT POST") < user_msg.index("CURRENT POST")
    assert llm_fallback.CALL_STATS_BY_KIND["semantic"]["succeeded"] == 1


@pytest.mark.parametrize("bad", [
    _raw(speaker_type="biller"),
    _raw(content_stance="asking"),
    _raw(seeking_level="L4"),
    _raw(first_person="yes"),
    _raw(stance_confidence="high"),
    _raw(probeps_fit="very_high"),
    _raw(business_impact=None),
    _raw(opportunity_type="sales_lead"),
    _raw(opportunity_reasoning=3),
    _raw(fit_confidence="high"),
    {k: v for k, v in _raw().items() if k != "problem_confidence"},
    {k: v for k, v in _raw().items() if k != "problem_evidence"},
    "not json",
])
def test_semantic_client_rejects_malformed_output(bad):
    p1, p2 = _enabled()
    with p1, p2, patch.object(llm_fallback.requests, "post", return_value=_ollama(bad)):
        assert llm_fallback.analyze_semantics_llm(REPLY) is None
    assert llm_fallback.CALL_STATS_BY_KIND["semantic"]["failed"] >= 1


def test_missing_opportunity_confidence_is_tolerated_as_none():
    # Nova sometimes drops one confidence; that signal then scores 0 instead
    # of the whole classification being thrown away.
    p1, p2 = _enabled()
    raw = {k: v for k, v in _raw().items() if k != "business_impact_confidence"}
    with p1, p2, patch.object(llm_fallback.requests, "post", return_value=_ollama(raw)):
        out = llm_fallback.analyze_semantics_llm(REPLY)
    assert out is not None and out["impact_confidence"] is None
    with patch.object(step2_semantic, "analyze_semantics_llm", return_value=out):
        row = pipeline_module.run_pipeline(source_item_id="x", title="", text=CLEAR_TEXT, created_at=None)
    assert row.score_breakdown["llm_points"]["business_impact"] == 0.0
    assert row.score_breakdown["llm_points"]["probeps_fit"] > 0


def test_relevance_client_validates():
    p1, p2 = _enabled()
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama({"relevant": True, "confidence": 0.91})):
        assert llm_fallback.classify_relevance_llm(ZERO_HIT_TEXT) == {"relevant": True, "confidence": 0.91}
    with p1, p2, patch.object(llm_fallback.requests, "post",
                              return_value=_ollama({"relevant": "yes", "confidence": 0.91})):
        assert llm_fallback.classify_relevance_llm(ZERO_HIT_TEXT) is None
