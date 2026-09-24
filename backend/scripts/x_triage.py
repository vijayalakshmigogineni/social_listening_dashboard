"""Triage helper for X discovery output: per-author tally + tweet dump.

Research aid only (not SLD scoring): the vendor flags just help decide which
accounts to open first; every selection decision is made by reading posts.

Usage (from backend/):
    python scripts/x_triage.py discovery authors
    python scripts/x_triage.py discovery tweets [--key uhc_denials] [--min-likes 5]
    python scripts/x_triage.py probes tweets --author somehandle
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DATA_DIR  # noqa: E402

RUN_DIR = DATA_DIR / "x_sourcing" / "20260924"
VENDOR_RE = re.compile(
    r"#(rcm|medicalbilling|revenuecycle|medicalcoding|healthcarebilling|denialmanagement)|"
    r"\bdm us\b|\bcontact us\b|\bbook a (demo|call)\b|\bour (team|services|experts)\b|"
    r"\bfree (audit|consultation)\b|\bwe help\b|\boutsourc", re.I)


def load(phase: str) -> list[dict]:
    rows = []
    for f in sorted((RUN_DIR / phase).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for t in d["items"]:
            t["_key"] = d["key"]
            rows.append(t)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase")
    p.add_argument("view", choices=["authors", "tweets"])
    p.add_argument("--key")
    p.add_argument("--author")
    p.add_argument("--min-likes", type=int, default=0)
    p.add_argument("--no-vendor", action="store_true")
    args = p.parse_args()

    rows = load(args.phase)
    seen = set()
    uniq = []
    for t in rows:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        uniq.append(t)
    print(f"# {len(rows)} rows, {len(uniq)} unique tweets")

    if args.view == "authors":
        agg = defaultdict(lambda: {"n": 0, "keys": set(), "vendor": 0, "likes": 0, "name": ""})
        for t in uniq:
            a = t["author"]
            g = agg[a["username"]]
            g["n"] += 1
            g["keys"].add(t["_key"])
            g["vendor"] += bool(VENDOR_RE.search(t["text"] or ""))
            g["likes"] += (t.get("metrics") or {}).get("likes") or 0
            g["name"] = a.get("name")
        for h, g in sorted(agg.items(), key=lambda x: (-x[1]["n"], -x[1]["likes"])):
            if g["n"] < 2 and not args.key:
                continue
            print(f"{h:22} n={g['n']:2} vendor={g['vendor']} likes={g['likes']:6} "
                  f"{g['name'][:28]:28} {','.join(sorted(g['keys']))}")
        return

    for t in uniq:
        if args.key and t["_key"] != args.key:
            continue
        if args.author and t["author"]["username"].lower() != args.author.lower():
            continue
        likes = (t.get("metrics") or {}).get("likes") or 0
        if likes < args.min_likes:
            continue
        vendor = bool(VENDOR_RE.search(t["text"] or ""))
        if args.no_vendor and vendor:
            continue
        text = " ".join((t["text"] or "").split())
        print(f"[{t['_key']}] @{t['author']['username']} ({t['author'].get('name')}) "
              f"{t['createdAt'][:10]} likes={likes} {'VENDOR ' if vendor else ''}"
              f"{'reply ' if t.get('replyTo') else ''}{t['url']}\n    {text[:420]}")


if __name__ == "__main__":
    main()
