"""
The project's LLM client -- the only module that talks to an LLM, so it can be
swapped, mocked, or disabled without touching any stage's control flow.

Three kinds of call go through it:

  relevance -- Step 1: resolves an *ambiguous* rule-gate result (zero RCM
               keyword hits) into relevant / not relevant.
  semantic  -- Step 2 (Semantic Problem & Intent Analysis): one call per
               relevant post returning problem evidence, first-person,
               speaker, stance, seeking level, an evidence quote and
               component confidences.
  legacy    -- the old Step 4 stance/seeking fallback, still used by the
               legacy stages that run when the semantic call fails.

The provider is chosen by LLM_PROVIDER in config.py:

  ollama   -- local Ollama server (OLLAMA_HOST / OLLAMA_MODEL, default llama3.1)
  bedrock  -- Amazon Nova 2 Lite via the Bedrock Converse API
  none     -- LLM disabled (every call returns None)

Only the selected provider's client is loaded: boto3 is imported lazily, so an
Ollama or disabled run works fully offline from AWS. On any request/parse
failure every public function returns None and the caller falls back rather
than crashing the pipeline. CALL_STATS counts attempts per run (and
CALL_STATS_BY_KIND splits them by call kind) so an experiment can report which
LLM actually answered, how often, and how often it failed.

Both providers force structured output against the same JSON schema -- Ollama
through `format=`, Bedrock through a forced tool call. Responses are validated
again here (enums, booleans, numeric confidences) because a schema-constrained
model can still return out-of-range or missing values.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional, get_args

import requests

from app.config import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    LLM_PROVIDER,
    OLLAMA_HOST,
    OLLAMA_MODEL,
)
from app.schemas.analysis import ContentStance, SeekingLevel, SpeakerType

PROVIDER = LLM_PROVIDER if LLM_PROVIDER in {"ollama", "bedrock", "none"} else "none"

OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"

if PROVIDER == "ollama":
    LLM_FALLBACK_ENABLED = bool(OLLAMA_MODEL)
    ACTIVE_MODEL = OLLAMA_MODEL
elif PROVIDER == "bedrock":
    # boto3 reads the Bedrock API key from AWS_BEARER_TOKEN_BEDROCK itself
    # (config.py loads the repo-root .env into the environment first).
    LLM_FALLBACK_ENABLED = bool(BEDROCK_MODEL_ID and os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
    ACTIVE_MODEL = BEDROCK_MODEL_ID
else:
    LLM_FALLBACK_ENABLED = False
    ACTIVE_MODEL = None

OLLAMA_TIMEOUT_S = 120  # first call after Ollama starts pays a one-time model-load cost
BEDROCK_TIMEOUT_S = 60
MAX_OUTPUT_TOKENS = 200
SEMANTIC_MAX_OUTPUT_TOKENS = 400
TOOL_NAME = "record_classification"

# Ollama's default context (2048 tokens) is too small for a long post plus a
# parent post plus the instructions; the relevance/semantic calls ask for a
# larger window and cap the text they send.
OLLAMA_NUM_CTX = 8192
MAX_POST_CHARS = 8000
MAX_PARENT_CHARS = 3000

CALL_STATS = {"attempted": 0, "succeeded": 0, "failed": 0}
CALL_KINDS = ("relevance", "semantic", "legacy")
CALL_STATS_BY_KIND = {k: {"attempted": 0, "succeeded": 0, "failed": 0} for k in CALL_KINDS}

STANCE_LABELS = list(get_args(ContentStance))
SEEKING_LABELS = list(get_args(SeekingLevel))
SPEAKER_LABELS = list(get_args(SpeakerType))
# JSON-schema enums with a null member are unreliable across providers, so
# "no seeking level" travels as the string "none" and is mapped back to None.
SEEKING_NONE = "none"

STANCE_SYSTEM_PROMPT = (
    "You are classifying a short social-media/forum post from the medical "
    "billing / revenue cycle management (RCM) domain. Decide the author's "
    "content stance:\n"
    "- seeking: the author is asking a question or requesting help, advice, or a solution.\n"
    "- supplying: the author is providing information, advice, or a solution to others.\n"
    "- neutral: the author is simply describing a situation without asking for or offering help.\n"
    "- mixed: the post both asks for help and offers information/advice.\n"
    "Answer with a label (one of the four values above) and a confidence "
    "between 0 and 1 reflecting your certainty."
)

SEEKING_SYSTEM_PROMPT = (
    "You are classifying a short social-media/forum post from the medical "
    "billing / revenue cycle management (RCM) domain, for a practice/staff "
    "member who is seeking something. Decide the seeking level:\n"
    "- L0: describing a problem or venting, with no explicit request for help.\n"
    "- L1: asking for help, information, or advice.\n"
    "- L2: looking for a solution, workaround, or better way to solve the problem.\n"
    "- L3: actively looking for a vendor, service, provider, or external solution.\n"
    'Answer with a label (one of "L0", "L1", "L2", "L3") and a confidence '
    "between 0 and 1 reflecting your certainty."
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _response_schema(labels: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels},
            "confidence": {"type": "number"},
        },
        "required": ["label", "confidence"],
    }


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _confidence(v: Any) -> float:
    """Clamped to [0, 1]. LLM confidences are self-reported, not calibrated --
    Step 5 aggregates them; nothing treats them as probabilities."""
    return round(min(1.0, max(0.0, float(v))), 4)


def _unexpected(parsed: Any) -> None:
    print(f"[llm_fallback] {PROVIDER} returned unexpected shape: {parsed!r}")
    return None


def _validated(parsed: Any, labels: list[str]) -> Optional[dict]:
    if not isinstance(parsed, dict):
        return _unexpected(parsed)
    label = parsed.get("label")
    confidence = parsed.get("confidence")
    if label not in labels or not _is_number(confidence):
        return _unexpected(parsed)
    return {"label": label, "confidence": round(float(confidence), 4)}


def _label_validator(labels: list[str]) -> Callable[[Any], Optional[dict]]:
    return lambda parsed: _validated(parsed, labels)


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
def ollama_model_available(model: str | None = None, timeout_s: float = 5.0) -> bool:
    """True when the Ollama server is reachable and has `model` pulled.

    Used as a preflight so an experiment fails loudly instead of silently
    running with every LLM call falling back.
    """
    model = model or OLLAMA_MODEL
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=timeout_s)
        resp.raise_for_status()
        names = {m.get("name", "") for m in resp.json().get("models", [])}
    except (requests.RequestException, ValueError):
        return False
    # "llama3.1" is stored as "llama3.1:latest"
    return model in names or f"{model}:latest" in names


def _call_ollama(
    system_prompt: str,
    text: str,
    schema: dict,
    validate: Callable[[Any], Optional[dict]],
    max_tokens: int,
    large_context: bool,
) -> Optional[dict]:
    options: dict[str, Any] = {"temperature": 0.0}
    if large_context:
        options.update(num_ctx=OLLAMA_NUM_CTX, num_predict=max_tokens)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "format": schema,
        "stream": False,
        "options": options,
    }
    try:
        resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=OLLAMA_TIMEOUT_S)
        resp.raise_for_status()
        parsed = json.loads(resp.json()["message"]["content"])
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[llm_fallback] Ollama call failed, caller falls back: {exc!r}")
        return None
    return validate(parsed)


# ---------------------------------------------------------------------------
# Bedrock (imported lazily -- never loaded unless PROVIDER == "bedrock")
# ---------------------------------------------------------------------------
_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        from botocore.config import Config

        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=Config(
                read_timeout=BEDROCK_TIMEOUT_S,
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )
    return _bedrock_client


def _call_bedrock(
    system_prompt: str,
    text: str,
    schema: dict,
    validate: Callable[[Any], Optional[dict]],
    max_tokens: int,
) -> Optional[dict]:
    from botocore.exceptions import BotoCoreError, ClientError

    tool = {
        "toolSpec": {
            "name": TOOL_NAME,
            "description": "Record the classification for this post.",
            "inputSchema": {"json": schema},
        }
    }
    try:
        resp = _get_client().converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": text}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": max_tokens},
            toolConfig={"tools": [tool], "toolChoice": {"tool": {"name": TOOL_NAME}}},
        )
        blocks = resp["output"]["message"]["content"]
        parsed = next(b["toolUse"]["input"] for b in blocks if "toolUse" in b)
    except (BotoCoreError, ClientError, KeyError, TypeError, StopIteration) as exc:
        print(f"[llm_fallback] Bedrock call failed, caller falls back: {exc!r}")
        return None
    return validate(parsed)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def _call_llm(
    system_prompt: str,
    text: str,
    schema: dict,
    validate: Callable[[Any], Optional[dict]],
    kind: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    large_context: bool = False,
) -> Optional[dict]:
    if not LLM_FALLBACK_ENABLED:
        return None
    CALL_STATS["attempted"] += 1
    CALL_STATS_BY_KIND[kind]["attempted"] += 1
    if PROVIDER == "ollama":
        result = _call_ollama(system_prompt, text, schema, validate, max_tokens, large_context)
    elif PROVIDER == "bedrock":
        result = _call_bedrock(system_prompt, text, schema, validate, max_tokens)
    else:
        result = None
    outcome = "succeeded" if result is not None else "failed"
    CALL_STATS[outcome] += 1
    CALL_STATS_BY_KIND[kind][outcome] += 1
    return result


def reset_call_stats() -> None:
    for key in CALL_STATS:
        CALL_STATS[key] = 0
    for stats in CALL_STATS_BY_KIND.values():
        for key in stats:
            stats[key] = 0


# ---------------------------------------------------------------------------
# Legacy Step 4 fallback (stance / seeking only)
# ---------------------------------------------------------------------------
def classify_stance_llm(text: str) -> Optional[dict]:
    """Returns {"label": ContentStance, "confidence": float} or None (disabled/failed)."""
    return _call_llm(STANCE_SYSTEM_PROMPT, text, _response_schema(STANCE_LABELS),
                     _label_validator(STANCE_LABELS), "legacy")


def classify_seeking_llm(text: str) -> Optional[dict]:
    """Returns {"label": SeekingLevel, "confidence": float} or None (disabled/failed)."""
    return _call_llm(SEEKING_SYSTEM_PROMPT, text, _response_schema(SEEKING_LABELS),
                     _label_validator(SEEKING_LABELS), "legacy")


# ---------------------------------------------------------------------------
# Shared input framing: the current post and its parent are always sent as
# separate, labelled sections -- never concatenated -- so the model classifies
# the current author and quotes only them.
# ---------------------------------------------------------------------------
def _clip(text: str | None, limit: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else t[:limit] + " [...truncated]"


def build_user_message(post_text: str, parent_text: str | None, source: str | None) -> str:
    parent = _clip(parent_text, MAX_PARENT_CHARS)
    return (
        f"SOURCE: {source or 'unknown'}\n\n"
        "PARENT POST (context only -- do NOT classify it and do NOT quote it):\n"
        f"<<<\n{parent or '(none -- the current post is not a reply)'}\n>>>\n\n"
        "CURRENT POST (classify this author's post):\n"
        f"<<<\n{_clip(post_text, MAX_POST_CHARS)}\n>>>"
    )


# ---------------------------------------------------------------------------
# Step 1 -- ambiguous relevance resolution
# ---------------------------------------------------------------------------
RELEVANCE_SYSTEM_PROMPT = (
    "You screen social-media/forum posts for a dashboard about medical billing and "
    "healthcare revenue cycle management (RCM). Decide whether the CURRENT POST is "
    "relevant to that domain: medical billing, medical coding, claims, denials, "
    "insurance reimbursement, payer policy, prior authorization, eligibility, "
    "payment posting / ERAs, or healthcare practice revenue operations -- whether "
    "as an operational issue, a question, a career topic, or general discussion. "
    "Use the parent post only to understand what the current post refers to. "
    "Posts about unrelated topics (general health, personal life, non-healthcare "
    "billing, generic software) are not relevant.\n"
    'Return JSON: {"relevant": true or false, "confidence": number between 0 and 1}. '
    "No explanation."
)

RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {"relevant": {"type": "boolean"}, "confidence": {"type": "number"}},
    "required": ["relevant", "confidence"],
}


def _validate_relevance(parsed: Any) -> Optional[dict]:
    if (
        not isinstance(parsed, dict)
        or not isinstance(parsed.get("relevant"), bool)
        or not _is_number(parsed.get("confidence"))
    ):
        return _unexpected(parsed)
    return {"relevant": parsed["relevant"], "confidence": _confidence(parsed["confidence"])}


def classify_relevance_llm(
    post_text: str, parent_text: str | None = None, source: str | None = None
) -> Optional[dict]:
    """Returns {"relevant": bool, "confidence": float} or None (disabled/failed)."""
    return _call_llm(RELEVANCE_SYSTEM_PROMPT, build_user_message(post_text, parent_text, source),
                     RELEVANCE_SCHEMA, _validate_relevance, "relevance", large_context=True)


# ---------------------------------------------------------------------------
# Step 2 -- Semantic Problem & Intent Analysis
# ---------------------------------------------------------------------------
SEMANTIC_SYSTEM_PROMPT = (
    "You analyze one social-media/forum post from the medical billing / healthcare "
    "revenue cycle management (RCM) domain. Classify ONLY the CURRENT POST's author. "
    "The parent post, if any, is context for understanding a reply -- never attribute "
    "the parent's problem, experience or intent to the current author unless the "
    "current post itself says it applies to them (e.g. 'same here', 'we have this too').\n\n"
    "Fields:\n"
    "- problem_evidence: the current post describes or clearly refers to a real "
    "operational problem (denials, authorization, reimbursement or payment delays, "
    "documentation / medical necessity, claim processing, payer policy, billing "
    "workflow). False for education, definitions, vendor promotion, recruiting, "
    "generic industry news/discussion or purely informational content.\n"
    "- problem_current: the problem is happening now, not historical or hypothetical.\n"
    "- problem_recurring: the problem is repeated or ongoing, not a one-off.\n"
    "- first_person: the author describes their OWN (or their organization's) "
    "experience ('we keep getting denials'). False for third-party or general "
    "statements ('many practices get denials'). Discussing a problem is not enough.\n"
    "- operational_impact: the post states an effect on operations, cash flow, "
    "workload or patient access.\n"
    "- speaker_type: vendor (selling or promoting a product/service), payer_side "
    "(works for an insurer/payer), practice_side (provider, biller, coder or staff at "
    "a practice/facility), patient, educator_media (teaching, news, commentary), "
    "unknown (not enough evidence -- do not infer from topic alone).\n"
    "- content_stance: seeking (asks for help/information/solution), supplying "
    "(gives information/advice/solution), neutral (describes without asking or "
    "offering), mixed (both asks and offers).\n"
    "- seeking_level: L0 = describing/venting with no explicit request; L1 = asking "
    "for help, information or advice; L2 = looking for a better way, workaround or "
    "process fix; L3 = looking for a vendor, service or external solution; "
    '"none" when the author is only supplying information.\n'
    "- evidence_quote: one short, exact, verbatim excerpt (at most two sentences) "
    "copied from the CURRENT POST that best supports the classification. Never "
    "quote the parent post.\n"
    "- problem/speaker/stance/seeking_confidence: your certainty for that field, 0 to 1.\n\n"
    "Return only the JSON object. No reasoning or explanation."
)

_BOOL_FIELDS = (
    "problem_evidence", "problem_current", "problem_recurring",
    "first_person", "operational_impact",
)
_CONFIDENCE_FIELDS = (
    "problem_confidence", "speaker_confidence", "stance_confidence", "seeking_confidence",
)

SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        **{f: {"type": "boolean"} for f in _BOOL_FIELDS},
        "speaker_type": {"type": "string", "enum": SPEAKER_LABELS},
        "content_stance": {"type": "string", "enum": STANCE_LABELS},
        "seeking_level": {"type": "string", "enum": SEEKING_LABELS + [SEEKING_NONE]},
        "evidence_quote": {"type": "string"},
        **{f: {"type": "number"} for f in _CONFIDENCE_FIELDS},
    },
    "required": [
        *_BOOL_FIELDS, "speaker_type", "content_stance", "seeking_level",
        "evidence_quote", *_CONFIDENCE_FIELDS,
    ],
}


def _validate_semantic(parsed: Any) -> Optional[dict]:
    """Structural validation only. Checks that depend on the post itself (is
    the quote really from the current post?) live in step2_semantic.py."""
    if not isinstance(parsed, dict):
        return _unexpected(parsed)
    if not all(isinstance(parsed.get(f), bool) for f in _BOOL_FIELDS):
        return _unexpected(parsed)
    if not all(_is_number(parsed.get(f)) for f in _CONFIDENCE_FIELDS):
        return _unexpected(parsed)
    if (
        parsed.get("speaker_type") not in SPEAKER_LABELS
        or parsed.get("content_stance") not in STANCE_LABELS
        or parsed.get("seeking_level") not in SEEKING_LABELS + [SEEKING_NONE]
    ):
        return _unexpected(parsed)
    quote = parsed.get("evidence_quote")
    result: dict[str, Any] = {f: parsed[f] for f in _BOOL_FIELDS}
    result.update({f: _confidence(parsed[f]) for f in _CONFIDENCE_FIELDS})
    result.update(
        speaker_type=parsed["speaker_type"],
        content_stance=parsed["content_stance"],
        seeking_level=None if parsed["seeking_level"] == SEEKING_NONE else parsed["seeking_level"],
        evidence_quote=quote.strip() if isinstance(quote, str) and quote.strip() else None,
    )
    return result


def analyze_semantics_llm(
    post_text: str, parent_text: str | None = None, source: str | None = None
) -> Optional[dict]:
    """One call returning every Step 2 field (see SEMANTIC_SCHEMA), validated,
    or None when the LLM is disabled, unreachable, or returned unusable output."""
    return _call_llm(SEMANTIC_SYSTEM_PROMPT, build_user_message(post_text, parent_text, source),
                     SEMANTIC_SCHEMA, _validate_semantic, "semantic",
                     max_tokens=SEMANTIC_MAX_OUTPUT_TOKENS, large_context=True)
