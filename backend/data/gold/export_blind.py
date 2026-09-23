"""Phase 1 export: all 167 posts, every v1 analysis field stripped.

Writes a blind corpus for independent labeling. AAPC rows are grouped by
conversation so replies can be judged in thread context; linkedin/reddit are
standalone. Nothing from analysis_results is read at all -- the query only
touches normalized_items, which is the integrity guarantee.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = "backend/data/sld.db"
OUT_DIR = Path(sys.argv[1])
MAX_CHARS = 3500

FORBIDDEN = {
    "final_score", "score_breakdown", "rcm_relevant", "problem_evidence",
    "speaker_type", "content_stance", "seeking_level", "confidence",
    "problem_category", "evidence_quote", "first_person",
}


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # collapse runs of blank lines; keep paragraph structure
    out, blank = [], 0
    for line in s.split("\n"):
        if line.strip():
            out.append(line.rstrip())
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    t = "\n".join(out).strip()
    if len(t) > MAX_CHARS:
        t = t[:MAX_CHARS] + f"\n[...truncated, full length {len(s)} chars]"
    return t


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [
        dict(r)
        for r in con.execute(
            "select source_item_id, source, title, text, conversation_id, parent_id, "
            "author_name, url, created_at, engagement, raw_data "
            "from normalized_items order by source, conversation_id, id"
        )
    ]
    assert len(rows) == 167, f"expected 167 rows, got {len(rows)}"

    records = []
    for r in rows:
        raw = json.loads(r["raw_data"]) if r["raw_data"] else {}
        rec = {
            "source_item_id": r["source_item_id"],
            "source": r["source"],
            "title": r["title"],
            "text": clean(r["text"]),
            "conversation_id": r["conversation_id"],
            "is_reply": r["parent_id"] is not None,
            "author_name": r["author_name"],
            "subreddit": raw.get("subreddit"),
            "forum": raw.get("forum") or raw.get("category"),
        }
        assert not (FORBIDDEN & set(rec)), "v1 field leaked into blind export"
        records.append(rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "blind_corpus.json").write_text(
        json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8"
    )

    # Human-readable, thread-grouped rendering for the labeling pass.
    by_conv: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        by_conv.setdefault((rec["source"], rec["conversation_id"] or rec["source_item_id"]), []).append(rec)

    lines: list[str] = []
    n = 0
    for (src, conv), group in by_conv.items():
        lines.append("\n" + "=" * 100)
        lines.append(f"### {src.upper()} | conversation {conv} | {len(group)} post(s)")
        for rec in group:
            n += 1
            role = "REPLY" if rec["is_reply"] else "ROOT"
            ctx = rec["subreddit"] or rec["forum"] or ""
            lines.append("-" * 100)
            lines.append(f"[{n}] id={rec['source_item_id']} | {role} | {src}{' /' + ctx if ctx else ''}")
            if rec["title"]:
                lines.append(f"TITLE: {rec['title']}")
            lines.append(rec["text"] or "(no body)")
    assert n == 167, n
    (OUT_DIR / "blind_corpus.txt").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {n} posts to {OUT_DIR}")
    print("chars:", len("\n".join(lines)))
    for s in ("aapc", "linkedin", "reddit"):
        print(f"  {s}: {sum(1 for r in records if r['source'] == s)}")


if __name__ == "__main__":
    main()
