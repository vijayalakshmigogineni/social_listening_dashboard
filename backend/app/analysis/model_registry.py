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

# A free Hugging Face Space sleeps when idle and takes a minute or two to
# wake, so the remote call waits long and retries on 503/connection errors.
_REMOTE_TIMEOUT_S = 180
_REMOTE_ATTEMPTS = 3
_REMOTE_RETRY_WAIT_S = 20


def get_zero_shot_classifier():
    global _zero_shot_classifier
    if _zero_shot_classifier is None:
        from transformers import pipeline

        print(f"[model_registry] loading zero-shot model: {ZERO_SHOT_MODEL_NAME} (first call only)")
        _zero_shot_classifier = pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL_NAME)
    return _zero_shot_classifier


def _classify_remote(text: str, hypotheses: list[str]) -> dict:
    import time

    import requests

    from app.config import ZERO_SHOT_API_KEY, ZERO_SHOT_API_URL

    headers = {"Authorization": f"Bearer {ZERO_SHOT_API_KEY}"} if ZERO_SHOT_API_KEY else {}
    for attempt in range(1, _REMOTE_ATTEMPTS + 1):
        try:
            resp = requests.post(
                f"{ZERO_SHOT_API_URL}/classify",
                json={"text": text, "hypotheses": hypotheses},
                headers=headers,
                timeout=_REMOTE_TIMEOUT_S,
            )
            if resp.status_code != 503:
                resp.raise_for_status()
                return resp.json()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == _REMOTE_ATTEMPTS:
                raise
        if attempt == _REMOTE_ATTEMPTS:
            resp.raise_for_status()
        print(f"[model_registry] zero-shot service not ready, retrying ({attempt}/{_REMOTE_ATTEMPTS})")
        time.sleep(_REMOTE_RETRY_WAIT_S)


def _classify(text: str, hypotheses: list[str]) -> dict:
    """Returns the pipeline's {labels, scores}, ranked, locally or via the Space."""
    from app.config import ZERO_SHOT_API_URL

    if ZERO_SHOT_API_URL:
        return _classify_remote(text, hypotheses)
    # hypothesis_template="{}" is required: our "labels" are already full
    # NLI hypothesis sentences, not short label words -- the pipeline's
    # default template would wrap them ungrammatically and degrade accuracy.
    return get_zero_shot_classifier()(text, hypotheses, hypothesis_template="{}", multi_label=False)


def run_zero_shot(text: str, labels: dict[str, str]) -> dict:
    """
    labels: {short_name: full_nli_hypothesis_sentence}
    Returns {label, top_score, second_label, second_score, margin, all_scores}.
    """
    names = list(labels.keys())
    hypotheses = [labels[n] for n in names]
    hyp_to_name = {labels[n]: n for n in names}

    result = _classify(text, hypotheses)

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
