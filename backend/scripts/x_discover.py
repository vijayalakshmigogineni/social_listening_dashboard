"""X source discovery: run problem-oriented X searches via Apify and save raw results.

Discovery/validation only -- nothing here is written to the DB or scored.
Output: data/x_sourcing/<run>/<phase>/<key>.json (one file per query).

Usage (from backend/):
    python scripts/x_discover.py discovery            # built-in QUERIES
    python scripts/x_discover.py probes --from-accounts handle1 handle2 ...
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.apify_client import run_actor_sync  # noqa: E402
from app.config import DATA_DIR  # noqa: E402

ACTOR_ID = "tweetapi/twitter-x-search-scraper"
RUN_DIR = DATA_DIR / "x_sourcing" / "20260924"
BASE = " lang:en -filter:retweets"

# Problem-oriented, not "RCM"-keyword-oriented: payer + problem verb + practice-side
# context, procedure/device coverage, MAC/LCD, fee schedule, AR/payment delay.
QUERIES = {
    "uhc_denials": '(UHC OR UnitedHealthcare OR Optum) (denied OR denying OR denials) (claims OR claim) (practice OR "our office" OR billing OR clinic)',
    "aetna_cigna_humana_denials": '(Aetna OR Cigna OR Humana OR BCBS OR "Blue Cross") (denied OR denying OR denials) (claims OR claim) (practice OR "our office" OR billing OR clinic)',
    "pa_my_patient_p2p": '("prior auth" OR "prior authorization") ("my patient" OR "my patients") (denied OR "peer to peer" OR "peer-to-peer")',
    "p2p_denied_procedure": '("peer to peer" OR "peer-to-peer") insurance denied (MRI OR surgery OR procedure OR injection)',
    "ma_denials_practice": '"Medicare Advantage" (denied OR denials OR "prior auth" OR clawback OR downcoding) (practice OR clinic OR physicians OR "our patients")',
    "mac_lcd": '(Novitas OR Noridian OR Palmetto OR "First Coast" OR WPS OR CGS OR "NGS Medicare" OR LCD) (denial OR denials OR reimbursement OR coverage OR "local coverage")',
    "fee_schedule_cuts": '("physician fee schedule" OR "conversion factor" OR "Medicare cuts" OR "Medicare pay cut") (practice OR practices OR clinic)',
    "not_getting_paid": '(claims OR insurance OR payer) ("not getting paid" OR "haven\'t been paid" OR "still waiting on payment" OR "months to pay") (practice OR clinic OR office)',
    "downcoding": '(downcoding OR downcoded OR "down-coding" OR "level 5" OR "E/M") (Cigna OR Aetna OR UHC OR payer OR insurer) (denied OR downcode OR paid)',
    "pain_procedures": '("spinal cord stimulator" OR "radiofrequency ablation" OR "epidural steroid" OR "SI joint" OR kyphoplasty OR Intracept OR "medial branch") (denied OR denial OR coverage OR reimbursement OR "prior auth")',
    "medical_necessity": '("not medically necessary" OR "medical necessity") (denied OR denial) ("my patient" OR "our patient" OR "our practice" OR "my practice")',
    "modifier_coding": '("modifier 25" OR "modifier 59" OR "-25 modifier" OR "CPT code") (denied OR denials OR paid OR payer OR insurance)',
    "pa_staff_burden": '("prior authorization" OR "prior auth" OR "prior auths") (staff OR "full-time" OR "hours a week" OR "on hold") (practice OR clinic OR office)',
    "medicaid_payment": 'Medicaid (claims OR payments OR reimbursement) (delayed OR denied OR "not paid" OR cut) (clinic OR practice OR providers)',
    "nsa_idr": '("No Surprises Act" OR IDR OR "independent dispute resolution") (payment OR arbitration OR insurer) (physicians OR practice OR won)',
    "payer_portal_hold": '(Availity OR "provider portal" OR "provider services" OR "provider rep") (claim OR denial OR hold OR hours)',
    "retro_denial_clawback": '("retro denial" OR "retroactive denial" OR recoupment OR clawback OR "recouped") (insurance OR payer OR Medicare OR UHC OR Aetna)',
    "ar_backlog": '("accounts receivable" OR "A/R" OR "claims backlog" OR "unpaid claims") (practice OR clinic OR physicians) (insurance OR payer OR Medicare)',
}


def run_query(key: str, query: str, mode: str, max_items: int, out_dir: Path) -> tuple[str, int]:
    items = run_actor_sync(
        ACTOR_ID,
        {"query": query + BASE, "mode": mode, "maxItems": max_items},
        max_items=max_items,
        max_total_charge_usd=0.05,
        timeout_s=600,
    )
    (out_dir / f"{key}.json").write_text(
        json.dumps({"key": key, "query": query + BASE, "mode": mode, "items": items},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return key, len(items)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase")
    p.add_argument("--mode", default="Top")
    p.add_argument("--max-items", type=int, default=50)
    p.add_argument("--from-accounts", nargs="*")
    p.add_argument("--only", nargs="*")
    args = p.parse_args()

    if args.from_accounts:
        queries = {f"from_{h}": f"from:{h}" for h in args.from_accounts}
    else:
        queries = {k: v for k, v in QUERIES.items() if not args.only or k in args.only}

    out_dir = RUN_DIR / args.phase
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_query, k, q, args.mode, args.max_items, out_dir)
                   for k, q in queries.items()]
        for f in futures:
            try:
                key, n = f.result()
                print(f"{key}: {n}", flush=True)
            except Exception as exc:
                print(f"ERROR: {exc}", flush=True)


if __name__ == "__main__":
    main()
