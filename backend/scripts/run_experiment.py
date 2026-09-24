"""Fresh end-to-end evaluation run: the 167-post gold set + the collected
Facebook posts, re-normalized from raw collection data and re-analyzed through
every stage, stored under experiment-specific versions.

Usage (from backend/):
    python scripts/run_experiment.py                  # manifest -> run -> report
    python scripts/run_experiment.py --report-only    # rebuild the report from stored output
    python scripts/run_experiment.py --experiment-id exp187-semantic
        --manifest-from exp187-20260924 --baseline exp187-20260924
                                                      # same frozen posts, compared to a baseline run

What it does, in order:
  1. Manifest  -- freezes the post list once (gold ids from
                  data/gold/sld_167_gold_labels.json + every source=facebook row)
                  into data/experiments/<id>/manifest.json. Later runs reuse it.
  2. Preflight -- refuses to start unless LLM_PROVIDER=ollama and the Ollama
                  model is pulled, so no run silently falls back to NLI-only or
                  touches Bedrock.
  3. Per post  -- rebuilds the normalized record from raw_data with the source's
                  own collector normalize_post(), validates it against the
                  canonical schema, then runs every analysis stage + v1 + v2
                  fresh (replies get their parent post as context).
  4. Storage   -- analysis_results rows under "<id>-v1" / "<id>-v2" (the
                  production sld-analysis-v1/-v2 rows are never touched), plus
                  posts.jsonl with the full per-stage trace.
  5. Report    -- report.md + summary.json.

Nothing here changes scoring weights; it only measures.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics as st
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis import llm_fallback  # noqa: E402
from app.analysis.pipeline import run_pipeline_traced  # noqa: E402
from app.analysis.runner import resolve_parent_text  # noqa: E402
from app.collectors import aapc, facebook, linkedin, reddit  # noqa: E402
from app.config import DATA_DIR  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.models import AnalysisResult as AnalysisResultRow  # noqa: E402
from app.db.models import NormalizedItem  # noqa: E402
from app.schemas.analysis import ANALYSIS_VERSION  # noqa: E402
from app.schemas.normalized import NormalizedItem as NormalizedSchema  # noqa: E402

DEFAULT_EXP_ID = "exp187-20260924"
GOLD_DIR = DATA_DIR / "gold"
SOURCES = ["aapc", "reddit", "linkedin", "facebook"]

V1_BANDS = [("High (>=20)", 20), ("Mid (10-20)", 10), ("Watch (4-10)", 4), ("Low (<4)", float("-inf"))]
V2_BANDS = [("Act (>=55)", 55), ("Engage (30-55)", 30), ("Watch (10-30)", 10), ("Discard (<10)", float("-inf"))]


# ---------------------------------------------------------------------------
# 1. Manifest
# ---------------------------------------------------------------------------
def build_manifest(db, expected_facebook: int) -> list[dict]:
    gold = json.loads((GOLD_DIR / "sld_167_gold_labels.json").read_text(encoding="utf-8"))
    entries = [
        {"source": g["source"], "source_item_id": g["source_item_id"], "in_gold": True,
         "gold_index": g["index"], "human_score": g["human_opportunity_score"]}
        for g in gold
    ]
    fb_ids = sorted(sid for (sid,) in db.query(NormalizedItem.source_item_id)
                    .filter_by(source="facebook").all())
    if len(fb_ids) != expected_facebook:
        raise SystemExit(f"expected {expected_facebook} facebook rows in normalized_items, "
                         f"found {len(fb_ids)} -- collect/top-up first")
    entries += [{"source": "facebook", "source_item_id": sid, "in_gold": False,
                 "gold_index": None, "human_score": None} for sid in fb_ids]
    return entries


# ---------------------------------------------------------------------------
# 2. Preflight
# ---------------------------------------------------------------------------
def preflight() -> dict:
    info = {"provider": llm_fallback.PROVIDER, "model": llm_fallback.ACTIVE_MODEL,
            "host": llm_fallback.OLLAMA_HOST, "enabled": llm_fallback.LLM_FALLBACK_ENABLED}
    if llm_fallback.PROVIDER != "ollama" or not llm_fallback.LLM_FALLBACK_ENABLED:
        raise SystemExit(f"LLM provider must be ollama for this experiment, got {info}. "
                         "Set LLM_PROVIDER=ollama.")
    if not llm_fallback.ollama_model_available():
        raise SystemExit(f"Ollama is not reachable at {llm_fallback.OLLAMA_HOST} or model "
                         f"'{llm_fallback.OLLAMA_MODEL}' is not pulled (ollama pull {llm_fallback.OLLAMA_MODEL}).")
    return info


# ---------------------------------------------------------------------------
# 3. Re-normalization from raw collection data
# ---------------------------------------------------------------------------
def renormalize(row: NormalizedItem) -> dict:
    raw = row.raw_data
    meta = row.source_metadata or {}
    if row.source == "reddit":
        rec = reddit.normalize_post(raw, meta.get("subreddit"))
    elif row.source == "linkedin":
        rec = linkedin.normalize_post(raw, meta.get("search_query"))
    elif row.source == "aapc":
        rec = aapc.normalize_post(raw)
    elif row.source == "facebook":
        rec = facebook.normalize_post(raw, meta.get("group_key"))
    else:
        raise ValueError(f"no normalizer for source {row.source!r}")
    NormalizedSchema(**rec)  # schema validation; raises on violation
    return rec


# ---------------------------------------------------------------------------
# 4. Run
# ---------------------------------------------------------------------------
def run(exp_id: str, out_dir: Path, expected_facebook: int) -> None:
    db = SessionLocal()
    try:
        manifest_path = out_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            print(f"[exp] reusing frozen manifest: {len(manifest)} posts")
        else:
            manifest = build_manifest(db, expected_facebook)
            manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
            print(f"[exp] manifest frozen: {len(manifest)} posts")

        llm_info = preflight()
        print(f"[exp] LLM: {llm_info}")
        llm_fallback.reset_call_stats()

        v1_tag, v2_tag = f"{exp_id}-v1", f"{exp_id}-v2"
        started = datetime.now(timezone.utc)
        lines = []
        for n, entry in enumerate(manifest, 1):
            rec_out = dict(entry)
            t0 = time.perf_counter()
            before = dict(llm_fallback.CALL_STATS)
            before_kind = {k: dict(v) for k, v in llm_fallback.CALL_STATS_BY_KIND.items()}
            try:
                row = (db.query(NormalizedItem)
                       .filter_by(source=entry["source"], source_item_id=entry["source_item_id"])
                       .one_or_none())
                if row is None:
                    raise LookupError("post not found in normalized_items")
                rec = renormalize(row)
                rec_out["renormalized_text_matches_stored"] = (
                    (rec["text"] or "") == (row.text or "") and (rec["title"] or "") == (row.title or ""))
                rec_out["channel"] = ((row.source_metadata or {}).get("subreddit")
                                      or (row.source_metadata or {}).get("forum")
                                      or (row.source_metadata or {}).get("group_key"))

                results, trace = run_pipeline_traced(
                    source_item_id=rec["source_item_id"],
                    title=rec["title"],
                    text=rec["text"],
                    created_at=rec["created_at"],
                    matched_keywords=(rec["source_metadata"] or {}).get("matched_rcm_keywords"),
                    analysis_version_v1=v1_tag,
                    analysis_version_v2=v2_tag,
                    parent_text=resolve_parent_text(db, row.source, row.parent_id),
                    source=row.source,
                )
                for result in results:
                    payload = result.model_dump(exclude={"created_at", "updated_at"})
                    existing = (db.query(AnalysisResultRow)
                                .filter_by(source_item_id=result.source_item_id,
                                           analysis_version=result.analysis_version)
                                .one_or_none())
                    if existing is None:
                        db.add(AnalysisResultRow(**payload))
                    else:
                        for field, value in payload.items():
                            setattr(existing, field, value)

                v1, v2 = results
                s1 = trace["step1_rcm_relevance"]
                s4 = trace["step4_context"]
                rec_out.update({
                    "ok": True, "error": None,
                    "relevance_status": s1.get("relevance_status"),
                    "relevance_method": s1.get("relevance_method"),
                    "semantic_source": (trace.get("step2_semantic") or {}).get("semantic_source"),
                    "rcm_relevant": v1.rcm_relevant, "problem_evidence": v1.problem_evidence,
                    "speaker_type": v1.speaker_type, "content_stance": v1.content_stance,
                    "seeking_level": v1.seeking_level,
                    "stance_source": s4.get("stance_source"), "seeking_source": s4.get("seeking_source"),
                    "confidence": v1.confidence,
                    "v1": v1.final_score, "v2": v2.final_score,
                    "v1_breakdown": v1.score_breakdown, "v2_breakdown": v2.score_breakdown,
                    "evidence_quote": v1.evidence_quote,
                    "trace": trace,
                })
            except Exception as exc:  # recorded, never aborts the run
                rec_out.update({"ok": False, "error": f"{type(exc).__name__}: {exc}",
                                "traceback": traceback.format_exc(limit=5)})
            after = llm_fallback.CALL_STATS
            rec_out["llm_calls"] = {k: after[k] - before[k] for k in after}
            rec_out["llm_calls_by_kind"] = {
                kind: stats["attempted"] - before_kind[kind]["attempted"]
                for kind, stats in llm_fallback.CALL_STATS_BY_KIND.items()
            }
            rec_out["seconds"] = round(time.perf_counter() - t0, 2)
            lines.append(rec_out)

            status = (f"v1={rec_out['v1']:.2f} v2={rec_out['v2']:.2f} "
                      f"llm={rec_out['llm_calls']['attempted']}") if rec_out.get("ok") else f"ERROR {rec_out['error']}"
            print(f"[{n}/{len(manifest)}] {entry['source']}:{entry['source_item_id']} {status} "
                  f"({rec_out['seconds']}s)", flush=True)
            if n % 10 == 0:
                db.commit()
        db.commit()

        finished = datetime.now(timezone.utc)
        with (out_dir / "posts.jsonl").open("w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(json.dumps(line, default=str, ensure_ascii=False) + "\n")
        run_meta = {
            "experiment_id": exp_id, "versions": [v1_tag, v2_tag],
            "started_at": started.isoformat(), "finished_at": finished.isoformat(),
            "llm": llm_info, "llm_call_stats": dict(llm_fallback.CALL_STATS),
            "llm_call_stats_by_kind": {k: dict(v) for k, v in llm_fallback.CALL_STATS_BY_KIND.items()},
            "boto3_imported": "boto3" in sys.modules,
        }
        (out_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=1), encoding="utf-8")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Report
# ---------------------------------------------------------------------------
def _pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(order):  # average ranks for ties
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def _spearman(a, b):
    return _pearson(_rank(a), _rank(b))


def _band(score, bands):
    for label, cutoff in bands:
        if score >= cutoff:
            return label
    return bands[-1][0]


def _stats(vals):
    if not vals:
        return {"mean": None, "median": None, "max": None}
    return {"mean": round(st.mean(vals), 2), "median": round(st.median(vals), 2), "max": round(max(vals), 2)}


def _group_summary(rows):
    ok = [r for r in rows if r.get("ok")]
    v1 = [r["v1"] for r in ok]
    v2 = [r["v2"] for r in ok]
    return {
        "posts": len(rows), "processed": len(ok), "errors": len(rows) - len(ok),
        "rcm_relevant": sum(1 for r in ok if r["rcm_relevant"]),
        "problem_evidence": sum(1 for r in ok if r["problem_evidence"]),
        "v1": _stats(v1), "v2": _stats(v2),
        "v1_bands": {b: sum(1 for x in v1 if _band(x, V1_BANDS) == b) for b, _ in V1_BANDS},
        "v2_bands": {b: sum(1 for x in v2 if _band(x, V2_BANDS) == b) for b, _ in V2_BANDS},
        "seeking": {k: sum(1 for r in ok if (r["seeking_level"] or "none") == k)
                    for k in ["L0", "L1", "L2", "L3", "none"]},
        "stance": dict(Counter(r["content_stance"] for r in ok)),
        "speaker": dict(Counter(r["speaker_type"] for r in ok)),
        "stance_source": dict(Counter(r["stance_source"] or "skipped" for r in ok)),
        "seeking_source": dict(Counter(r["seeking_source"] or "skipped" for r in ok)),
        "relevance_method": dict(Counter(
            f"{r.get('relevance_status') or '?'}/{r.get('relevance_method') or '?'}" for r in ok)),
        "semantic_source": dict(Counter(r.get("semantic_source") or "skipped" for r in ok)),
        "llm_calls": {k: sum(r["llm_calls"][k] for r in rows) for k in ("attempted", "succeeded", "failed")},
        "llm_calls_by_kind": {k: sum((r.get("llm_calls_by_kind") or {}).get(k, 0) for r in rows)
                              for k in llm_fallback.CALL_KINDS},
        "renormalize_mismatches": sum(1 for r in ok if r.get("renormalized_text_matches_stored") is False),
        "avg_seconds": round(st.mean(r["seconds"] for r in rows), 2) if rows else None,
    }


def _old_scores(db) -> tuple[dict, dict]:
    old_v1 = dict(db.query(AnalysisResultRow.source_item_id, AnalysisResultRow.final_score)
                  .filter_by(analysis_version=ANALYSIS_VERSION).all())
    old_v2 = {}
    with (GOLD_DIR / "model_comparison.csv").open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            old_v2[r["source_item_id"]] = float(r["v2_modified"])
    return old_v1, old_v2


def _excerpt(text: str | None, n: int = 90) -> str:
    t = " ".join((text or "").split())
    t = t.replace("|", "/")
    return t[:n] + ("..." if len(t) > n else "")


def report(exp_id: str, out_dir: Path, baseline_id: str | None = None) -> dict:
    rows = [json.loads(l) for l in (out_dir / "posts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    meta = json.loads((out_dir / "run_meta.json").read_text(encoding="utf-8"))

    by_source = {s: _group_summary([r for r in rows if r["source"] == s]) for s in SOURCES}
    overall = _group_summary(rows)
    fb_groups = {g: _group_summary([r for r in rows if r["source"] == "facebook" and r.get("channel") == g])
                 for g in sorted({r.get("channel") for r in rows if r["source"] == "facebook"}, key=str)}

    db = SessionLocal()
    try:
        old_v1, old_v2 = _old_scores(db)
        fb_text = {sid: t for sid, t in db.query(NormalizedItem.source_item_id, NormalizedItem.text)
                   .filter_by(source="facebook").all()}
    finally:
        db.close()

    gold = [r for r in rows if r["in_gold"] and r.get("ok")]
    H = [r["human_score"] for r in gold]
    human_top20 = {r["source_item_id"] for r in sorted(gold, key=lambda r: -r["human_score"])[:20]}

    def agreement(scores):
        top = {r["source_item_id"] for r, _ in sorted(zip(gold, scores), key=lambda x: -x[1])[:20]}
        return {"pearson": round(_pearson(H, scores), 3), "spearman": round(_spearman(H, scores), 3),
                "top20_overlap": len(top & human_top20)}

    gold_eval = {
        "posts": len(gold),
        "fresh_v1": agreement([r["v1"] for r in gold]),
        "fresh_v2": agreement([r["v2"] for r in gold]),
        "stored_v1": agreement([old_v1.get(r["source_item_id"], 0.0) for r in gold]),
        "reference_v2_gold_csv": agreement([old_v2.get(r["source_item_id"], 0.0) for r in gold]),
        "v1_changed_vs_stored": sum(1 for r in gold if abs(r["v1"] - old_v1.get(r["source_item_id"], 0)) > 0.01),
        "v2_changed_vs_reference": sum(1 for r in gold if abs(r["v2"] - old_v2.get(r["source_item_id"], 0)) > 0.01),
    }

    baseline_eval = None
    if baseline_id:
        base_path = DATA_DIR / "experiments" / baseline_id / "posts.jsonl"
        base = {r["source_item_id"]: r for r in
                (json.loads(l) for l in base_path.read_text(encoding="utf-8").splitlines() if l.strip())
                if r.get("ok")}
        paired = [r for r in gold if r["source_item_id"] in base]
        Hp = [r["human_score"] for r in paired]
        human_top20_p = {r["source_item_id"] for r in sorted(paired, key=lambda r: -r["human_score"])[:20]}

        def agreement_p(scores):
            top = {r["source_item_id"] for r, _ in sorted(zip(paired, scores), key=lambda x: -x[1])[:20]}
            return {"pearson": round(_pearson(Hp, scores), 3), "spearman": round(_spearman(Hp, scores), 3),
                    "top20_overlap": len(top & human_top20_p)}

        def changed(field):
            return sum(1 for r in paired if r.get(field) != base[r["source_item_id"]].get(field))

        baseline_eval = {
            "baseline": baseline_id, "paired_posts": len(paired),
            "baseline_v1": agreement_p([base[r["source_item_id"]]["v1"] for r in paired]),
            "baseline_v2": agreement_p([base[r["source_item_id"]]["v2"] for r in paired]),
            "this_v1": agreement_p([r["v1"] for r in paired]),
            "this_v2": agreement_p([r["v2"] for r in paired]),
            "changed": {f: changed(f) for f in ("rcm_relevant", "problem_evidence", "speaker_type",
                                                "content_stance", "seeking_level")},
        }

    summary = {"experiment": meta, "by_source": by_source, "overall": overall,
               "facebook_by_group": fb_groups, "gold_eval": gold_eval, "baseline_eval": baseline_eval}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    # ---- markdown ----------------------------------------------------------
    cols = SOURCES + ["overall"]
    table = {**by_source, "overall": overall}
    L = []
    w = L.append
    w(f"# SLD evaluation run `{exp_id}`\n")
    w(f"Run {meta['started_at'][:19]}Z -> {meta['finished_at'][:19]}Z. "
      f"Stored as analysis versions `{meta['versions'][0]}` / `{meta['versions'][1]}`; "
      "production `sld-analysis-v1/-v2` rows and the gold files were not modified.\n")
    llm = meta["llm"]
    cs = meta["llm_call_stats"]
    w(f"**LLM used:** {llm['provider']} `{llm['model']}` at {llm['host']}. "
      f"Calls attempted {cs['attempted']}, succeeded {cs['succeeded']}, failed {cs['failed']}. "
      f"boto3 imported during run: {meta['boto3_imported']}.\n")
    w("Scores: v1 bands High>=20 / Mid>=10 / Watch>=4 / Low; v2 bands Act>=55 / Engage>=30 / "
      "Watch>=10 / Discard (the dashboard's cutoffs). v2 weights are unchanged.\n")

    def row(label, fn):
        w(f"| {label} | " + " | ".join(str(fn(table[c])) for c in cols) + " |")

    w("## Per-source summary\n")
    w("| | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    row("Posts", lambda s: s["posts"])
    row("Processed OK", lambda s: s["processed"])
    row("Processing errors", lambda s: s["errors"])
    row("RCM-relevant (Step 1)", lambda s: s["rcm_relevant"])
    row("Problem evidence (Step 2, semantic)", lambda s: s["problem_evidence"])
    row("v1 mean / median", lambda s: f"{s['v1']['mean']} / {s['v1']['median']}")
    row("v1 max", lambda s: s["v1"]["max"])
    row("v2 mean / median", lambda s: f"{s['v2']['mean']} / {s['v2']['median']}")
    row("v2 max", lambda s: s["v2"]["max"])
    row("Avg seconds / post", lambda s: s["avg_seconds"])
    w("")

    w("## v2 action bands\n")
    w("| Band | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for b, _ in V2_BANDS:
        row(b, lambda s, b=b: f"{s['v2_bands'][b]} ({100 * s['v2_bands'][b] / max(s['processed'], 1):.0f}%)")
    w("")
    w("## v1 bands\n")
    w("| Band | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for b, _ in V1_BANDS:
        row(b, lambda s, b=b: s["v1_bands"][b])
    w("")

    w("## Seeking level (Step 2)\n")
    w("| Level | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for k in ["L0", "L1", "L2", "L3", "none"]:
        row(k if k != "none" else "none (supplying / not relevant)", lambda s, k=k: s["seeking"][k])
    w("")

    w("## Decision sources and LLM calls\n")
    w("Step 1: `clearly_relevant/rules` = >=1 keyword hit, no LLM; `ambiguous/llm` = "
      "zero hits resolved by the LLM; `ambiguous/fallback` = LLM unavailable, NLI decided. "
      "Step 2: `llm` = one semantic call; `fallback` = legacy rule/NLI stages; "
      "`skipped` = not RCM-relevant.\n")
    w("| | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for m in ["clearly_relevant/rules", "ambiguous/llm", "ambiguous/fallback", "ambiguous/rules"]:
        row(f"Step 1 {m}", lambda s, m=m: s["relevance_method"].get(m, 0))
    for src in ["llm", "fallback", "skipped"]:
        row(f"Step 2 via {src}", lambda s, src=src: s["semantic_source"].get(src, 0))
    for kind in llm_fallback.CALL_KINDS:
        row(f"LLM calls: {kind}", lambda s, kind=kind: s["llm_calls_by_kind"][kind])
    row("LLM calls attempted", lambda s: s["llm_calls"]["attempted"])
    row("LLM calls failed", lambda s: s["llm_calls"]["failed"])
    row("Re-normalized text != stored", lambda s: s["renormalize_mismatches"])
    w("")

    w("## Speaker type\n")
    speakers = sorted({k for c in cols for k in table[c]["speaker"]})
    w("| Speaker | " + " | ".join(cols) + " |")
    w("|---|" + "---:|" * len(cols))
    for k in speakers:
        row(k, lambda s, k=k: s["speaker"].get(k, 0))
    w("")

    g = gold_eval
    w(f"## Agreement with human scores (gold set, {g['posts']} posts)\n")
    w("Facebook posts have no human labels, so this covers the 167 gold posts only.\n")
    w("| Scorer | Pearson | Spearman | Human top-20 found |")
    w("|---|---:|---:|---:|")
    for label, key in [("v1, fresh run", "fresh_v1"), ("v2, fresh run", "fresh_v2"),
                       ("v1, stored production rows", "stored_v1"),
                       ("v2, reference (model_comparison.csv)", "reference_v2_gold_csv")]:
        w(f"| {label} | {g[key]['pearson']} | {g[key]['spearman']} | {g[key]['top20_overlap']} / 20 |")
    w(f"\nv1 score changed vs stored row on {g['v1_changed_vs_stored']} posts; "
      f"v2 changed vs the gold-set reference on {g['v2_changed_vs_reference']} posts.\n")

    if baseline_eval:
        b = baseline_eval
        w(f"## Semantic pipeline vs baseline `{b['baseline']}` (gold posts in both, {b['paired_posts']})\n")
        w("Same posts, same scorers and weights; only the upstream analysis differs. "
          "**In-sample:** the gold set is the one v2 was fitted on, so these figures are optimistic "
          "and do not by themselves show the new pipeline is better.\n")
        w("| Scorer | Pearson | Spearman | Human top-20 found |")
        w("|---|---:|---:|---:|")
        for label, key in [("v1, baseline", "baseline_v1"), ("v1, this run", "this_v1"),
                           ("v2, baseline", "baseline_v2"), ("v2, this run", "this_v2")]:
            w(f"| {label} | {b[key]['pearson']} | {b[key]['spearman']} | {b[key]['top20_overlap']} / 20 |")
        w("\nLabels changed vs baseline: " + ", ".join(f"{k} {v}" for k, v in b["changed"].items()) + ".\n")

    w("## Facebook by group\n")
    w("| Group | Posts | RCM-relevant | v1 mean | v2 mean | v2 max | Act+Engage |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for grp, s in fb_groups.items():
        ae = s["v2_bands"]["Act (>=55)"] + s["v2_bands"]["Engage (30-55)"]
        w(f"| {grp} | {s['posts']} | {s['rcm_relevant']} | {s['v1']['mean']} | {s['v2']['mean']} | {s['v2']['max']} | {ae} |")
    w("")

    w("## Facebook posts\n")
    w("| Post id | Group | v1 | v2 | v2 band | Seeking | Excerpt |")
    w("|---|---|---:|---:|---|---|---|")
    for r in sorted([r for r in rows if r["source"] == "facebook"], key=lambda r: -(r.get("v2") or -1)):
        if not r.get("ok"):
            w(f"| {r['source_item_id']} | {r.get('channel')} | - | - | ERROR | - | {r['error']} |")
            continue
        w(f"| {r['source_item_id']} | {r.get('channel')} | {r['v1']:.1f} | {r['v2']:.1f} | "
          f"{_band(r['v2'], V2_BANDS)} | {r['seeking_level'] or 'none'} | {_excerpt(fb_text.get(r['source_item_id']))} |")
    w("")

    errs = [r for r in rows if not r.get("ok")]
    w("## Processing errors\n")
    if errs:
        for r in errs:
            w(f"- `{r['source']}:{r['source_item_id']}` -- {r['error']}")
    else:
        w("None.")
    w("")

    (out_dir / "report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[exp] report written: {out_dir / 'report.md'}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default=DEFAULT_EXP_ID)
    parser.add_argument("--expected-facebook", type=int, default=20)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--manifest-from", help="experiment id whose frozen manifest.json to reuse")
    parser.add_argument("--baseline", help="experiment id to compare against in the report")
    args = parser.parse_args()

    out_dir = DATA_DIR / "experiments" / args.experiment_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.manifest_from and not (out_dir / "manifest.json").exists():
        src = DATA_DIR / "experiments" / args.manifest_from / "manifest.json"
        (out_dir / "manifest.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    if not args.report_only:
        run(args.experiment_id, out_dir, args.expected_facebook)
    report(args.experiment_id, out_dir, args.baseline)


if __name__ == "__main__":
    main()
