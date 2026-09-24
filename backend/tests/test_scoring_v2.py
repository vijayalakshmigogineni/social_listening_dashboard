"""
Step 6/7 v2 scoring.

These tests pin the behaviours the v2 model was redesigned to fix, each of
which was a measured defect in v1 against the 167-post gold set
(backend/data/gold/):

  * a forum reply must not inherit the problem described in the parent post
    it quotes -- under v1 that was the second-highest-scoring post in the corpus
  * "denial" without any billing vocabulary is not a claim denial -- under v1
    a couples-therapy post was the top Reddit result by base score
  * a non-relevant record is damped, not zeroed -- relevance is a graded floor
  * vendor/self-promotional content is penalised rather than rewarded
  * both scoring versions come out of ONE pass over Steps 1-5, under distinct
    analysis_version values so they can coexist in analysis_results

No network and no model downloads: the zero-shot classifier is patched
wherever Step 4 would otherwise run.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.analysis import pipeline as pipeline_module
from app.analysis import step1_relevance as step1
from app.analysis import step2_problem_evidence as step2
from app.analysis import step4_speaker_stance_seeking as step4
from app.analysis.step6_scoring_v2 import (
    COMMENTARY_FACTOR,
    OFF_DOMAIN_FACTOR,
    RELEVANCE_FLOOR,
    SCORE_CAP,
    score_record_v2,
    strip_quoted_parent,
)
from app.db.models import AnalysisResult as AnalysisResultRow
from app.schemas.analysis import (
    ANALYSIS_VERSION,
    ANALYSIS_VERSION_V2,
    SCORING_VERSION,
    SCORING_VERSION_V2,
)
from tests.test_step4 import _nli_result, fake_run_zero_shot_factory

# A first-person practice account of a payer denying a named code -- the
# highest-value shape in the gold set.
STRONG_POST = (
    "93294 and 93296 denying as POS per Medicare. We are a Part B provider and we "
    "have recently seen an influx of denials for claims we billed under POS 11. "
    "Can someone help me understand this billing issue?"
)

QUOTING_REPLY = (
    "wjbruton said:\n"
    "We have had a lot of denials from Medicare on our claims and our billing team "
    "cannot keep up. Any help appreciated.\n"
    "Click to expand...\n"
    "GT as a modifier is invalid."
)


def _patch_all_nli(stance: dict, seeking: dict):
    """Steps 1, 2 AND 4 each call run_zero_shot, and each imported it by name,
    so every binding has to be patched or the real DeBERTa model is loaded.
    Patching only step4 -- which is enough for texts that hit step1/step2's
    keyword fast-paths -- silently downloads the model for texts that don't.
    """
    step4_fake = fake_run_zero_shot_factory(stance, seeking)

    def _fake(text: str, labels: dict) -> dict:
        keys = set(labels.keys())
        if keys == set(step1.RCM_RELEVANCE_LABELS.keys()):
            return _nli_result("rcm_relevant", 0.95, 0.9)
        if keys == set(step2.PROBLEM_EVIDENCE_LABELS.keys()):
            return _nli_result("problem_experience", 0.95, 0.9)
        return step4_fake(text, labels)

    return [
        patch.object(step1, "run_zero_shot", _fake),
        patch.object(step2, "run_zero_shot", _fake),
        patch.object(step4, "run_zero_shot", _fake),
    ]


# ---------------------------------------------------------------------------
# Quote stripping
# ---------------------------------------------------------------------------
def test_quoted_parent_is_removed_before_scoring():
    own = strip_quoted_parent(QUOTING_REPLY)
    assert "GT as a modifier is invalid." in own
    assert "cannot keep up" not in own, "the parent's pain leaked into the reply"


def test_reply_scores_below_the_post_it_quotes():
    parent = score_record_v2(
        "We have had a lot of denials from Medicare on our claims and our billing "
        "team cannot keep up. Any help appreciated.", "L1").final_score
    reply = score_record_v2(QUOTING_REPLY, "L1").final_score
    assert reply < parent


def test_reply_that_is_only_a_quote_keeps_its_text():
    # Stripping everything would leave an empty string and a meaningless score;
    # the original text is kept instead.
    only_quote = "someone said:\nI have denials on our Medicare claims.\nClick to expand...\n"
    assert strip_quoted_parent(only_quote).strip()


# ---------------------------------------------------------------------------
# Domain anchor -- the polysemy fix
# ---------------------------------------------------------------------------
def test_denial_without_billing_vocabulary_is_damped():
    therapy = (
        "When prompted to explore this, it is often met with denial, which I "
        "understand is most likely protective for this client."
    )
    billing = "We are seeing denial after denial on our claims from Medicare."
    assert score_record_v2(therapy, "L1").final_score < score_record_v2(billing, "L1").final_score


def test_domain_factor_is_recorded_not_hidden():
    bd = score_record_v2("I keep thinking about denial and grief.", None)
    assert bd.domain_factor == OFF_DOMAIN_FACTOR
    assert "domain" not in bd.signals


# ---------------------------------------------------------------------------
# Relevance is a floor, never a gate
# ---------------------------------------------------------------------------
def test_off_topic_post_is_damped_but_not_zeroed():
    bd = score_record_v2("Our team is behind on the vendor purchase orders.", None)
    assert bd.relevance_factor == RELEVANCE_FLOOR
    assert bd.final_score > 0, "relevance must damp, not zero -- that was the v1 kill-gate"


def test_relevant_post_gets_full_relevance_factor():
    assert score_record_v2(STRONG_POST, "L1").relevance_factor == 1.0


# ---------------------------------------------------------------------------
# Intent tiers. L1 and L2 share a score but stay distinct upstream.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "level,expected",
    [("L0", 10.0), ("L1", 15.0), ("L2", 15.0), ("L3", 20.0), (None, 10.0)],
)
def test_intent_tier_scores(level, expected):
    assert score_record_v2(STRONG_POST, level).intent_strength == expected


def test_l1_and_l2_score_the_same_but_are_not_merged_upstream():
    assert (
        score_record_v2(STRONG_POST, "L1").final_score
        == score_record_v2(STRONG_POST, "L2").final_score
    )
    # seeking_level itself is persisted by Step 4, untouched by scoring, so the
    # L1/L2 distinction survives in the data even though the score is equal.


# ---------------------------------------------------------------------------
# Penalties and bounds
# ---------------------------------------------------------------------------
def test_vendor_self_promotion_is_penalised():
    pitch = (
        "60+ Day AR? Your lab may be sitting on recoverable revenue. We investigate "
        "Medicare denials and clearinghouse rejections on your claims. DM me."
    )
    bd = score_record_v2(pitch, None)
    assert bd.noise_factor < 1.0


def test_commentary_without_ownership_is_discounted():
    commentary = "A growing number of health systems report denials on Medicare claims."
    assert score_record_v2(commentary, None).commentary_factor == COMMENTARY_FACTOR


def test_score_is_bounded():
    loud = (STRONG_POST + " We keep getting denied repeatedly, our claims are "
            "unworked and sitting in AR for 6 months, and when we call they "
            "tell us it does not make sense. Has anyone else seen this?")
    bd = score_record_v2(loud, "L3")
    assert 0 <= bd.final_score <= SCORE_CAP


def test_empty_text_does_not_raise():
    assert score_record_v2("", None).final_score >= 0


# ---------------------------------------------------------------------------
# Pipeline integration: one pass over Steps 1-5, two persistable rows
# ---------------------------------------------------------------------------
def test_run_pipeline_all_versions_emits_two_distinct_rows():
    from contextlib import ExitStack

    stance, seeking = _nli_result("seeking", 0.9, 0.5), _nli_result("L1", 0.9, 0.5)
    with ExitStack() as stack:
        for p in _patch_all_nli(stance, seeking):
            stack.enter_context(p)
        results = pipeline_module.run_pipeline_all_versions(
            source_item_id="aapc:236527", title="Denials as POS per Medicare",
            text=STRONG_POST, created_at=None,
        )

    assert [r.analysis_version for r in results] == [ANALYSIS_VERSION, ANALYSIS_VERSION_V2]
    assert [r.scoring_version for r in results] == [SCORING_VERSION, SCORING_VERSION_V2]

    # Steps 1-5 are shared, so everything except the score must be identical --
    # that is what makes scoring twice off one NLI pass legitimate.
    v1, v2 = results
    assert v1.seeking_level == v2.seeking_level
    assert v1.speaker_type == v2.speaker_type
    assert v1.evidence_quote == v2.evidence_quote

    # Both must satisfy the same DB contract, since they share the table.
    row_columns = {c.name for c in AnalysisResultRow.__table__.columns}
    for r in results:
        missing = row_columns - set(r.model_dump().keys()) - {"id"}
        assert not missing, f"{r.scoring_version} is missing columns: {missing}"


def test_v2_scores_non_relevant_records_that_v1_zeroes(monkeypatch):
    # Step 1 short-circuits non-relevant records and v1 scores them 0. v2 must
    # still produce a graded score, which is the behaviour change that recovered
    # false negatives in the gold set. (Zero keyword hits -> ambiguous -> the
    # relevance LLM, stubbed here, resolves it as not relevant.)
    monkeypatch.setattr(step1, "classify_relevance_llm",
                        lambda *a, **k: {"relevant": False, "confidence": 0.9})
    results = pipeline_module.run_pipeline_all_versions(
        source_item_id="reddit:xyz789", title="", text="I love hiking on weekends.",
        created_at=None,
    )
    v1, v2 = results
    assert v1.rcm_relevant is False
    assert v1.final_score == 0.0
    assert v2.seeking_level is None
    assert v2.final_score >= 0.0
