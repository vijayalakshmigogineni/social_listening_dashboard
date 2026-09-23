"""Phases 2-4: distribution, group contrasts, observability, and the
human-vs-pipeline comparison. Read-only against sld.db."""

from __future__ import annotations

import json
import re
import sqlite3
import statistics as st
from collections import Counter
from pathlib import Path

SCRATCH = Path(__file__).parent
DB = "backend/data/sld.db"
gold = json.loads((SCRATCH / "gold" / "sld_167_gold_labels.json").read_text(encoding="utf-8"))
corpus = {r["source_item_id"]: r for r in json.loads(
    (SCRATCH / "phase1" / "blind_corpus.json").read_text(encoding="utf-8"))}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
v1 = {}
for sid, fs, sb, stype, stance, seek, rel in con.execute(
    "select source_item_id, final_score, score_breakdown, speaker_type, "
    "content_stance, seeking_level, rcm_relevant from analysis_results"
):
    v1[sid] = {"final": fs, "bd": json.loads(sb), "speaker": stype,
               "stance": stance, "seek": seek, "rcm_relevant": rel}

for g in gold:
    g["v1"] = v1[g["source_item_id"]]["final"]
    g["v1bd"] = v1[g["source_item_id"]]["bd"]
    g["v1speaker"] = v1[g["source_item_id"]]["speaker"]
    g["v1rel"] = v1[g["source_item_id"]]["rcm_relevant"]
    g["text"] = (corpus[g["source_item_id"]]["text"] or "")

H = [g["human_opportunity_score"] for g in gold]
P = [g["v1"] for g in gold]

def pct(vals, q):
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0

def rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r

print("=" * 78)
print("SECTION A -- SCORE DISTRIBUTIONS")
print("=" * 78)
for name, v in (("human", H), ("pipeline", P)):
    print(f"{name:9s} n={len(v)} min={min(v):5.1f} p25={pct(v,.25):5.1f} median={st.median(v):5.1f} "
          f"mean={st.mean(v):5.1f} p75={pct(v,.75):5.1f} p90={pct(v,.90):5.1f} max={max(v):5.1f} sd={st.pstdev(v):5.1f}")
print(f"\nzeros: human={sum(1 for x in H if x==0)}  pipeline={sum(1 for x in P if x==0)}")
print(f"pearson r = {pearson(H,P):.3f}")
print(f"spearman rho = {pearson(rank(H), rank(P)):.3f}")
d = [h - p for h, p in zip(H, P)]
print(f"mean diff (human-pipeline) = {st.mean(d):.1f}   median diff = {st.median(d):.1f}")
print(f"posts with |diff| >= 20 : {sum(1 for x in d if abs(x)>=20)}")

print()
print("=" * 78)
print("SECTION B -- GROUPS FROM THE HUMAN DISTRIBUTION")
print("=" * 78)
def grp(s):
    return "A" if s >= 55 else ("B" if s >= 30 else "C")
for g in gold:
    g["group"] = grp(g["human_opportunity_score"])
for G in "ABC":
    rows = [g for g in gold if g["group"] == G]
    print(f"\nGroup {G}: n={len(rows)} ({len(rows)/167:.0%})  human {min(r['human_opportunity_score'] for r in rows)}-"
          f"{max(r['human_opportunity_score'] for r in rows)}  "
          f"pipeline mean={st.mean([r['v1'] for r in rows]):.1f} max={max(r['v1'] for r in rows):.1f}")
    print("   source:", dict(Counter(r["source"] for r in rows)))
    print("   opp type:", dict(Counter(r["opportunity_type"] for r in rows).most_common()))
    print("   pain:", dict(Counter(r["pain_severity"] for r in rows)))
    print("   recurrence:", dict(Counter(r["recurrence"] for r in rows)))
    print("   practice_side:", dict(Counter(r["practice_side_evidence"] for r in rows)))
    print("   v1 speaker:", dict(Counter(r["v1speaker"] for r in rows)))

print()
print("=" * 78)
print("SECTION C -- OBSERVABILITY OF CANDIDATE SIGNALS (regex over raw text)")
print("=" * 78)
SIG = {
 "named_payer": r"\b(medicare|medicaid|aetna|cigna|humana|bcbs|blue cross|unitedhealth|uhc|umr|molina|noridian|novitas|palmetto|wps|caresource|tricare|medi-cal|wellpoint|cgs)\b",
 "cpt_or_hcpcs": r"\b(\d{5}|[A-Z]\d{4})\b",
 "denial_language": r"\b(denial|denials|denied|denying|deny|rejected|rejection|underpaid|not getting paid|non-?covered)\b",
 "recurrence_language": r"\b(keeps?|recently|influx|a lot of|a bunch of|repeatedly|constantly|every time|again|still|months|continue[sd]?|always|never)\b",
 "first_person_practice": r"\b(we are|we have|we bill|we bill|our (claims|practice|office|provider|clinic|surgeon|patients|software|team)|i am receiving|i work for|my (provider|surgeon|practice|office))\b",
 "explicit_ask": r"(any (help|input|suggestions?|advice|insight|guidance)|has anyone|does anyone|can someone|would appreciate|looking for|what (are|do) you (all )?us|how (do|are) you)",
 "escalation_failed_channel": r"(when (she|he|we|i) call|not been helpful|no response|told (us|me|her|him)|at a loss|cannot keep up|can.t keep up|maddening|100\+ websites|still appreciate|no one to ask)",
 "financial_impact_explicit": r"(\$\s?\d|\d+\s?(dollars|k\b)|lesser value|not getting paid|lost revenue|write ?off)",
 "practice_size_or_identity": r"(critical access|part b provider|dme (supply )?(store|biller)|group practice|our facility|small (outpatient )?clinic|health system|independent practice)",
 "vendor_selfpromo": r"(dm me|comment .|contact us|our (team|free guide|latest infographic)|#hiring|apply here|we are hiring|read the full (report|article)|https?://lnkd\.in)",
}
print(f"{'signal':32s} {'all':>7s} {'A':>7s} {'B':>7s} {'C':>7s}   verdict")
for name, pat in SIG.items():
    rx = re.compile(pat, re.I)
    hits = {G: 0 for G in "ABC"}
    tot = 0
    for g in gold:
        if rx.search(g["text"] or ""):
            tot += 1
            hits[g["group"]] += 1
    nA = sum(1 for g in gold if g["group"] == "A")
    nB = sum(1 for g in gold if g["group"] == "B")
    nC = sum(1 for g in gold if g["group"] == "C")
    ra, rb, rc = hits["A"]/nA, hits["B"]/nB, hits["C"]/nC
    lift = (ra / rc) if rc else float("inf")
    verdict = "HIGH obs" if tot/167 >= .30 else ("MED obs" if tot/167 >= .15 else "LOW obs")
    verdict += f", A/C lift={lift:.1f}" if lift != float("inf") else ", A/C lift=inf"
    print(f"{name:32s} {tot/167:6.0%} {ra:6.0%} {rb:6.0%} {rc:6.0%}   {verdict}")

print()
print("=" * 78)
print("SECTION D -- FALSE NEGATIVES (human high, pipeline low)")
print("=" * 78)
fn = sorted([g for g in gold if g["human_opportunity_score"] - g["v1"] >= 20],
            key=lambda g: g["v1"] - g["human_opportunity_score"])
print(f"count = {len(fn)}\n")
for g in fn[:18]:
    bd = g["v1bd"]
    print(f"[{g['index']:3d}] {g['source']:8s} human={g['human_opportunity_score']:3d} v1={g['v1']:5.2f} "
          f"(base={bd['base_score']:.0f} conf={bd['confidence']:.2f} rec={bd['recency_factor']:.2f} "
          f"speaker={g['v1speaker']} rcm_rel={g['v1rel']})")
    print(f"      {(g['title'] or g['text'][:70]).strip()[:88]}")

print()
print("=" * 78)
print("SECTION E -- FALSE POSITIVES (pipeline high relative to human)")
print("=" * 78)
fp = sorted([g for g in gold if g["v1"] - g["human_opportunity_score"] >= 5], key=lambda g: g["human_opportunity_score"] - g["v1"])
print(f"count (v1 exceeds human by >=5) = {len(fp)}\n")
for g in fp[:15]:
    bd = g["v1bd"]
    print(f"[{g['index']:3d}] {g['source']:8s} human={g['human_opportunity_score']:3d} v1={g['v1']:5.2f} "
          f"type={g['opportunity_type']:12s} base={bd['base_score']:.0f} rec={bd['recency_factor']:.2f}")
    print(f"      {(g['title'] or g['text'][:70]).strip()[:88]}")

print()
print("=" * 78)
print("SECTION F -- PIPELINE TOP 10 vs HUMAN TOP 10")
print("=" * 78)
print("pipeline top 10:")
for g in sorted(gold, key=lambda g: -g["v1"])[:10]:
    print(f"   v1={g['v1']:5.2f} human={g['human_opportunity_score']:3d} {g['source']:8s} {g['opportunity_type']:12s} {(g['title'] or g['text'][:60]).strip()[:64]}")
print("\nhuman top 10:")
for g in sorted(gold, key=lambda g: -g["human_opportunity_score"])[:10]:
    print(f"   human={g['human_opportunity_score']:3d} v1={g['v1']:5.2f} {g['source']:8s} {g['opportunity_type']:12s} {(g['title'] or g['text'][:60]).strip()[:64]}")

print()
print("=" * 78)
print("SECTION G -- PAIN x INTENT GRID (mean human score, n)")
print("=" * 78)
for pain in ("high", "medium", "low", "none"):
    row = []
    for intent in ("L2", "L1", "L0", "none"):
        rows = [g for g in gold if g["pain_severity"] == pain and g["intent_level"] == intent]
        row.append(f"{st.mean([r['human_opportunity_score'] for r in rows]):5.1f}(n={len(rows):3d})" if rows else "     -      ")
    print(f"pain={pain:7s} " + " ".join(row))
print("                " + " ".join(f"{i:^12s}" for i in ("L2", "L1", "L0", "none")))

print()
print("=" * 78)
print("SECTION H -- PER SOURCE")
print("=" * 78)
for s in ("aapc", "linkedin", "reddit"):
    rows = [g for g in gold if g["source"] == s]
    print(f"{s:9s} n={len(rows):3d} human mean={st.mean([r['human_opportunity_score'] for r in rows]):5.1f} "
          f"max={max(r['human_opportunity_score'] for r in rows):3d}  "
          f"v1 mean={st.mean([r['v1'] for r in rows]):5.2f} max={max(r['v1'] for r in rows):5.2f}  "
          f"GroupA={sum(1 for r in rows if r['group']=='A'):3d}  zero-human={sum(1 for r in rows if r['human_opportunity_score']==0)}")

print()
print("=" * 78)
print("SECTION I -- THREAD ROLLUP (AAPC)")
print("=" * 78)
conv = {}
for g in gold:
    if g["source"] == "aapc":
        conv.setdefault(g["conversation_id"], []).append(g)
multi = {k: v for k, v in conv.items() if len(v) > 1}
print(f"threads={len(conv)}  multi-post={len(multi)}")
gain = [(max(r['human_opportunity_score'] for r in v), st.mean([r['human_opportunity_score'] for r in v]), k, len(v)) for k, v in multi.items()]
print("threads where the max post far exceeds the thread mean (post-level scoring dilutes):")
for mx, mn, k, n in sorted(gain, key=lambda t: -(t[0]-t[1]))[:8]:
    print(f"   conv {k}: n={n} max={mx} mean={mn:.1f} spread={mx-mn:.1f}")

print()
print("=" * 78)
print("SECTION J -- SPOT-CHECK SET (25 most consequential uncertain labels)")
print("=" * 78)
cand = [g for g in gold if g["human_confidence"] in ("low", "medium")]
cand.sort(key=lambda g: -(g["human_opportunity_score"] + (15 if g["human_confidence"] == "low" else 0)))
for g in cand[:25]:
    print(f"[{g['index']:3d}] {g['source']:8s} human={g['human_opportunity_score']:3d} conf={g['human_confidence']:6s} "
          f"{(g['title'] or g['text'][:55]).strip()[:66]}")
Path(SCRATCH / "gold" / "spotcheck_25.json").write_text(json.dumps(
    [{k: g[k] for k in ("index","source_item_id","source","title","human_opportunity_score",
                        "opportunity_type","human_confidence","reason")} for g in cand[:25]],
    indent=1, ensure_ascii=False), encoding="utf-8")

json.dump([{k: v for k, v in g.items() if k not in ("text", "v1bd")} for g in gold],
          open(SCRATCH / "gold" / "gold_with_v1.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
