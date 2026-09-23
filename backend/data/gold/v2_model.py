"""SLD scoring v2 -- candidate scorer evaluated against the 167-post gold set.

Built only from signals shown to be observable and discriminative in the audit:
every term is a regex or a structural fact already present in normalized_items.
No new model, no new pipeline stage.

Two variants are scored side by side so the effect of the requested weight
changes is measurable rather than asserted:

  proposed  -- the scorer as it came out of the audit
  modified  -- two requested changes:
                 1. first-person practice voice 18 -> 12
                 2. flat 12-point ask term -> level-based intent,
                    L0 = 10, L1/L2 = 15, L3 = 20
               L1 and L2 share a scoring tier but stay distinct as metadata.

The 0.35 relevance floor is retained in BOTH variants -- relevance is a graded
multiplier, never a hard zero-gate.

Self-contained: reads post text and v1 scores directly from sld.db (read-only)
and the human labels from sld_167_gold_labels.json in this directory.

    cd backend && python data/gold/v2_model.py
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "sld.db"

# --- Quote stripping: AAPC replies embed the full parent post. Scoring the
# --- quote credits the replier with the original author's problem.
QUOTE = re.compile(r"^.*?said:\n.*?Click to expand\.\.\.\n?", re.S)


def own_text(text: str | None) -> str:
    t = text or ""
    stripped = QUOTE.sub("", t)
    return stripped if stripped.strip() else t


RX = {
 "payer": re.compile(r"\b(medicare|medicaid|aetna|cigna|humana|bcbs|blue cross|unitedhealth|uhc|umr|molina|noridian|novitas|palmetto|wps|caresource|tricare|medi-cal|wellpoint|cgs|waystar)\b", re.I),
 "code": re.compile(r"\b(\d{5}|[A-Z]\d{4})\b"),
 "denial": re.compile(r"\b(denial|denials|denied|denying|deny|rejected|rejection|underpaid|not getting paid|non-?covered|not be(?:ing)? paid|(?:will|would|do|does|did)(?: not|n.t) pay|lesser value)\b", re.I),
 "firstperson": re.compile(r"\b(we are|we have|we bill|we bill|we (?:were|do|did|get|got|see|seen|receive|received|use|used|had|keep)|our (?:claims?|practice|office|provider|clinic|surgeon|patients?|software|team|panels?|facility|charges?)|i am (?:receiving|having)|i work (?:for|in|with)|i have a (?:provider|surgeon|physician|client)|my (?:provider|surgeon|practice|office|facility|claims?))\b", re.I),
 # Domain anchor: without one of these, a word like "denial" is not a claim denial.
 "domain": re.compile(r"\b(claim|billing|billed|bill|cpt|hcpcs|icd|modifier|payer|payor|reimburs|coding|coder|code|deductible|coinsurance|copay|fee schedule|clearinghouse|remittance|eob|appeal|authoriz|pre-?cert|ncci|lcd|ncd|revenue cycle|accounts receivable|superbill|cms-?1500|ub-?04|medicare|medicaid|rvu|pos\b|place of service)", re.I),
 # Operational distress: a queue nobody is working is the strongest buying trigger.
 "backlog": re.compile(r"(not (?:been )?(?:worked|touched)|unworked|backlog|sitting in|aging|piling up|behind on|no one (?:is|has been) working|for (?:approximately |about )?\d+ months|short.?staffed|understaffed|no one to ask|left all .{0,30}up to the individual)", re.I),
 "ask": re.compile(r"(any (?:help|input|suggestions?|advice|insight|guidance|one else)|has anyone|does anyone|anyone else|can someone|would (?:appreciate|be willing)|looking for|what (?:are|do) you (?:all )?us|how (?:do|are) you|greatly appreciated|appreciate any)", re.I),
 "escalation": re.compile(r"(when (?:she|he|we|i) call|call(?:ed|ing)? (?:and|the payer|them)|not been helpful|no response|at a loss|(?:cannot|can.t) keep up|maddening|100\+? websites|still (?:would )?appreciate|no one to ask|does not make sense|do not make sense|nonsense|has not been helpful|told (?:us|me|her|him) (?:that|we|to))", re.I),
 "recurring": re.compile(r"\b(influx|a lot of|a bunch of|repeatedly|constantly|keeps? (?:getting|denying|coming)|every (?:time|case|claim|single)|for (?:the past )?(?:few |several |a few )?(?:months|weeks|years)|recently (?:seen|noticed|started)|continue to|still (?:getting|denying|denied)|all of the|no longer)\b", re.I),
 "noise": re.compile(r"(#hiring|we are hiring|apply (?:here|directly)|share (?:your|with someone)|dm me|comment .lab ar.|read the full (?:report|article)|https?://lnkd\.in|interested candidates|expected ctc|salary:|\U0001F4E7|our free guide)", re.I),
 "offdomain": re.compile(r"\b(procurement|biogas|earthworks|weathering|xenon|donor|fundrais|charity|pupils|curriculum|survey beacons|structural engineering|climate)\b", re.I),
}

# Weights mirror the A/C lift ordering measured in the audit.
W = {"denial": 22, "payer": 12, "ask": 12,
     "escalation": 10, "recurring": 10, "code": 6, "backlog": 16}

FIRST_PERSON_WEIGHT = {"proposed": 18, "modified": 12}   # change 1: 18 -> 12
RELEVANCE_FLOOR = 0.35    # graded, never a hard zero-gate
OFF_DOMAIN_FACTOR = 0.10  # no RCM anchor term present at all
COMMENTARY_FACTOR = 0.55  # talking *about* the industry, not owning a problem
NOISE_FACTOR = 0.35
OFFDOMAIN_PENALTY = 0.15
SCORE_CAP = 95.0


def intent_score(level: str | None) -> int:
    """Change 2: level-based intent.

    L1 and L2 deliberately share a tier -- the gold set does not show L2 to be
    materially more valuable than L1 -- but the raw level is preserved as
    metadata so the distinction is never lost from the data.
    """
    if level == "L3":            # explicit vendor / service / outsourcing intent
        return 20
    if level in ("L1", "L2"):    # one scoring tier, two labels retained
        return 15
    return 10                    # L0 and unclassified alike


def score(text: str, seeking_level: str | None, variant: str) -> dict:
    t = own_text(text)
    hit = {k: bool(rx.search(t)) for k, rx in RX.items()}

    problem = (W["denial"] * hit["denial"] + W["recurring"] * hit["recurring"]
               + W["escalation"] * hit["escalation"] + W["backlog"] * hit["backlog"])
    identity = FIRST_PERSON_WEIGHT[variant] * hit["firstperson"]
    specificity = W["payer"] * hit["payer"] + W["code"] * hit["code"]
    intent = intent_score(seeking_level) if variant == "modified" else W["ask"] * hit["ask"]

    base = problem + identity + specificity + intent
    # Interaction: a first-person account of a denial is the corpus signature.
    if hit["denial"] and hit["firstperson"]:
        base += 10
    # Relevance as a graded multiplier, not a gate.
    rel = 1.0 if (hit["code"] or hit["payer"] or hit["denial"]) else RELEVANCE_FLOOR
    # Domain anchor: no RCM vocabulary at all means a word like "denial" is
    # not a claim denial. This is what separates a claims post from therapy.
    if not hit["domain"]:
        base *= OFF_DOMAIN_FACTOR
    # Commentary discount: with no first-person practice identity and no
    # operational distress, the post is somebody talking *about* the industry.
    if not hit["firstperson"] and not hit["backlog"]:
        base *= COMMENTARY_FACTOR
    if hit["noise"]:
        base *= NOISE_FACTOR
    if hit["offdomain"]:
        base *= OFFDOMAIN_PENALTY
    return {
        "score": round(min(SCORE_CAP, base * rel), 1),
        "intent_component": intent,
        **{f"hit_{k}": v for k, v in hit.items()},
    }


# --------------------------------------------------------------------------
# Load: human labels from disk, post text and v1 outputs from the DB.
# --------------------------------------------------------------------------
def load() -> list[dict]:
    gold = json.loads((HERE / "sld_167_gold_labels.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    db = {
        r["source_item_id"]: dict(r)
        for r in con.execute(
            "select n.source_item_id, n.title, n.text, a.final_score, "
            "a.seeking_level, a.rcm_relevant "
            "from normalized_items n join analysis_results a "
            "on a.source_item_id = n.source_item_id"
        )
    }
    con.close()

    rows = []
    for g in gold:
        d = db[g["source_item_id"]]
        text = f"{d['title'] or ''}\n{d['text'] or ''}".strip()
        human = g["human_opportunity_score"]
        prop = score(text, d["seeking_level"], "proposed")
        mod = score(text, d["seeking_level"], "modified")
        rows.append({
            **g,
            "group": "A" if human >= 55 else ("B" if human >= 30 else "C"),
            "human": human,
            "v1": round(d["final_score"], 1),
            "v2_proposed": prop["score"],
            "v2_modified": mod["score"],
            "intent_level": d["seeking_level"],          # metadata preserved
            "intent_component": mod["intent_component"],
            "rcm_relevant": bool(d["rcm_relevant"]),
            **{k: v for k, v in mod.items() if k.startswith("hit_")},
        })
    assert len(rows) == 167, f"expected 167 scored rows, got {len(rows)}"
    return rows


# --------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------
def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    return pearson(rank(a), rank(b))


MODELS = [("v1", "v1"), ("v2 proposed", "v2_proposed"), ("v2 modified", "v2_modified")]


def report(rows: list[dict]) -> None:
    H = [r["human"] for r in rows]

    def topk(key, k):
        hi = {r["index"] for r in sorted(rows, key=lambda r: -r["human"])[:k]}
        vi = {r["index"] for r in sorted(rows, key=lambda r: -r[key])[:k]}
        return len(hi & vi)

    def recall_a(key):
        return sum(1 for r in sorted(rows, key=lambda r: -r[key])[:33] if r["group"] == "A")

    print("=" * 96)
    print("SLD SCORING COMPARISON -- 167 gold-labelled posts")
    print("=" * 96)
    hdr = (f"{'model':14s} {'pearson':>8s} {'spearman':>9s} {'A@33':>5s} {'top10':>6s} "
           f"{'top20':>6s} {'mean':>6s} {'median':>7s} {'max':>6s} {'zeros':>6s} {'>=30 @ 0':>9s}")
    print(hdr)
    print("-" * len(hdr))
    for name, key in MODELS:
        v = [r[key] for r in rows]
        zeroed = sum(1 for r in rows if r[key] == 0 and r["human"] >= 30)
        print(f"{name:14s} {pearson(H, v):8.3f} {spearman(H, v):9.3f} {recall_a(key):5d} "
              f"{topk(key, 10):5d}  {topk(key, 20):5d}  {st.mean(v):6.1f} {st.median(v):7.1f} "
              f"{max(v):6.1f} {sum(1 for x in v if x == 0):6d} {zeroed:9d}")

    print()
    print("Ranking quality among the 102 posts step 1 marked RCM-relevant")
    print("(the headline numbers above are inflated by correctly ordering obvious noise):")
    sub = [r for r in rows if r["rcm_relevant"]]
    Hs = [r["human"] for r in sub]
    for name, key in MODELS:
        v = [r[key] for r in sub]
        print(f"   {name:14s} pearson={pearson(Hs, v):.3f}  spearman={spearman(Hs, v):.3f}")

    print()
    print("=" * 96)
    print("INTENT -- distribution of the new level-based term")
    print("=" * 96)
    levels = {}
    for r in rows:
        levels.setdefault(str(r["intent_level"]), []).append(r)
    print(f"{'level':8s} {'n':>5s} {'score':>6s} {'mean human':>11s}")
    for lv in ("L0", "L1", "L2", "L3", "None"):
        rs = levels.get(lv, [])
        if not rs:
            print(f"{lv:8s} {0:5d} {intent_score(None if lv == 'None' else lv):6d} {'--':>11s}")
            continue
        print(f"{lv:8s} {len(rs):5d} {rs[0]['intent_component']:6d} "
              f"{st.mean([r['human'] for r in rs]):11.1f}")
    fired = {intent_score(r["intent_level"]) for r in rows}
    print(f"\n   distinct intent values actually emitted: {sorted(fired)}  "
          f"(spread {max(fired) - min(fired)} pts)")
    if not any(r["intent_level"] == "L3" for r in rows):
        print("   NOTE: L3 fires on 0/167 posts -- the 20-point tier is defined but "
              "unreachable on this corpus.")

    print()
    print("=" * 96)
    print("SCORE DISTRIBUTION BY BAND (v2 modified)")
    print("=" * 96)
    bands = [("Act", 55, 96), ("Engage", 30, 55), ("Watch", 10, 30), ("Discard", 0, 10)]
    for name, lo, hi in bands:
        rs = [r for r in rows if lo <= r["v2_modified"] < hi]
        a = sum(1 for r in rs if r["group"] == "A")
        print(f"   {name:8s} {lo:3d}-{hi - 1:<3d} n={len(rs):4d}   Group A inside: {a:3d}")

    print()
    print("=" * 96)
    print("EFFECT OF THE FIRST-PERSON CHANGE (18 -> 12) ON GROUP A")
    print("=" * 96)
    fp = [r for r in rows if r["hit_firstperson"] and r["group"] == "A"]
    deltas = sorted(fp, key=lambda r: r["v2_modified"] - r["v2_proposed"])
    print(f"   Group A posts carrying first-person voice: {len(fp)}")
    print(f"   worst drop: {deltas[0]['v2_modified'] - deltas[0]['v2_proposed']:+.1f} pts    "
          f"median drop: {st.median([r['v2_modified'] - r['v2_proposed'] for r in fp]):+.1f} pts")
    dropped = [r for r in fp if r["v2_proposed"] >= 55 > r["v2_modified"]]
    print(f"   Group A posts that fell out of the Act band: {len(dropped)}")
    for r in deltas[:5]:
        print(f"      human={r['human']:3d}  {r['v2_proposed']:5.1f} -> {r['v2_modified']:5.1f}  "
              f"({r['v2_modified'] - r['v2_proposed']:+5.1f})  {(r['title'] or '(reply)')[:44]}")

    print()
    print("=" * 96)
    print("TOP 12 BY v2 MODIFIED")
    print("=" * 96)
    for r in sorted(rows, key=lambda r: -r["v2_modified"])[:12]:
        print(f"   v2mod={r['v2_modified']:5.1f}  human={r['human']:3d}  v1={r['v1']:5.1f}  "
              f"{r['group']}  {r['source']:8s} {(r['title'] or '(reply)')[:50]}")

    print()
    print("FALSE NEGATIVES -- human >= 55, v2 modified low:")
    fn = [r for r in rows if r["human"] >= 55]
    for r in sorted(fn, key=lambda r: r["v2_modified"] - r["human"])[:6]:
        print(f"   human={r['human']:3d}  v2mod={r['v2_modified']:5.1f}  v1={r['v1']:5.1f}  "
              f"{(r['title'] or '(reply)')[:52]}")

    print()
    print("FALSE POSITIVES -- v2 modified high, human low:")
    for r in sorted(rows, key=lambda r: r["human"] - r["v2_modified"])[:6]:
        print(f"   human={r['human']:3d}  v2mod={r['v2_modified']:5.1f}  "
              f"{(r['title'] or '(reply)')[:52]}")


def write_outputs(rows: list[dict]) -> None:
    (HERE / "model_comparison.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    cols = ["index", "source_item_id", "source", "title", "group", "human", "v1",
            "v2_proposed", "v2_modified", "intent_level", "intent_component",
            "rcm_relevant", "opportunity_type", "human_confidence"]
    with (HERE / "model_comparison.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote model_comparison.json / .csv to {HERE}")


if __name__ == "__main__":
    rows = load()
    report(rows)
    write_outputs(rows)
