"""Store hand-selected Facebook posts from already-downloaded raw actor output.

Usage (from backend/):
    python scripts/ingest_facebook_selection.py --dir data/facebook_sourcing/20260924 [--dry-run]

Reads <dir>/evaluation.json ("selected": [{post_id, group_key, ...}] and
"raw_files": [...]) and the raw apify/facebook-groups-scraper items in those
files, then normalizes each selected post with the collector's own
facebook.normalize_post and upserts it with the shared
upsert_normalized_items -- same schema and (source, source_item_id) dedup as a
normal collection run, without paying for a second Apify run.

Only selected ids are stored. A selected id that is not in the raw files, or
not a real post, is reported and skipped -- never reconstructed. Posts already
in the DB are skipped, so re-running is a no-op.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items  # noqa: E402
from app.collectors.facebook import is_collectable, normalize_post, post_id  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.models import NormalizedItem  # noqa: E402


def index_raw(raw_payloads: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for payload in raw_payloads:
        for item in payload.get("items", []):
            pid = post_id(item)
            if pid and pid not in index:
                index[pid] = item
    return index


def build_records(selection: list[dict], raw_index: dict[str, dict], stored_ids: set[str]) -> dict:
    records, missing, not_post, already = [], [], [], []
    for entry in selection:
        pid = str(entry["post_id"])
        if pid in stored_ids:
            already.append(pid)
            continue
        item = raw_index.get(pid)
        if item is None:
            missing.append(pid)
            continue
        if not is_collectable(item):
            not_post.append(pid)
            continue
        records.append(normalize_post(item, entry["group_key"]))
    return {"records": records, "missing": missing, "not_post": not_post, "already_stored": already}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    evaluation = json.loads((args.dir / "evaluation.json").read_text(encoding="utf-8"))
    raw = [json.loads((args.dir / f).read_text(encoding="utf-8")) for f in evaluation["raw_files"]]
    raw_index = index_raw(raw)

    db = SessionLocal()
    try:
        stored = {sid for (sid,) in db.query(NormalizedItem.source_item_id).filter_by(source="facebook").all()}
        result = build_records(evaluation["selected"], raw_index, stored)
        print(f"selected {len(evaluation['selected'])}: to store {len(result['records'])}, "
              f"already stored {len(result['already_stored'])}, missing from raw {result['missing']}, "
              f"not a post {result['not_post']}")
        if not args.dry_run and result["records"]:
            print(f"DB upsert summary: {upsert_normalized_items(db, result['records'])}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
