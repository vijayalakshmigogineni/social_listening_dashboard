"""
Step 4 LLM fallback -- content_stance and seeking_level only.

Called exclusively when zero-shot NLI (model_registry.run_zero_shot) is
ambiguous (see step4_speaker_stance_seeking.py's confidence/margin gate).
Never called for every post, and never used for speaker_type.

Isolated on purpose: this is the only module in the project that talks to an
LLM (a local Ollama server), so it can be swapped, mocked, or disabled
without touching Step 4's control flow. LLM_FALLBACK_ENABLED is a single
switch -- with OLLAMA_MODEL unset, or on any request/parse failure (including
Ollama not running locally), both functions return None and the caller keeps
the NLI result rather than crashing the pipeline.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

from app.config import OLLAMA_HOST, OLLAMA_MODEL

OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"

LLM_FALLBACK_ENABLED = bool(OLLAMA_MODEL)

REQUEST_TIMEOUT_S = 120  # first call after Ollama starts pays a one-time model-load cost

STANCE_LABELS = ["seeking", "supplying", "neutral", "mixed"]
SEEKING_LABELS = ["L0", "L1", "L2", "L3"]

STANCE_SYSTEM_PROMPT = (
    "You are classifying a short social-media/forum post from the medical "
    "billing / revenue cycle management (RCM) domain. Decide the author's "
    "content stance:\n"
    "- seeking: the author is asking a question or requesting help, advice, or a solution.\n"
    "- supplying: the author is providing information, advice, or a solution to others.\n"
    "- neutral: the author is simply describing a situation without asking for or offering help.\n"
    "- mixed: the post both asks for help and offers information/advice.\n"
    'Respond with strict JSON: {"label": one of the four values above, '
    '"confidence": a number between 0 and 1 reflecting your certainty}.'
)

SEEKING_SYSTEM_PROMPT = (
    "You are classifying a short social-media/forum post from the medical "
    "billing / revenue cycle management (RCM) domain, for a practice/staff "
    "member who is seeking something. Decide the seeking level:\n"
    "- L0: describing a problem or venting, with no explicit request for help.\n"
    "- L1: asking for help, information, or advice.\n"
    "- L2: looking for a solution, workaround, or better way to solve the problem.\n"
    "- L3: actively looking for a vendor, service, provider, or external solution.\n"
    'Respond with strict JSON: {"label": one of "L0", "L1", "L2", "L3", '
    '"confidence": a number between 0 and 1 reflecting your certainty}.'
)


def _response_schema(labels: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels},
            "confidence": {"type": "number"},
        },
        "required": ["label", "confidence"],
    }


def _call_ollama(system_prompt: str, text: str, labels: list[str]) -> Optional[dict]:
    if not LLM_FALLBACK_ENABLED:
        return None

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "format": _response_schema(labels),
        "stream": False,
        "options": {"temperature": 0.0},
    }

    try:
        resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        raw_text = resp.json()["message"]["content"]
        parsed = json.loads(raw_text)
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        print(f"[llm_fallback] Ollama call failed, keeping NLI result: {exc}")
        return None

    label = parsed.get("label")
    confidence = parsed.get("confidence")
    if label not in labels or not isinstance(confidence, (int, float)):
        print(f"[llm_fallback] Ollama returned unexpected shape: {parsed!r}")
        return None

    return {"label": label, "confidence": round(float(confidence), 4)}


def classify_stance_llm(text: str) -> Optional[dict]:
    """Returns {"label": ContentStance, "confidence": float} or None (disabled/failed)."""
    return _call_ollama(STANCE_SYSTEM_PROMPT, text, STANCE_LABELS)


def classify_seeking_llm(text: str) -> Optional[dict]:
    """Returns {"label": SeekingLevel, "confidence": float} or None (disabled/failed)."""
    return _call_ollama(SEEKING_SYSTEM_PROMPT, text, SEEKING_LABELS)
