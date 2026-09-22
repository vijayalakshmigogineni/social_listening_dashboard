"""
Lazy-loaded pretrained NLP models, shared across analysis pipeline stages.

Loading a transformer model is expensive (a few seconds, plus a one-time
download), so every stage that needs the zero-shot classifier gets it from
here instead of instantiating its own pipeline. Swappable by design: change
ZERO_SHOT_MODEL_NAME (or replace get_zero_shot_classifier's body) without
touching any stage's code.
"""

from __future__ import annotations

# MoritzLaurer/deberta-v3-base-zeroshot-v2.0 was validated against
# facebook/bart-large-mnli in the existing research codebase
# (testing/compare_classifiers.py): bart forced several career/job posts
# into confident-looking false positives that this model got right, at a
# similar (base-sized) model weight.
ZERO_SHOT_MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"

_zero_shot_classifier = None


def get_zero_shot_classifier():
    global _zero_shot_classifier
    if _zero_shot_classifier is None:
        from transformers import pipeline

        print(f"[model_registry] loading zero-shot model: {ZERO_SHOT_MODEL_NAME} (first call only)")
        _zero_shot_classifier = pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL_NAME)
    return _zero_shot_classifier


def run_zero_shot(text: str, labels: dict[str, str]) -> dict:
    """
    labels: {short_name: full_nli_hypothesis_sentence}
    Returns {label, top_score, second_label, second_score, margin, all_scores}.
    """
    classifier = get_zero_shot_classifier()
    names = list(labels.keys())
    hypotheses = [labels[n] for n in names]
    hyp_to_name = {labels[n]: n for n in names}

    # hypothesis_template="{}" is required: our "labels" are already full
    # NLI hypothesis sentences, not short label words -- the pipeline's
    # default template would wrap them ungrammatically and degrade accuracy.
    result = classifier(text, hypotheses, hypothesis_template="{}", multi_label=False)

    ranked = list(zip(result["labels"], result["scores"]))
    top_hyp, top_score = ranked[0]
    second_hyp, second_score = ranked[1] if len(ranked) > 1 else (top_hyp, 0.0)

    return {
        "label": hyp_to_name[top_hyp],
        "top_score": top_score,
        "second_label": hyp_to_name[second_hyp],
        "second_score": second_score,
        "margin": top_score - second_score,
        "all_scores": {hyp_to_name[h]: s for h, s in ranked},
    }


def nli_confidence(top_score: float, margin: float) -> float:
    """
    Zero-shot NLI scores are a softmax over the hypotheses we supplied, not a
    calibrated probability (see model docstrings throughout this package).
    We discount top_score by how decisively it beat the runner-up: a high
    score with a thin margin is much less trustworthy than the same score
    with a wide margin. This is a documented V1 heuristic, not a calibrated
    probability -- revisit once labelled data exists to calibrate against.
    """
    return round(top_score * min(1.0, 0.5 + margin), 4)
