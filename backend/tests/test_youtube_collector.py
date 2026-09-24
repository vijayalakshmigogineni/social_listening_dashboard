"""
YouTube collector: normalization, video/comment dedup, error resilience and
config shape. No network -- run_actor_sync is monkeypatched, and the DB is
an isolated in-memory SQLite, never backend/data/sld.db.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors import youtube
from app.collectors.apify_client import ApifyRunError
from app.collectors.common import upsert_normalized_items
from app.db.base import Base
from app.db.models import NormalizedItem  # noqa: F401  (registers the table on Base.metadata)

NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def _video(video_id="vid1", query="medical claim denial", **extra):
    return {
        "type": "video",
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": "How to Handle UnitedHealthcare Claim Denials",
        "date": "2026-05-01T00:00:00.000Z",
        "channelName": "RCM Channel",
        "channelUrl": "https://www.youtube.com/@RCMChannel",
        "channelId": "UC123",
        "viewCount": 1000,
        "likes": 50,
        "commentsCount": 12,
        "commentsTurnedOff": False,
        "text": "Video description",
        "input": query,
        **extra,
    }


def _comment(cid="Ugx1", video_id="vid1", text=None, reply_to=None, when="2 weeks ago"):
    return {
        "cid": cid,
        "replyToCid": reply_to,
        "type": "comment",
        "publishedTimeText": when,
        "comment": text if text is not None else (
            "Our practice has been getting repeated UHC denials for months. Anyone else?"
        ),
        "author": "@biller42",
        "authorIsChannelOwner": False,
        "replyCount": 2,
        "voteCount": 7,
        "hasCreatorHeart": False,
        "videoId": video_id,
        "title": "How to Handle UnitedHealthcare Claim Denials",
    }


def _entry(video):
    return {**video, "_queries": [video["input"]], "_families": ["claims_denials"]}


# --- normalization -------------------------------------------------------------

def test_normalize_comment_maps_to_canonical_fields():
    rec = youtube.normalize_comment(_comment(), _entry(_video()), NOW)

    assert rec["source"] == "youtube"
    assert rec["source_item_id"] == "Ugx1"
    assert rec["url"] == "https://www.youtube.com/watch?v=vid1&lc=Ugx1"
    assert rec["title"] == "How to Handle UnitedHealthcare Claim Denials"
    assert rec["text"].startswith("Our practice has been getting repeated UHC denials")
    assert rec["author_profile_url"] == "https://www.youtube.com/@biller42"
    assert rec["conversation_id"] == "vid1"
    assert rec["parent_id"] is None
    assert rec["media_type"] == "comment"
    assert rec["created_at"] == NOW - timedelta(days=14)

    meta = rec["source_metadata"]
    assert meta["video_id"] == "vid1"
    assert meta["channel_name"] == "RCM Channel"
    assert meta["discovery_queries"] == ["medical claim denial"]
    assert meta["is_reply"] is False
    assert meta["created_at_is_approximate"] is True


def test_reply_keeps_parent_relationship():
    rec = youtube.normalize_comment(
        _comment(cid="Ugx1.abc", reply_to="Ugx1", text="Same issue here"), _entry(_video()), NOW
    )
    assert rec["parent_id"] == "Ugx1"
    assert rec["source_metadata"]["parent_comment_id"] == "Ugx1"
    assert rec["source_metadata"]["is_reply"] is True


def test_keywords_come_from_comment_text_not_video_title():
    """The video title mentions claim denials; 'Great explanation!' does not."""
    rec = youtube.normalize_comment(_comment(text="Great explanation!"), _entry(_video()), NOW)
    assert rec["source_metadata"]["matched_rcm_keywords"] == []


@pytest.mark.parametrize(
    "text,days",
    [("3 days ago", 3), ("1 week ago", 7), ("2 months ago (edited)", 60), ("1 year ago", 365)],
)
def test_parse_relative_time(text, days):
    assert youtube.parse_relative_time(text, NOW) == NOW - timedelta(days=days)


def test_parse_relative_time_unparseable_is_none():
    assert youtube.parse_relative_time("yesterday-ish", NOW) is None
    assert youtube.parse_relative_time(None, NOW) is None


# --- dedup ---------------------------------------------------------------------

def test_same_video_from_two_queries_is_merged_once(monkeypatch):
    families = {"claims_denials": ["medical claim denial"], "payers": ["UnitedHealthcare claim denial"]}
    responses = {
        "claims_denials": [_video(query="medical claim denial")],
        "payers": [_video(query="UnitedHealthcare claim denial"), _video("vid2", "UnitedHealthcare claim denial")],
    }

    def fake_run(actor_id, run_input, **kw):
        family = "claims_denials" if run_input["searchQueries"] == families["claims_denials"] else "payers"
        return responses[family]

    monkeypatch.setattr(youtube, "run_actor_sync", fake_run)
    videos = youtube.discover_videos(families)

    assert set(videos) == {"vid1", "vid2"}
    assert videos["vid1"]["_queries"] == ["medical claim denial", "UnitedHealthcare claim denial"]
    assert videos["vid1"]["_families"] == ["claims_denials", "payers"]


def test_same_comment_twice_and_rerun_upserts_to_one_row():
    entry = _entry(_video())
    rec_a = youtube.normalize_comment(_comment(), entry, NOW)
    rec_b = youtube.normalize_comment(_comment(), entry, NOW)

    session = _make_session()
    try:
        first = upsert_normalized_items(session, [rec_a, rec_b])
        rerun = upsert_normalized_items(session, [youtube.normalize_comment(_comment(), entry, NOW)])
        rows = session.query(NormalizedItem).filter_by(source="youtube").count()
    finally:
        session.close()

    assert rows == 1
    assert first == {"inserted": 1, "updated": 1, "skipped": 0}
    assert rerun == {"inserted": 0, "updated": 1, "skipped": 0}


# --- collection flow / error handling -------------------------------------------

def test_collect_skips_commentless_videos_and_survives_failed_chunks(monkeypatch):
    monkeypatch.setattr(youtube, "VIDEOS_PER_COMMENT_RUN", 1)
    videos = [
        _video("vid1"),
        _video("vid2"),
        _video("off", commentsTurnedOff=True),
        _video("zero", commentsCount=0),
    ]
    comment_calls = []

    def fake_run(actor_id, run_input, **kw):
        if actor_id == youtube.SEARCH_ACTOR_ID:
            return videos
        url = run_input["startUrls"][0]["url"]
        comment_calls.append(url)
        if url.endswith("vid1"):
            raise ApifyRunError("actor run failed")
        return [
            _comment("Ugx2", "vid2"),
            _comment("Ugx2", "vid2"),        # duplicate within the run
            _comment("Ugx3", "vid2", text=""),  # deleted / empty
            {"videoId": "vid2", "comment": "no id"},
        ]

    monkeypatch.setattr(youtube, "run_actor_sync", fake_run)
    records = youtube.collect_families({"claims_denials": ["medical claim denial"]})

    assert len(comment_calls) == 2  # comments-off and zero-comment videos never fetched
    assert [r["source_item_id"] for r in records] == ["Ugx2"]


def test_failed_discovery_family_does_not_stop_others(monkeypatch):
    def fake_run(actor_id, run_input, **kw):
        if run_input["searchQueries"] == ["bad"]:
            raise ApifyRunError("boom")
        return [_video("vid9", "good")]

    monkeypatch.setattr(youtube, "run_actor_sync", fake_run)
    videos = youtube.discover_videos({"a": ["bad"], "b": ["good"]})
    assert list(videos) == ["vid9"]


def test_max_videos_total_caps_comment_fetch(monkeypatch):
    fetched = []

    def fake_run(actor_id, run_input, **kw):
        if actor_id == youtube.SEARCH_ACTOR_ID:
            return [_video(f"v{i}") for i in range(5)]
        fetched.extend(u["url"] for u in run_input["startUrls"])
        return []

    monkeypatch.setattr(youtube, "run_actor_sync", fake_run)
    youtube.collect_families({"f": ["q"]}, max_videos_total=2)
    assert len(fetched) == 2


def test_invalid_video_date_filter_rejected():
    with pytest.raises(ValueError):
        youtube.collect_families({"f": ["q"]}, video_date_filter="decade")


# --- config shape ----------------------------------------------------------------

def test_query_families_cover_required_themes():
    assert {"medical_billing", "claims_denials", "prior_authorization", "payers",
            "practice_operations"} <= set(youtube.QUERY_FAMILIES)
    assert sum(len(q) for q in youtube.QUERY_FAMILIES.values()) >= 15


def test_payer_queries_are_paired_with_an_rcm_term():
    payers = ("unitedhealthcare", "aetna", "cigna", "humana", "medicare", "medicaid", "blue cross")
    for q in youtube.QUERY_FAMILIES["payers"]:
        lowered = q.lower()
        assert any(p in lowered for p in payers)
        assert len(lowered.split()) >= 2 and not any(lowered == p for p in payers)
