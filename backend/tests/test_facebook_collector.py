"""
Facebook collector: normalization into the canonical schema, the 20-post
round-robin selection, de-duplication, and DB upsert identity. No network --
the Apify call is mocked, and the DB is an isolated in-memory SQLite.

The raw post shape mirrors real apify/facebook-groups-scraper output recorded
in testing/problem-intelligence/facebook/fb_prior_runs_inspection.json.
"""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors import facebook
from app.collectors.common import upsert_normalized_items
from app.db.base import Base
from app.db.models import NormalizedItem
from app.schemas.normalized import NormalizedItem as NormalizedSchema


def _raw(legacy_id: str, text: str = "We have claims denying for 64492. Any help?",
         group: str = "290657479460430", **extra) -> dict:
    post = {
        "facebookUrl": f"https://www.facebook.com/groups/{group}",
        "url": f"https://www.facebook.com/groups/{group}/permalink/{legacy_id}/",
        "time": "2026-09-18T23:33:37.000Z",
        "user": {"id": "u-" + legacy_id, "name": "Anon Biller"},
        "text": text,
        "id": "UzpfSTEy" + legacy_id,
        "legacyId": legacy_id,
        "likesCount": 1,
        "commentsCount": 4,
        "sharesCount": 0,
        "facebookId": group,
        "groupTitle": "PM&R and Interventional Pain Management Coding and Billing",
        "inputUrl": f"https://www.facebook.com/groups/{group}",
    }
    post.update(extra)
    return post


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_normalize_maps_fields_and_passes_canonical_schema():
    record = facebook.normalize_post(_raw("1619623016563863"), "pmr_interventional_pain_billing")
    NormalizedSchema(**record)  # raises on any schema violation

    assert record["source"] == "facebook"
    assert record["source_item_id"] == "1619623016563863"
    assert record["url"].endswith("/permalink/1619623016563863/")
    assert record["author_name"] == "Anon Biller"
    assert record["author_profile_url"] is None  # never constructed
    assert record["created_at"].year == 2026 and record["created_at"].tzinfo is not None
    assert record["engagement"] == {"likes": 1, "comments": 4, "shares": 0}
    meta = record["source_metadata"]
    assert meta["group_id"] == "290657479460430"
    assert meta["group_key"] == "pmr_interventional_pain_billing"
    assert "denying" not in meta["matched_rcm_keywords"]  # keywords come from the lexicon only
    assert "claims" in meta["matched_rcm_keywords"]


def test_post_id_prefers_stable_legacy_id_over_base64_id():
    assert facebook.post_id(_raw("111")) == "111"
    no_legacy = _raw("222")
    del no_legacy["legacyId"]
    assert facebook.post_id(no_legacy) == "UzpfSTEy222"


def test_error_rows_and_textless_posts_are_not_collectable():
    assert not facebook.is_collectable({"url": "https://www.facebook.com/groups/x",
                                        "error": "no_items"})
    assert not facebook.is_collectable(_raw("333", text="   "))
    no_ids = _raw("444")
    for key in ("legacyId", "id"):
        del no_ids[key]
    assert not facebook.is_collectable(no_ids)
    assert facebook.is_collectable(_raw("555"))


def test_select_posts_round_robins_dedups_and_caps_at_limit():
    raw_by_group = {
        "a": [_raw(f"a{i}", group="1") for i in range(15)],
        "b": [_raw(f"b{i}", group="2") for i in range(3)] + [_raw("a0", group="1")],
        "c": [{"error": "no_items"}],
    }
    selected = facebook.select_posts(raw_by_group, limit=10)
    ids = [r["source_item_id"] for r in selected]

    assert len(selected) == 10
    assert len(set(ids)) == 10
    assert ids[:6] == ["a0", "b0", "a1", "b1", "a2", "b2"]  # interleaved, not group-by-group
    assert ids.count("a0") == 1


def test_select_posts_top_up_skips_already_stored_ids():
    raw = {"a": [_raw("1"), _raw("2"), _raw("3")]}
    selected = facebook.select_posts(raw, limit=1, exclude_ids={"1", "2"})
    assert [r["source_item_id"] for r in selected] == ["3"]


def test_select_posts_does_not_pad_when_short():
    selected = facebook.select_posts({"a": [_raw("1"), _raw("2")]}, limit=20)
    assert len(selected) == 2


def test_collect_runs_actor_once_per_group_with_charge_cap():
    groups = {"g1": "https://www.facebook.com/groups/1", "g2": "https://www.facebook.com/groups/2"}
    fake = {
        "https://www.facebook.com/groups/1": [_raw(f"x{i}", group="1") for i in range(5)],
        "https://www.facebook.com/groups/2": [_raw(f"y{i}", group="2") for i in range(5)],
    }
    calls = []

    def fake_run(actor_id, run_input, **kwargs):
        calls.append((actor_id, run_input, kwargs))
        return fake[run_input["startUrls"][0]["url"]]

    with patch.object(facebook, "run_actor_sync", side_effect=fake_run):
        records = facebook.collect(groups=groups, limit=6, per_group=5)

    assert len(calls) == 2
    assert all(c[0] == "apify/facebook-groups-scraper" for c in calls)
    assert all(c[2]["max_total_charge_usd"] == facebook.MAX_CHARGE_PER_RUN_USD for c in calls)
    assert all(c[1]["resultsLimit"] == 5 for c in calls)
    assert len(records) == 6


def test_same_post_collected_twice_upserts_to_one_row():
    record_a = facebook.normalize_post(_raw("777"), "g1")
    record_b = facebook.normalize_post(_raw("777", text="edited text, same post"), "g1")

    session = _session()
    try:
        first = upsert_normalized_items(session, [record_a])
        second = upsert_normalized_items(session, [record_b])
        rows = session.query(NormalizedItem).filter_by(source="facebook").all()
    finally:
        session.close()

    assert first == {"inserted": 1, "updated": 0, "skipped": 0}
    assert second == {"inserted": 0, "updated": 1, "skipped": 0}
    assert len(rows) == 1
    assert rows[0].text == "edited text, same post"
