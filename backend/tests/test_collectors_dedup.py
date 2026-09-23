"""
LinkedIn query-family dedup: two query families can legitimately return the
same post (same urn). Confirms the existing (source, source_item_id) upsert
identity in collectors/common.py already collapses that into one row, with
no new dedup mechanism needed -- run against an isolated in-memory DB, never
the real backend/data/sld.db.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.common import upsert_normalized_items
from app.collectors.linkedin import normalize_post
from app.db.base import Base
from app.db.models import NormalizedItem  # noqa: F401  (registers the table on Base.metadata)


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def _raw_post(urn: str) -> dict:
    return {
        "urn": urn,
        "text": "Our billing team is looking for a better way to handle denials.",
        "url": f"https://www.linkedin.com/feed/update/{urn}",
        "postedAtISO": "2026-09-20T00:00:00.000Z",
        "author": {"id": "u1", "name": "Jane Biller"},
    }


def test_same_post_from_two_query_families_upserts_to_one_row():
    same_post = _raw_post("urn:li:activity:12345")
    record_a = normalize_post(same_post, search_query="practice_voice family")
    record_b = normalize_post(same_post, search_query="denials_reimbursement family")
    assert record_a["source_item_id"] == record_b["source_item_id"]

    session = _make_session()
    try:
        summary = upsert_normalized_items(session, [record_a, record_b])
        row_count = session.query(NormalizedItem).count()
    finally:
        session.close()

    assert row_count == 1
    assert summary["inserted"] == 1
    assert summary["updated"] == 1
