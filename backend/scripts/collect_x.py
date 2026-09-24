"""Run the X collector: fetch each validated account, save raw output, select
posts round-robin, and (with --store) upsert them into normalized_items.

Usage (from backend/):
    python scripts/collect_x.py                 # fetch + select + print, no DB write
    python scripts/collect_x.py --from-raw --store   # reuse saved raw output, store
    python scripts/collect_x.py --from-raw --ids-file data/x_sourcing/20260924/selection.json --store

--ids-file restricts the sample to the post ids listed in a research selection
file (Phase 4 of report.md). The research labels in that file are NOT stored:
the pipeline scores every post independently.

Raw actor output is kept under data/x_sourcing/20260924/collection/ so the
selection can be re-run without paying Apify again (~$0.25 per 1K posts).
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items  # noqa: E402
from app.collectors.x import (  # noqa: E402
    DEFAULT_ACCOUNTS,
    DEFAULT_LIMIT,
    DEFAULT_PER_ACCOUNT,
    build_query,
    collect_account,
    select_posts,
)
from app.config import DATA_DIR  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.models import NormalizedItem  # noqa: E402

RAW_DIR = DATA_DIR / "x_sourcing" / "20260924" / "collection"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--per-account", type=int, default=DEFAULT_PER_ACCOUNT)
    parser.add_argument("--from-raw", action="store_true")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--ids-file", type=Path, default=None)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    queries = {h: build_query(h) for h in DEFAULT_ACCOUNTS}
    raw_by_account = {}
    for handle in DEFAULT_ACCOUNTS:
        path = RAW_DIR / f"{handle}.json"
        if args.from_raw:
            raw_by_account[handle] = json.loads(path.read_text(encoding="utf-8"))["items"]
        else:
            items = collect_account(handle, args.per_account)
            path.write_text(json.dumps({"query": queries[handle], "items": items},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
            raw_by_account[handle] = items
        print(f"[x] {handle}: {len(raw_by_account[handle])} returned")

    db = SessionLocal()
    try:
        # analysis_results is keyed on source_item_id alone, so an X id must
        # not collide with any other source's id.
        existing = {sid: src for sid, src in db.query(NormalizedItem.source_item_id,
                                                      NormalizedItem.source).all()}
        if args.ids_file:
            wanted = {p["id"] for p in json.loads(args.ids_file.read_text(encoding="utf-8"))["posts"]}
            raw_by_account = {h: [t for t in items if str(t.get("id")) in wanted]
                              for h, items in raw_by_account.items()}
        records = select_posts(raw_by_account, args.limit,
                               exclude_ids={s for s, src in existing.items() if src != "x"},
                               queries=queries)
        print(f"\n[x] selected {len(records)} posts")
        for r in records:
            print(f"  {r['source_item_id']} @{r['source_metadata']['username']} "
                  f"{r['created_at']:%Y-%m-%d} {' '.join(r['text'].split())[:110]}")
        if len(records) < args.limit:
            print(f"[x] WARNING: only {len(records)} collectable posts (wanted {args.limit}); not padding.")

        if args.store:
            db_path = DATA_DIR / "sld.db"
            backup = db_path.with_name(f"sld.db.bak-before-x-{datetime.now():%Y%m%d%H%M%S}")
            shutil.copy2(db_path, backup)
            print(f"[x] DB backed up to {backup.name}")
            print(f"[x] upsert: {upsert_normalized_items(db, records)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
