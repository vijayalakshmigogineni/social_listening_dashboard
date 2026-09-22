"""
Per-post orchestration for the SLD hierarchical classifier.

classify_post() runs Stage 1 (RCM relevance) -> short-circuits if
off-topic -> Stage 2 (content type) -> Stage 3 (deterministic rule
mapping to intent_level / problem & opportunity evidence / sld_candidate).

See sld_classifier.py for the full architecture explanation.
"""

import sld_classifier as clf


def classify_post(model, text: str, matched_keywords=None) -> dict:
    matched_keywords = matched_keywords or []

    if not text or not text.strip():
        return {
            "rcm_relevant": False,
            "rcm_relevant_score": None,
            "content_type": "empty_text",
            "content_type_score": None,
            "content_type_second_label": None,
            "content_type_second_score": None,
            "intent_level": None,
            "problem_evidence": False,
            "opportunity_evidence": False,
            "sld_candidate": False,
            "confidence_tier": "low",
            "margin": None,
            "needs_review": True,
            "evidence_quote": "",
            "classification_reason": "Post had no usable text.",
            "classification_method": "empty_text_shortcut",
            "classification_version": clf.CLASSIFIER_VERSION,
        }

    evidence_quote = clf.extract_evidence_quote(text, matched_keywords)

    # ---- Stage 1: RCM domain relevance ---------------------------------
    stage1 = clf.classify_rcm_relevance(model, text)
    rcm_relevant = stage1.label == "rcm_relevant"

    if not rcm_relevant:
        tier = "high" if stage1.margin >= 0.20 else "medium"
        return {
            "rcm_relevant": False,
            "rcm_relevant_score": round(stage1.top_score, 4),
            "content_type": "off_topic",
            "content_type_score": None,
            "content_type_second_label": None,
            "content_type_second_score": None,
            "intent_level": None,
            "problem_evidence": False,
            "opportunity_evidence": False,
            "sld_candidate": False,
            "confidence_tier": tier,
            "margin": round(stage1.margin, 4),
            "needs_review": stage1.margin < 0.20,
            "evidence_quote": evidence_quote,
            "classification_reason": (
                f"Stage 1 gate: classified as NOT RCM-domain-relevant "
                f"(score={stage1.top_score:.2f}, margin={stage1.margin:.2f}). "
                f"Stopped before content-type classification."
            ),
            "classification_method": "hierarchical_zero_shot_nli_v2",
            "classification_version": clf.CLASSIFIER_VERSION,
        }

    # ---- Stage 2: content type ------------------------------------------
    stage2 = clf.classify_content_type(model, text)
    content_type = stage2.label

    # ---- Stage 3: deterministic mapping (no model call) ------------------
    intent_level = clf.map_intent_level(content_type)
    problem_evidence, opportunity_evidence = clf.compute_evidence_flags(content_type)
    sld_candidate = problem_evidence or opportunity_evidence

    confidence_tier, needs_review = clf.compute_confidence(
        stage2.margin, stage2.top_score
    )

    if content_type in clf.OPERATIONAL_CONTENT_TYPES:
        intent_clause = (
            f"Mapped to intent_level={intent_level} because content_type "
            f"'{content_type}' is an operational category."
        )
    else:
        intent_clause = (
            f"intent_level is null because content_type '{content_type}' is "
            f"a non-operational category (career/education/job/general/news)."
        )

    reason = (
        f"Stage 1: RCM-domain-relevant (score={stage1.top_score:.2f}). "
        f"Stage 2: best-matching content type is '{content_type}' "
        f"(score={stage2.top_score:.2f}, margin={stage2.margin:.2f} vs "
        f"runner-up '{stage2.second_label}'). {intent_clause}"
    )

    return {
        "rcm_relevant": True,
        "rcm_relevant_score": round(stage1.top_score, 4),
        "content_type": content_type,
        "content_type_score": round(stage2.top_score, 4),
        "content_type_second_label": stage2.second_label,
        "content_type_second_score": round(stage2.second_score, 4),
        "intent_level": intent_level,
        "problem_evidence": problem_evidence,
        "opportunity_evidence": opportunity_evidence,
        "sld_candidate": sld_candidate,
        "confidence_tier": confidence_tier,
        "margin": round(stage2.margin, 4),
        "needs_review": needs_review,
        "evidence_quote": evidence_quote,
        "classification_reason": reason,
        "classification_method": "hierarchical_zero_shot_nli_v2",
        "classification_version": clf.CLASSIFIER_VERSION,
    }
