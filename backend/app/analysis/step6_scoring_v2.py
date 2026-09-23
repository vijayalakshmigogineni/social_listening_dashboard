"""
Step 6/7 -- Scoring, v2.

Derived bottom-up from a blind human re-scoring of the 167-post gold set
(backend/data/gold/). Every term here was measured for two things before it
earned a weight: how often it is actually observable in real public posts, and
how much more often it appears in high-value posts than in low-value ones.
Signals that were theoretically attractive but rarely observable -- explicit
financial impact (4% of posts), practice identity (6%) -- carry no weight.

Differences from v1 that matter:

  * No recency multiplier. A denial that has not been paid does not become
    less of a problem because the thread is old, and v1's version could zero
    a post outright over an unparsed date.
  * No confidence multiplier. Classifier uncertainty is reported, not baked
    into the score.
  * Relevance is a graded floor (0.35), never a hard zero-gate.
  * Vendor/self-promotional content is penalised rather than ignored.
  * Quoted parent text is stripped before scoring, so a forum reply is not
    credited with the problem the person above them described.

Unlike v1 this stage DOES read the text, deliberately: the signals it needs
(first-person voice, denial language, escalation) are surface features that
Steps 1-5 do not expose. It reads only `seeking_level` from the earlier
stages.

Weights are provisional and fitted against model-proposed labels awaiting
human validation -- treat them as an ordering, not a measurement.
"""

from __future__ import annotations

import re

from app.schemas.analysis import SCORING_VERSION_V2, ScoreBreakdownV2

# ---------------------------------------------------------------------------
# Forum replies embed the full parent post ("X said: ... Click to expand...").
# Scoring that quote credits the replier with the original author's problem --
# it was the second-highest-scoring post under v1.
# ---------------------------------------------------------------------------
QUOTE_BLOCK_RE = re.compile(r"^.*?said:\n.*?Click to expand\.\.\.\n?", re.S)


def strip_quoted_parent(text: str | None) -> str:
    t = text or ""
    stripped = QUOTE_BLOCK_RE.sub("", t)
    # A reply that is *only* a quote keeps its original text rather than
    # becoming empty.
    return stripped if stripped.strip() else t


SIGNALS: dict[str, re.Pattern[str]] = {
    "payer": re.compile(
        r"\b(medicare|medicaid|aetna|cigna|humana|bcbs|blue cross|unitedhealth|uhc|umr|"
        r"molina|noridian|novitas|palmetto|wps|caresource|tricare|medi-cal|wellpoint|"
        r"cgs|waystar)\b", re.I),
    "code": re.compile(r"\b(\d{5}|[A-Z]\d{4})\b"),
    "denial": re.compile(
        r"\b(denial|denials|denied|denying|deny|rejected|rejection|underpaid|"
        r"not getting paid|non-?covered|not be(?:ing)? paid|"
        r"(?:will|would|do|does|did)(?: not|n.t) pay|lesser value)\b", re.I),
    "firstperson": re.compile(
        r"\b(we are|we have|we bill|we (?:were|do|did|get|got|see|seen|receive|received|"
        r"use|used|had|keep)|our (?:claims?|practice|office|provider|clinic|surgeon|"
        r"patients?|software|team|panels?|facility|charges?)|i am (?:receiving|having)|"
        r"i work (?:for|in|with)|i have a (?:provider|surgeon|physician|client)|"
        r"my (?:provider|surgeon|practice|office|facility|claims?))\b", re.I),
    # Domain anchor: without RCM vocabulary, a word like "denial" is not a
    # claim denial. This is what stops a couples-therapy post scoring as the
    # top Reddit result, which is exactly what happened under v1.
    "domain": re.compile(
        r"\b(claim|billing|billed|bill|cpt|hcpcs|icd|modifier|payer|payor|reimburs|"
        r"coding|coder|code|deductible|coinsurance|copay|fee schedule|clearinghouse|"
        r"remittance|eob|appeal|authoriz|pre-?cert|ncci|lcd|ncd|revenue cycle|"
        r"accounts receivable|superbill|cms-?1500|ub-?04|medicare|medicaid|rvu|pos\b|"
        r"place of service)", re.I),
    # Operational distress: a queue nobody is working is the strongest buying
    # trigger in the corpus, and the only term that catches its one direct lead.
    "backlog": re.compile(
        r"(not (?:been )?(?:worked|touched)|unworked|backlog|sitting in|aging|piling up|"
        r"behind on|no one (?:is|has been) working|for (?:approximately |about )?\d+ months|"
        r"short.?staffed|understaffed|no one to ask|"
        r"left all .{0,30}up to the individual)", re.I),
    "ask": re.compile(
        r"(any (?:help|input|suggestions?|advice|insight|guidance|one else)|has anyone|"
        r"does anyone|anyone else|can someone|would (?:appreciate|be willing)|looking for|"
        r"what (?:are|do) you (?:all )?us|how (?:do|are) you|greatly appreciated|"
        r"appreciate any)", re.I),
    # The payer channel has already failed them -- rare (7%) but nearly always
    # decisive when present.
    "escalation": re.compile(
        r"(when (?:she|he|we|i) call|call(?:ed|ing)? (?:and|the payer|them)|"
        r"not been helpful|no response|at a loss|(?:cannot|can.t) keep up|maddening|"
        r"100\+? websites|still (?:would )?appreciate|no one to ask|"
        r"does not make sense|do not make sense|nonsense|has not been helpful|"
        r"told (?:us|me|her|him) (?:that|we|to))", re.I),
    "recurring": re.compile(
        r"\b(influx|a lot of|a bunch of|repeatedly|constantly|"
        r"keeps? (?:getting|denying|coming)|every (?:time|case|claim|single)|"
        r"for (?:the past )?(?:few |several |a few )?(?:months|weeks|years)|"
        r"recently (?:seen|noticed|started)|continue to|still (?:getting|denying|denied)|"
        r"all of the|no longer)\b", re.I),
    "noise": re.compile(
        r"(#hiring|we are hiring|apply (?:here|directly)|share (?:your|with someone)|"
        r"dm me|comment .lab ar.|read the full (?:report|article)|https?://lnkd\.in|"
        r"interested candidates|expected ctc|salary:|\U0001F4E7|our free guide)", re.I),
    "offdomain": re.compile(
        r"\b(procurement|biogas|earthworks|weathering|xenon|donor|fundrais|charity|"
        r"pupils|curriculum|survey beacons|structural engineering|climate)\b", re.I),
}

# Additive weights, ordered to mirror the measured Group-A/Group-C lift.
WEIGHTS = {
    "denial": 22,
    "backlog": 16,
    "payer": 12,
    "escalation": 10,
    "recurring": 10,
    "code": 6,
}
FIRST_PERSON_WEIGHT = 12

# Intent by seeking level. L1 and L2 deliberately share a tier -- the gold set
# does not show L2 to be materially more valuable than L1 -- but seeking_level
# is still persisted separately, so the distinction is never lost from the data.
INTENT_BY_LEVEL = {"L3": 20, "L2": 15, "L1": 15, "L0": 10}
INTENT_DEFAULT = 10

DENIAL_FIRST_PERSON_BONUS = 10.0  # the corpus signature
RELEVANCE_FLOOR = 0.35            # graded, never a hard zero-gate
OFF_DOMAIN_FACTOR = 0.10          # no RCM anchor vocabulary at all
COMMENTARY_FACTOR = 0.55          # talking *about* the industry, not owning a problem
NOISE_FACTOR = 0.35               # vendor / recruitment / self-promotion
OFFDOMAIN_PENALTY = 0.15          # a different industry entirely
SCORE_CAP = 95.0


def intent_strength(seeking_level: str | None) -> float:
    return float(INTENT_BY_LEVEL.get(seeking_level or "", INTENT_DEFAULT))


def score_record_v2(text: str, seeking_level: str | None) -> ScoreBreakdownV2:
    own_text = strip_quoted_parent(text)
    hit = {name: bool(rx.search(own_text)) for name, rx in SIGNALS.items()}

    problem_strength = float(
        WEIGHTS["denial"] * hit["denial"]
        + WEIGHTS["backlog"] * hit["backlog"]
        + WEIGHTS["escalation"] * hit["escalation"]
        + WEIGHTS["recurring"] * hit["recurring"]
    )
    identity = float(FIRST_PERSON_WEIGHT * hit["firstperson"])
    specificity = float(WEIGHTS["payer"] * hit["payer"] + WEIGHTS["code"] * hit["code"])
    intent = intent_strength(seeking_level)

    interaction = DENIAL_FIRST_PERSON_BONUS if (hit["denial"] and hit["firstperson"]) else 0.0
    base_score = problem_strength + identity + specificity + intent + interaction

    relevance_factor = 1.0 if (hit["code"] or hit["payer"] or hit["denial"]) else RELEVANCE_FLOOR
    domain_factor = 1.0 if hit["domain"] else OFF_DOMAIN_FACTOR
    commentary_factor = (
        COMMENTARY_FACTOR if (not hit["firstperson"] and not hit["backlog"]) else 1.0
    )
    noise_factor = NOISE_FACTOR if hit["noise"] else 1.0
    offdomain_factor = OFFDOMAIN_PENALTY if hit["offdomain"] else 1.0

    penalised = base_score * domain_factor * commentary_factor * noise_factor * offdomain_factor
    final_score = round(min(SCORE_CAP, penalised * relevance_factor), 4)

    return ScoreBreakdownV2(
        problem_strength=problem_strength,
        identity=identity,
        specificity=specificity,
        intent_strength=intent,
        interaction_bonus=interaction,
        base_score=round(base_score, 4),
        relevance_factor=relevance_factor,
        domain_factor=domain_factor,
        commentary_factor=commentary_factor,
        noise_factor=noise_factor,
        offdomain_factor=offdomain_factor,
        final_score=final_score,
        signals=sorted(name for name, fired in hit.items() if fired),
    )


__all__ = ["score_record_v2", "strip_quoted_parent", "SCORING_VERSION_V2"]
