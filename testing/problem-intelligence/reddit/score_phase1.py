"""
Join the hand-authored labels to the 60-post dataset, validate, and compute
the five Phase 1 base rates plus the supporting counts.

Labels live in labels_authored.py and are kept separate from the raw capture
in data/raw/reddit_60.json. This script writes:

    data/labels/reddit_60_labels.json   labels joined to post identity
    results/phase1_base_rates.json      the numbers
"""

import json
import sys
from pathlib import Path
from collections import Counter

from labels_authored import LABELS

HERE = Path(__file__).resolve().parent
POSTS_FILE = HERE / "data" / "reddit_60_posts.json"
LABELS_FILE = HERE / "data" / "labels" / "reddit_60_labels.json"
RATES_FILE = HERE / "results" / "phase1_base_rates.json"

FIELDS = [
    "post_id",
    "relevant_to_rcm",
    "problem_evidence",
    "first_person_problem",
    "problem_category",
    "seeking_level",
    "identifiable_role",
    "identifiable_organization",
    "pain_management_relevant",
    "painmedpa_service_match",
    "orgs_mentioned",
    "notes",
]

CATEGORIES = [
    "Authorization & Pre-Certification",
    "Denials & Appeals",
    "Coding & Documentation",
    "Reimbursement & Underpayment",
    "AR & Collections",
    "Credentialing & Enrollment",
    "Staffing & Capacity",
    "Technology & Workflow",
    "Vendor / Outsourcing Dissatisfaction",
    "Other",
    "None",
]

SEEKING = ["L0", "L1", "L2", "L3", "L4"]
YN = {"yes", "no"}
YNU = {"yes", "no", "unclear"}


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def main():
    posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))["posts"]
    by_id = {p["post_id"]: p for p in posts}

    records = [dict(zip(FIELDS, row)) for row in LABELS]

    # ---------------- validation ----------------
    errors = []

    if len(records) != len(posts):
        errors.append(f"label count {len(records)} != post count {len(posts)}")

    label_ids = [r["post_id"] for r in records]
    if len(set(label_ids)) != len(label_ids):
        dupes = [k for k, v in Counter(label_ids).items() if v > 1]
        errors.append(f"duplicate label ids: {dupes}")

    missing = set(by_id) - set(label_ids)
    extra = set(label_ids) - set(by_id)
    if missing:
        errors.append(f"posts with no label: {sorted(missing)}")
    if extra:
        errors.append(f"labels with no post: {sorted(extra)}")

    for r in records:
        pid = r["post_id"]
        if r["relevant_to_rcm"] not in YN:
            errors.append(f"{pid}: bad relevant_to_rcm {r['relevant_to_rcm']}")
        if r["problem_evidence"] not in YN:
            errors.append(f"{pid}: bad problem_evidence {r['problem_evidence']}")
        if r["first_person_problem"] not in YNU:
            errors.append(f"{pid}: bad first_person_problem")
        if r["problem_category"] not in CATEGORIES:
            errors.append(f"{pid}: bad category {r['problem_category']}")
        if r["seeking_level"] not in SEEKING:
            errors.append(f"{pid}: bad seeking_level {r['seeking_level']}")
        for f in (
            "identifiable_role",
            "identifiable_organization",
            "pain_management_relevant",
            "painmedpa_service_match",
        ):
            if r[f] not in YNU:
                errors.append(f"{pid}: bad {f} {r[f]}")
        if not (r["notes"] or "").strip():
            errors.append(f"{pid}: empty notes (labels must be traceable)")

        # Internal consistency of the stated rules.
        if r["problem_evidence"] == "yes" and r["relevant_to_rcm"] != "yes":
            errors.append(f"{pid}: problem_evidence yes but relevant_to_rcm no")
        if r["problem_evidence"] == "no" and r["problem_category"] != "None":
            errors.append(f"{pid}: no problem_evidence but category set")
        if r["problem_evidence"] == "yes" and r["problem_category"] == "None":
            errors.append(f"{pid}: problem_evidence yes but category None")
        if r["painmedpa_service_match"] == "yes" and r["pain_management_relevant"] != "yes":
            errors.append(f"{pid}: service_match yes without pain relevance")

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print(f"validation passed: {len(records)} labels, {len(posts)} posts, ids match")

    # ---------------- join and persist labels ----------------
    joined = []
    for r in records:
        p = by_id[r["post_id"]]
        joined.append(
            {
                **r,
                "community": p["community"],
                "url": p["url"],
                "title": p["title"],
                "created_at": p["created_at"],
            }
        )

    LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LABELS_FILE.write_text(
        json.dumps(
            {
                "meta": {
                    "phase": "Phase 1 - Manual Reality Check",
                    "labelled_by": "hand-labelled from post text",
                    "posts_file": "data/reddit_60_posts.json",
                    "raw_file": "data/raw/reddit_60.json",
                    "n": len(joined),
                },
                "labels": joined,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ---------------- base rates ----------------
    n = len(records)

    def count(pred, rows=None):
        return sum(1 for r in (rows if rows is not None else records) if pred(r))

    rcm = [r for r in records if r["relevant_to_rcm"] == "yes"]
    evid = [r for r in records if r["problem_evidence"] == "yes"]

    n_problem = len(evid)
    n_first_person = count(
        lambda r: r["problem_evidence"] == "yes" and r["first_person_problem"] == "yes"
    )
    n_l2plus = count(lambda r: r["seeking_level"] in ("L2", "L3", "L4"))
    n_l3plus = count(lambda r: r["seeking_level"] in ("L3", "L4"))
    n_role = count(lambda r: r["identifiable_role"] == "yes")
    n_org = count(lambda r: r["identifiable_organization"] == "yes")
    n_any_org = count(lambda r: bool(r["orgs_mentioned"]))
    n_pain = count(lambda r: r["pain_management_relevant"] == "yes")
    n_pain_incl_unclear = count(
        lambda r: r["pain_management_relevant"] in ("yes", "unclear")
    )
    n_match = count(lambda r: r["painmedpa_service_match"] == "yes")
    n_match_incl_unclear = count(
        lambda r: r["painmedpa_service_match"] in ("yes", "unclear")
    )

    # L2+ restricted to posts that actually carry RCM problem evidence -- the
    # headline L2+ figure above includes career-domain posts that are seeking
    # a remedy for something other than an operational problem.
    n_l2plus_evid = count(
        lambda r: r["seeking_level"] in ("L2", "L3", "L4"), rows=evid
    )
    n_l3plus_evid = count(lambda r: r["seeking_level"] in ("L3", "L4"), rows=evid)

    cat_counts = Counter(r["problem_category"] for r in records)
    seek_counts = Counter(r["seeking_level"] for r in records)
    by_sub = Counter(by_id[r["post_id"]]["community"] for r in evid)

    results = {
        "meta": {
            "phase": "Phase 1 - Manual Reality Check",
            "source": "reddit",
            "communities": sorted({p["community"] for p in posts}),
            "n_posts": n,
            "collected_via": "apify:trudax/reddit-scraper-lite",
            "denominator_note": "All five headline rates use n=60, the full sample. "
            "No filtering was applied before labelling.",
        },
        "base_rates": {
            "problem_evidence_rate": {
                "n": n_problem,
                "of": n,
                "pct": pct(n_problem, n),
                "definition": "posts showing a concrete RCM/practice operational problem "
                "someone is actually experiencing (not commentary, not a pure "
                "knowledge question, not career/labour-market difficulty)",
            },
            "solution_seeking_rate": {
                "n": n_l2plus,
                "of": n,
                "pct": pct(n_l2plus, n),
                "definition": "seeking_level L2 or above across the whole sample",
            },
            "identifiable_role_rate": {
                "n": n_role,
                "of": n,
                "pct": pct(n_role, n),
                "definition": "post text evidences the author's professional role",
            },
            "identifiable_organization_rate": {
                "n": n_org,
                "of": n,
                "pct": pct(n_org, n),
                "definition": "post text identifies the organisation the AUTHOR works for "
                "or on behalf of; third-party payers, vendors and prospective "
                "employers do not count",
            },
            "pain_management_relevance_rate": {
                "n": n_pain,
                "of": n,
                "pct": pct(n_pain, n),
                "definition": "post text evidences pain-management clinical or billing "
                "relevance",
            },
        },
        "counts": {
            "problem_category": {c: cat_counts.get(c, 0) for c in CATEGORIES},
            "seeking_level": {s: seek_counts.get(s, 0) for s in SEEKING},
            "l2_plus": n_l2plus,
            "l3_plus": n_l3plus,
            "pain_management_relevant": n_pain,
            "painmedpa_service_match": n_match,
        },
        "supporting": {
            "relevant_to_rcm": len(rcm),
            "problem_evidence": n_problem,
            "problem_evidence_first_person": n_first_person,
            "l2_plus_among_problem_evidence": n_l2plus_evid,
            "l3_plus_among_problem_evidence": n_l3plus_evid,
            "pain_management_relevant_incl_unclear": n_pain_incl_unclear,
            "painmedpa_service_match_incl_unclear": n_match_incl_unclear,
            "any_organisation_named_incl_third_party": n_any_org,
            "problem_evidence_by_community": dict(by_sub),
        },
        "decision_gate": {
            "roadmap_rule": "problem-evidence rate < 10% -> change sources before "
            "building; L3+ rate < 2% -> Deliverable B may not be viable",
            "problem_evidence_pct": pct(n_problem, n),
            "problem_evidence_gate": "PASS" if pct(n_problem, n) >= 10 else "FAIL",
            "l3_plus_pct": pct(n_l3plus, n),
            "l3_plus_gate": "PASS" if pct(n_l3plus, n) >= 2 else "FAIL",
        },
    }

    RATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    RATES_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---------------- console summary ----------------
    print("\n" + "=" * 68)
    print("PHASE 1 BASE RATES  (n = %d)" % n)
    print("=" * 68)
    for k, v in results["base_rates"].items():
        print(f"  {k:34s} {v['n']:3d}/{v['of']}  {v['pct']:5.1f}%")

    print("\nProblem categories:")
    for c in CATEGORIES:
        if cat_counts.get(c):
            print(f"  {c:38s} {cat_counts[c]:3d}")

    print("\nSeeking levels:")
    for s in SEEKING:
        print(f"  {s:38s} {seek_counts.get(s, 0):3d}")

    print(f"\n  L2+                                    {n_l2plus:3d}")
    print(f"  L3+                                    {n_l3plus:3d}")
    print(f"  pain-management relevant               {n_pain:3d}")
    print(f"  PainMed-PA service match               {n_match:3d}")

    print("\nDecision gates:")
    g = results["decision_gate"]
    print(f"  problem evidence {g['problem_evidence_pct']}% (>=10%) -> {g['problem_evidence_gate']}")
    print(f"  L3+ {g['l3_plus_pct']}% (>=2%) -> {g['l3_plus_gate']}")

    print(f"\nwrote {LABELS_FILE}")
    print(f"wrote {RATES_FILE}")


if __name__ == "__main__":
    main()
