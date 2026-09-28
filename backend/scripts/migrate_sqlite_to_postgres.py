"""Copy the SQLite database into PostgreSQL (Neon).

Usage (from backend/, with DATABASE_URL set in the repo-root .env):
    python scripts/migrate_sqlite_to_postgres.py            # target must be empty
    python scripts/migrate_sqlite_to_postgres.py --replace  # clear the target first

Source: app.config.DATABASE_PATH ("sld 1.db"), opened READ-ONLY -- it is never
modified and stays as the archive. Target: DATABASE_URL (refuses SQLite).

What is copied, in dependency order, keeping the original ids:
  normalized_items        all rows
  analysis_results        only v3 rows (sld-analysis-v3); the retired v1/v2
                          and experiment rows stay in the SQLite archive
  collection_jobs         all rows
  collection_checkpoints  all rows
  analysis_jobs           all rows, with `scores` reduced to its v3 entry

SQLite hands DateTime(timezone=True) values back naive (they were stored as
UTC); they are tagged UTC before insert so PostgreSQL does not reinterpret
them in the session time zone. Id sequences are then moved past max(id).
Finally row counts, per-source post counts and the v3 score sum are compared
source vs target; any mismatch exits non-zero.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import DateTime, create_engine, func, select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import DATABASE_PATH, DATABASE_URL, IS_SQLITE  # noqa: E402
from app.db import models  # noqa: E402,F401  (registers the tables)
from app.db.base import Base, engine as target  # noqa: E402
from app.schemas.analysis import ANALYSIS_VERSION_V3  # noqa: E402

TABLE_ORDER = [
    "normalized_items",
    "analysis_results",
    "collection_jobs",
    "collection_checkpoints",
    "analysis_jobs",
]
BATCH = 500


def source_engine():
    if not DATABASE_PATH.exists():
        raise SystemExit(f"source SQLite file not found: {DATABASE_PATH}")
    uri = f"file:{quote(DATABASE_PATH.as_posix())}?mode=ro"
    return create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True))


def source_query(table):
    q = select(table)
    if table.name == "analysis_results":
        q = q.where(table.c.analysis_version == ANALYSIS_VERSION_V3)
    return q


def transform(table, row: dict) -> dict:
    for col in table.columns:
        v = row.get(col.name)
        if isinstance(col.type, DateTime) and isinstance(v, datetime) and v.tzinfo is None:
            row[col.name] = v.replace(tzinfo=timezone.utc)
    if table.name == "analysis_jobs":
        scores = row.get("scores") or {}
        row["scores"] = {"v3": scores.get("v3", [])}
    return row


def count(conn, table, where=None) -> int:
    q = select(func.count()).select_from(table)
    if where is not None:
        q = q.where(where)
    return conn.execute(q).scalar_one()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true",
                        help="delete all rows in the target tables before copying")
    args = parser.parse_args()

    if IS_SQLITE:
        raise SystemExit("DATABASE_URL is not set to PostgreSQL -- nothing to migrate to.")
    url = make_url(DATABASE_URL)
    print(f"[migrate] source: {DATABASE_PATH} (read-only)")
    print(f"[migrate] target: {url.get_backend_name()} {url.host} / {url.database}")

    src = source_engine()
    tables = [Base.metadata.tables[name] for name in TABLE_ORDER]

    with target.connect() as conn:
        print("[migrate] target server:", conn.execute(text("select version()")).scalar_one().split(",")[0])
    Base.metadata.create_all(target)

    with target.begin() as conn:
        existing = {t.name: count(conn, t) for t in tables}
        if any(existing.values()):
            if not args.replace:
                raise SystemExit(f"[migrate] target is not empty {existing} -- rerun with --replace to overwrite")
            names = ", ".join(t.name for t in tables)
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY"))
            print(f"[migrate] cleared target tables {existing}")

    for table in tables:
        copied = 0
        with src.connect() as s_conn, target.begin() as t_conn:
            result = s_conn.execute(source_query(table)).mappings()
            while True:
                chunk = result.fetchmany(BATCH)
                if not chunk:
                    break
                t_conn.execute(table.insert(), [transform(table, dict(r)) for r in chunk])
                copied += len(chunk)
            if "id" in table.c and table.c.id.primary_key:
                t_conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"
                ))
        print(f"[migrate] {table.name}: copied {copied}")

    # ---- verification -------------------------------------------------------
    problems = []
    with src.connect() as s, target.connect() as t:
        for table in tables:
            where = (table.c.analysis_version == ANALYSIS_VERSION_V3) if table.name == "analysis_results" else None
            a, b = count(s, table, where), count(t, table)
            print(f"[verify] {table.name}: source {a} / target {b}")
            if a != b:
                problems.append(f"{table.name} count {a} != {b}")

        items = Base.metadata.tables["normalized_items"]
        per_source_q = select(items.c.source, func.count()).group_by(items.c.source)
        src_sources, tgt_sources = dict(s.execute(per_source_q).all()), dict(t.execute(per_source_q).all())
        print(f"[verify] posts per source: {dict(sorted(tgt_sources.items()))}")
        if src_sources != tgt_sources:
            problems.append(f"per-source counts differ: {src_sources} vs {tgt_sources}")

        ar = Base.metadata.tables["analysis_results"]
        sum_q = select(func.sum(ar.c.final_score)).where(ar.c.analysis_version == ANALYSIS_VERSION_V3)
        a, b = s.execute(sum_q).scalar() or 0.0, t.execute(sum_q).scalar() or 0.0
        print(f"[verify] v3 final_score sum: source {a:.4f} / target {b:.4f}")
        if abs(a - b) > 1e-6:
            problems.append(f"v3 score sum {a} != {b}")

    if problems:
        print("[migrate] FAILED verification:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("[migrate] OK -- all checks passed")


if __name__ == "__main__":
    main()
