"""Join the blind labels to source_item_ids and emit the gold dataset.

The index->id mapping is rebuilt exactly as export_blind.py rendered it, so
label [n] lands on the post that was displayed as [n].
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from labels import FIELDS, L  # noqa: E402

SCRATCH = Path(__file__).parent
records = json.loads((SCRATCH / "phase1" / "blind_corpus.json").read_text(encoding="utf-8"))

by_conv: dict[tuple[str, str], list[dict]] = {}
for rec in records:
    by_conv.setdefault((rec["source"], rec["conversation_id"] or rec["source_item_id"]), []).append(rec)

ordered: list[dict] = []
for group in by_conv.values():
    ordered.extend(group)
assert len(ordered) == 167
assert sorted(L) == list(range(1, 168)), "labels must cover 1..167 exactly"

gold = []
for i, rec in enumerate(ordered, 1):
    vals = dict(zip(FIELDS, L[i]))
    gold.append({
        "index": i,
        "source_item_id": rec["source_item_id"],
        "source": rec["source"],
        "conversation_id": rec["conversation_id"],
        "is_reply": rec["is_reply"],
        "title": rec["title"],
        "channel": rec["subreddit"] or rec["forum"],
        **vals,
        "label_basis": "model-proposed, blind to pipeline scores; human validation pending",
    })

out_dir = SCRATCH / "gold"
out_dir.mkdir(exist_ok=True)
(out_dir / "sld_167_gold_labels.json").write_text(
    json.dumps(gold, indent=1, ensure_ascii=False), encoding="utf-8"
)

cols = list(gold[0].keys())
with (out_dir / "sld_167_gold_labels.csv").open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(gold)

# Integrity checks the plan promised.
assert all(g["reason"] for g in gold), "every row must carry a reason"
assert all(0 <= g["human_opportunity_score"] <= 95 for g in gold)
print(f"gold rows: {len(gold)}")
low = [g for g in gold if g["human_confidence"] == "low"]
print(f"low-confidence rows flagged for spot-check: {len(low)}")
