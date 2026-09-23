"""Verify what the pipeline actually wrote against the offline evaluation.

Answers three questions after a `run_pipeline.py --force`:

  1. Did v1 reproduce? Steps 1-5 and the v1 scorer are unchanged, so a forced
     re-run should land on the same numbers. Drift means the NLI/LLM-fallback
     path is non-deterministic, which would invalidate any comparison drawn
     against the previously-stored v1 scores.
  2. Do the v2 rows the pipeline wrote match the offline model that the
     weights were chosen against?
  3. Do the headline metrics still hold when recomputed from the database
     rather than from the evaluation script's own in-memory scores?

Read-only. Run from backend/:  python data/gold/verify_pipeline_v2.py
"""

from __future__ import annotations

import json
import sqlite3
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "sld.db"
V1, V2 = "sld-analysis-v1", "sld-analysis-v2"
TOLERANCE = 0.11  # the offline file stores 1dp; the DB stores 4dp


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


def main() -> int:
    ref = {r["source_item_id"]: r for r in json.loads(
        (HERE / "model_comparison.json").read_text(encoding="utf-8"))}
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)

    rows = {}
    for sid, ver, score, breakdown in con.execute(
        "select source_item_id, analysis_version, final_score, score_breakdown "
        "from analysis_results where analysis_version in (?, ?)", (V1, V2)
    ):
        rows.setdefault(sid, {})[ver] = (score, json.loads(breakdown))

    failures: list[str] = []

    print("=" * 78)
    print("1. ROW COVERAGE")
    print("=" * 78)
    n_v1 = sum(1 for v in rows.values() if V1 in v)
    n_v2 = sum(1 for v in rows.values() if V2 in v)
    print(f"   items with a v1 row: {n_v1}")
    print(f"   items with a v2 row: {n_v2}")
    both = [s for s, v in rows.items() if V1 in v and V2 in v]
    print(f"   items with BOTH:     {len(both)}")
    if n_v1 != 167 or n_v2 != 167:
        failures.append(f"expected 167 rows per version, got v1={n_v1} v2={n_v2}")

    print()
    print("=" * 78)
    print("2. DID v1 REPRODUCE? (unchanged code -- drift would mean non-determinism)")
    print("=" * 78)
    drift = [
        (s, ref[s]["v1"], rows[s][V1][0])
        for s in both
        if s in ref and abs(rows[s][V1][0] - ref[s]["v1"]) > TOLERANCE
    ]
    print(f"   posts whose v1 score moved: {len(drift)} of {len(both)}")
    for s, was, now in drift[:8]:
        print(f"      {s:16s} {was:6.2f} -> {now:6.2f}")
    if drift:
        print("   NOTE: v1 is NOT deterministic. Metrics computed against the")
        print("         previously-stored v1 scores need recomputing.")

    print()
    print("=" * 78)
    print("3. DOES THE PIPELINE's v2 MATCH THE OFFLINE MODEL?")
    print("=" * 78)
    mism = [
        (s, ref[s]["v2_modified"], rows[s][V2][0])
        for s in both
        if s in ref and abs(rows[s][V2][0] - ref[s]["v2_modified"]) > TOLERANCE
    ]
    print(f"   mismatches beyond +/-{TOLERANCE}: {len(mism)} of {len(both)}")
    for s, want, got in mism[:8]:
        print(f"      {s:16s} offline={want:6.2f}  pipeline={got:6.2f}")
    if mism:
        failures.append(f"{len(mism)} v2 scores diverge from the offline model")

    print()
    print("=" * 78)
    print("4. METRICS RECOMPUTED FROM THE DATABASE")
    print("=" * 78)
    ids = [s for s in both if s in ref]
    H = [ref[s]["human"] for s in ids]
    A = [ref[s]["group"] for s in ids]
    print(f"{'source':16s} {'pearson':>8s} {'spearman':>9s} {'mean':>7s} {'max':>6s} {'A@33':>5s}")
    for name, vals in (
        ("db v1", [rows[s][V1][0] for s in ids]),
        ("db v2", [rows[s][V2][0] for s in ids]),
        ("offline v2", [ref[s]["v2_modified"] for s in ids]),
    ):
        order = sorted(range(len(vals)), key=lambda i: -vals[i])[:33]
        a33 = sum(1 for i in order if A[i] == "A")
        print(f"{name:16s} {pearson(H, vals):8.3f} {spearman(H, vals):9.3f} "
              f"{st.mean(vals):7.2f} {max(vals):6.1f} {a33:5d}")

    print()
    print("=" * 78)
    print("5. BEHAVIOUR CHANGE: posts v1 zeroes that v2 rescues")
    print("=" * 78)
    rescued = [
        (s, ref[s]["human"], rows[s][V2][0])
        for s in ids
        if rows[s][V1][0] == 0 and rows[s][V2][0] > 0 and ref[s]["human"] >= 30
    ]
    print(f"   posts scored 0 by v1 but >0 by v2, which a human rated >=30: {len(rescued)}")
    for s, human, v2 in sorted(rescued, key=lambda t: -t[1])[:8]:
        print(f"      {s:16s} human={human:3d}  v1=0.00  v2={v2:6.2f}")

    print()
    print("=" * 78)
    if failures:
        print("VERIFICATION FAILED")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("VERIFICATION PASSED -- pipeline v2 reproduces the offline model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
