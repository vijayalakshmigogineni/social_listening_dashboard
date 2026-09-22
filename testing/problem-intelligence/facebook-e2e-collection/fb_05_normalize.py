"""
STEP 5 -- NORMALIZATION into the fixed canonical schema.

ONE pipeline normalizes all four Facebook record shapes:

    discovered search posts   (scrapesmith, searchType=posts)
    discovered pages          (scrapesmith, searchType=pages)
    discovered groups         (scrapesmith, searchType=groups)
    page posts                (thedoor/facebook-page-scraper)
    group posts               (whatever step 3 established was actually collectible)
    comments                  (apify/facebook-comments-scraper)

    -> facebook_normalized_records.json
    -> facebook_field_completeness.json

RULES FOLLOWED
  * The canonical schema is fixed. No field is added, renamed or removed.
  * NO intelligence fields. Nothing here classifies, scores or tags anything.
  * Missing data is null. Nothing is guessed and no URL is ever constructed --
    every url/profile url emitted came verbatim from the source record.
  * raw_data holds the COMPLETE original Apify record.
  * source_metadata holds Facebook-specific extras, including content_type.

Run:  python fb_05_normalize.py
"""

import base64
import json
from datetime import datetime, timezone

from fb_common import HERE, now_iso, save, load

CANONICAL_FIELDS = [
    "source", "source_item_id", "url", "title", "text",
    "author_id", "author_name", "author_profile_url",
    "author_role",
    "organization_name", "organization_url",
    "location",
    "created_at", "collected_at",
    "engagement",
    "parent_id", "conversation_id",
    "media_type",
    "raw_data", "source_metadata",
]

# Fields the intelligence layer owns. Asserted absent so a later edit cannot
# quietly leak classification into the collection phase.
FORBIDDEN_FIELDS = [
    "rcm_relevant", "problem_evidence", "first_person", "problem_category",
    "procedure_tags", "payer_tags", "denial_reason_tags",
    "pain_management_relevant", "seeking_level", "evidence_quote",
    "classification_reason", "classification_version",
]


# ---------------------------------------------------------------- helpers

def blank():
    return {f: None for f in CANONICAL_FIELDS}


def iso_from_epoch(v):
    """Epoch seconds or milliseconds -> ISO-8601 UTC. None-safe."""
    if v in (None, "", 0):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n > 1e11:          # milliseconds
        n /= 1000.0
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def iso_from_string(v):
    """Pass through an already-ISO timestamp; normalise 'Z' to +00:00."""
    if not v:
        return None
    s = str(v).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(
            timezone.utc).isoformat()
    except ValueError:
        return s or None


def clean(v):
    """Empty string / empty container -> None, so completeness counts are honest."""
    if v in ("", [], {}):
        return None
    return v


def engagement(likes=None, comments=None, shares=None, views=None):
    """
    Canonical engagement block. Returns None when Facebook gave us nothing,
    so 'no engagement data' and 'zero engagement' stay distinguishable.
    """
    def num(x):
        if x in (None, ""):
            return None
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return None

    e = {"likes": num(likes), "comments": num(comments),
         "shares": num(shares), "views": num(views)}
    return e if any(v is not None for v in e.values()) else None


def decode_comment_id(b64_id):
    """
    Apify comment `id` is base64 of 'comment:<postId>_<commentId>'.

    This matters: for a REPLY the top-level `commentId` field holds the PARENT
    comment's id, so two different replies under one parent carry an identical
    `commentId`. Using it as source_item_id would collide. The decoded suffix is
    the reply's own id.
    """
    if not b64_id:
        return None, None
    try:
        dec = base64.b64decode(b64_id).decode("utf-8", "replace")
    except Exception:                                   # noqa: BLE001
        return None, None
    if ":" not in dec:
        return None, None
    body = dec.split(":", 1)[1]
    if "_" in body:
        post_id, own_id = body.split("_", 1)
        return post_id or None, own_id or None
    return None, body or None


def group_id_from_url(url):
    """Extract a group id/slug from a /groups/<id>/... url. Never invents one."""
    s = str(url or "")
    if "/groups/" not in s:
        return None
    tail = s.split("/groups/", 1)[1]
    gid = tail.split("/", 1)[0].split("?", 1)[0]
    return gid or None


def media_type_from_search_post(rec):
    if rec.get("video"):
        return "video"
    if "/reel/" in str(rec.get("url") or ""):
        return "reel"
    if rec.get("image") or (rec.get("imagesCount") or 0) > 0:
        return "image"
    if rec.get("text"):
        return "text"
    return None


def followers_text(snippet):
    """
    The follower/member count exists only inside a display string such as
    'Product/service - 286 followers'. It is NOT a structured field. We keep the
    raw string and a parsed number in source_metadata, clearly marked derived,
    and leave the canonical fields alone.
    """
    if not snippet:
        return None, None
    for tok in str(snippet).replace("·", " ").split():
        t = tok.upper().replace(",", "")
        try:
            if t.endswith("K"):
                return snippet, int(float(t[:-1]) * 1000)
            if t.endswith("M"):
                return snippet, int(float(t[:-1]) * 1_000_000)
            if t.isdigit():
                return snippet, int(t)
        except ValueError:
            continue
    return snippet, None


def provenance(block):
    run = (block or {}).get("run") or {}
    return {
        "actor_slug": run.get("actor_slug"),
        "actor_run_id": run.get("run_id"),
        "dataset_id": run.get("dataset_id"),
        "run_finished_at": run.get("finished_at"),
    }


def collected_at_for(block):
    run = (block or {}).get("run") or {}
    return (iso_from_string(run.get("finished_at"))
            or iso_from_string((block or {}).get("produced_at"))
            or now_iso())


# ---------------------------------------------------------------- mappers

def norm_search_post(rec, block):
    author = rec.get("author") or {}
    r = blank()
    r["source"] = "facebook"
    r["source_item_id"] = clean(rec.get("postId"))
    r["url"] = clean(rec.get("url"))
    # Facebook posts have no title field. Not invented.
    r["title"] = None
    r["text"] = clean(rec.get("text"))
    r["author_id"] = clean(author.get("id") or rec.get("facebookId"))
    r["author_name"] = clean(rec.get("authorName") or author.get("name") or rec.get("name"))
    r["author_profile_url"] = clean(author.get("url"))
    r["author_role"] = None
    r["organization_name"] = None
    r["organization_url"] = None
    r["location"] = None
    r["created_at"] = iso_from_epoch(rec.get("timestamp"))
    r["collected_at"] = collected_at_for(block)
    r["engagement"] = engagement(rec.get("reactionsCount"), rec.get("commentsCount"),
                                 rec.get("sharesCount"), rec.get("videoViewCount"))
    r["parent_id"] = None
    r["conversation_id"] = clean(rec.get("postId"))
    r["media_type"] = media_type_from_search_post(rec)
    r["raw_data"] = rec

    gid = group_id_from_url(rec.get("url"))
    r["source_metadata"] = {
        "content_type": "group" if gid else "post",
        "content_subtype": "group_post_via_search" if gid else "search_post",
        "discovery_query": clean(rec.get("query")),
        "facebook_group_id": gid,
        "facebook_post_id": clean(rec.get("postId")),
        "facebook_actor_id": clean(rec.get("facebookId")),
        "reaction_breakdown": clean(rec.get("reactions")),
        "images_count": rec.get("imagesCount"),
        "external_url": clean(rec.get("externalUrl")),
        "author_profile_picture_url": clean(author.get("profile_picture_url")),
        "record_type_reported_by_actor": clean(rec.get("type")),
        **provenance(block),
    }
    return r


def norm_entity(rec, block, kind):
    """A discovered PAGE or GROUP entity (not a post)."""
    snip, parsed = followers_text(rec.get("snippet"))
    is_page = kind == "page"
    r = blank()
    r["source"] = "facebook"
    r["source_item_id"] = clean(rec.get("facebookId"))
    r["url"] = clean(rec.get("url") or rec.get("profileUrl"))
    r["title"] = clean(rec.get("name"))
    # A page/group listing has no post body. Its description is the only prose
    # the source gives, so that is what goes in text.
    r["text"] = clean(rec.get("description") or rec.get("snippet"))
    r["author_id"] = clean(rec.get("facebookId"))
    r["author_name"] = clean(rec.get("name"))
    r["author_profile_url"] = clean(rec.get("profileUrl"))
    r["author_role"] = None
    # A Facebook PAGE is an organisation account, so its name/url ARE the
    # organisation directly. A GROUP is a community, not an organisation --
    # left null rather than stretched to fit.
    r["organization_name"] = clean(rec.get("name")) if is_page else None
    r["organization_url"] = clean(rec.get("url")) if is_page else None
    # Address text appears inside the snippet display string, never as a
    # structured field. Parsing it would be a guess, so location stays null and
    # the raw snippet is preserved in source_metadata instead.
    r["location"] = None
    r["created_at"] = None      # search results carry no creation timestamp
    r["collected_at"] = collected_at_for(block)
    r["engagement"] = None      # followers/members are not likes/comments/shares/views
    r["parent_id"] = None
    r["conversation_id"] = None
    r["media_type"] = None
    r["raw_data"] = rec
    r["source_metadata"] = {
        "content_type": kind,
        "content_subtype": f"discovered_{kind}",
        "discovery_query": clean(rec.get("query")),
        "snippet_raw": clean(snip),
        "followers_or_members_parsed_from_snippet": parsed,
        "followers_or_members_is_derived": parsed is not None,
        "is_verified": rec.get("isVerified"),
        "profile_image_url": clean((rec.get("image") or {}).get("uri")),
        "record_type_reported_by_actor": clean(rec.get("type")),
        **provenance(block),
    }
    return r


def norm_page_post(rec, block):
    post = rec.get("post") or {}
    page = rec.get("page") or {}
    eng = rec.get("engagement") or {}
    created = rec.get("created") or {}
    media = rec.get("media") or []
    video = rec.get("video") or {}

    mt = None
    if video.get("is_video"):
        mt = "video"
    elif media:
        mt = clean((media[0] or {}).get("media_type")) or "image"
    elif post.get("text"):
        mt = "text"

    r = blank()
    r["source"] = "facebook"
    r["source_item_id"] = clean(post.get("id"))
    r["url"] = clean(post.get("url"))
    r["title"] = None
    r["text"] = clean(post.get("text"))
    r["author_id"] = clean(page.get("id"))
    r["author_name"] = clean(page.get("name"))
    r["author_profile_url"] = clean(page.get("url"))
    r["author_role"] = None
    r["organization_name"] = clean(page.get("name"))
    r["organization_url"] = clean(page.get("url"))
    r["location"] = None
    r["created_at"] = (iso_from_epoch(created.get("timestamp"))
                       or iso_from_string(created.get("time")))
    r["collected_at"] = collected_at_for(block)
    r["engagement"] = engagement(eng.get("reactions"), eng.get("comments"),
                                 eng.get("shares"), eng.get("views"))
    r["parent_id"] = None
    r["conversation_id"] = clean(post.get("id"))
    r["media_type"] = mt
    r["raw_data"] = rec
    r["source_metadata"] = {
        "content_type": "post",
        "content_subtype": "page_post",
        "discovery_query": None,
        "facebook_page_id": clean(page.get("id")),
        "facebook_post_id": clean(post.get("id")),
        "feedback_id": clean(post.get("feedback_id")),
        "post_type_reported_by_actor": clean(post.get("type")),
        "hashtags": clean(post.get("hashtags")),
        "reaction_breakdown": clean(eng.get("reaction_breakdown")),
        "is_paid_partnership": (rec.get("partnership") or {}).get("paid"),
        "text_references": clean((rec.get("references") or {}).get("text_references")),
        "video_transcript": clean(video.get("transcript")),
        **provenance(block),
    }
    return r


def norm_comment(rec, block):
    author = rec.get("author") or {}
    post_id, own_id = decode_comment_id(rec.get("id"))
    _, parent_comment_id = decode_comment_id(rec.get("replyToCommentId"))
    depth = rec.get("threadingDepth")
    try:
        depth = int(depth) if depth not in (None, "") else None
    except (TypeError, ValueError):
        depth = None

    parent_post_id = post_id or clean(rec.get("facebookId"))

    att = rec.get("attachments") or []
    mt = "text"
    if att:
        tn = str((att[0] or {}).get("__typename") or "").lower()
        mt = "video" if "video" in tn else "image"

    r = blank()
    r["source"] = "facebook"
    # NOT rec['commentId'] -- for a reply that field holds the PARENT's id and
    # collides across sibling replies. The decoded id is the comment's own id.
    r["source_item_id"] = own_id or clean(rec.get("commentId"))
    r["url"] = clean(rec.get("commentUrl"))
    # The actor supplies a field literally named postTitle; it carries the parent
    # post's text, which is exactly the parent context the brief asks to keep.
    # It is source-provided, not invented.
    r["title"] = clean(rec.get("postTitle"))
    r["text"] = clean(rec.get("text"))
    r["author_id"] = clean(rec.get("profileId") or author.get("id"))
    r["author_name"] = clean(rec.get("profileName") or author.get("name"))
    r["author_profile_url"] = clean(rec.get("profileUrl") or author.get("url"))
    r["author_role"] = None
    r["organization_name"] = None
    r["organization_url"] = None
    r["location"] = None
    r["created_at"] = iso_from_string(rec.get("date"))
    r["collected_at"] = collected_at_for(block)
    # commentsCount on a comment = number of replies to it.
    r["engagement"] = engagement(rec.get("likesCount"), rec.get("commentsCount"))
    # A top-level comment's parent is the post; a reply's parent is its comment.
    r["parent_id"] = parent_comment_id if depth else parent_post_id
    r["conversation_id"] = parent_post_id
    r["media_type"] = mt
    r["raw_data"] = rec
    r["source_metadata"] = {
        "content_type": "comment",
        "content_subtype": "comment_reply" if depth else "comment_top_level",
        "threading_depth": depth,
        "parent_post_id": parent_post_id,
        "parent_post_url": clean(rec.get("facebookUrl")),
        "parent_post_text": clean(rec.get("postTitle")),
        "parent_comment_id": parent_comment_id,
        "reply_to_comment_id_raw": clean(rec.get("replyToCommentId")),
        "comment_id_field_from_actor": clean(rec.get("commentId")),
        "group_title": clean(rec.get("groupTitle")),
        "facebook_group_id": group_id_from_url(rec.get("facebookUrl")),
        "feedback_id": clean(rec.get("feedbackId")),
        "input_url": clean(rec.get("inputUrl")),
        "author_is_verified": author.get("is_verified"),
        "attachments_count": len(att),
        **provenance(block),
    }
    return r


# ---------------------------------------------------------------- pipeline

def normalize_all():
    out = []
    counts = {}

    def add(records, fn, label, block):
        n = 0
        for rec in records or []:
            if not isinstance(rec, dict):
                continue
            out.append(fn(rec, block))
            n += 1
        counts[label] = n
        print(f"  {label:<28} {n:>4} records")

    b = load(HERE / "facebook_raw_search_posts.json")
    add((b or {}).get("records"), norm_search_post, "search posts", b)

    b = load(HERE / "facebook_raw_pages.json")
    add((b or {}).get("records"), lambda r, blk: norm_entity(r, blk, "page"),
        "discovered pages", b)

    b = load(HERE / "facebook_raw_groups.json")
    add((b or {}).get("records"), lambda r, blk: norm_entity(r, blk, "group"),
        "discovered groups", b)

    b = load(HERE / "facebook_raw_page_posts.json")
    add((b or {}).get("records"), norm_page_post, "page posts", b)

    # Group posts: whichever path step 3 proved. If targeted retrieval failed,
    # these are the group posts surfaced by keyword search -- same shape as a
    # search post, so the same mapper applies.
    b = load(HERE / "facebook_raw_group_posts.json")
    grecs = (b or {}).get("records") or []
    if grecs and "post" in (grecs[0] or {}):
        add(grecs, norm_page_post, "group posts", b)
    else:
        add(grecs, norm_search_post, "group posts", b)

    b = load(HERE / "facebook_raw_comments.json")
    add((b or {}).get("records"), norm_comment, "comments", b)

    return out, counts


def dedupe(records):
    """Dedupe on (content_type, source_item_id), url as fallback."""
    seen, kept, dupes = {}, [], []
    for r in records:
        ct = (r.get("source_metadata") or {}).get("content_type")
        key = f"{ct}:{r.get('source_item_id')}" if r.get("source_item_id") \
            else f"{ct}:URL:{r.get('url')}"
        if key in seen:
            dupes.append({"key": key, "url": r.get("url")})
            continue
        seen[key] = True
        kept.append(r)
    return kept, dupes


def completeness(records):
    """Field | Available | Missing | Percentage, overall and per content_type."""
    total = len(records)
    rows = []
    for f in CANONICAL_FIELDS:
        avail = sum(1 for r in records if r.get(f) not in (None, "", [], {}))
        rows.append({
            "field": f,
            "available": avail,
            "missing": total - avail,
            "percentage": round(100.0 * avail / total, 1) if total else 0.0,
        })

    by_type = {}
    for r in records:
        ct = (r.get("source_metadata") or {}).get("content_type") or "unknown"
        by_type.setdefault(ct, []).append(r)

    per_type = {}
    for ct, recs in sorted(by_type.items()):
        n = len(recs)
        per_type[ct] = {
            "record_count": n,
            "fields": [{
                "field": f,
                "available": sum(1 for r in recs if r.get(f) not in (None, "", [], {})),
                "missing": n - sum(1 for r in recs if r.get(f) not in (None, "", [], {})),
                "percentage": round(
                    100.0 * sum(1 for r in recs if r.get(f) not in (None, "", [], {})) / n, 1
                ) if n else 0.0,
            } for f in CANONICAL_FIELDS],
        }
    return rows, per_type


def validate(records):
    """Schema is fixed and no intelligence field may appear."""
    problems = []
    for i, r in enumerate(records):
        extra = set(r) - set(CANONICAL_FIELDS)
        missing = set(CANONICAL_FIELDS) - set(r)
        if extra:
            problems.append({"index": i, "issue": "extra field", "fields": sorted(extra)})
        if missing:
            problems.append({"index": i, "issue": "missing field", "fields": sorted(missing)})
        leaked = [f for f in FORBIDDEN_FIELDS if f in r]
        if leaked:
            problems.append({"index": i, "issue": "intelligence field present",
                             "fields": leaked})
    return problems


def main():
    print(f"=== STEP 5: NORMALIZATION ({now_iso()}) ===")
    records, counts = normalize_all()
    print(f"\n  total normalized: {len(records)}")

    records, dupes = dedupe(records)
    print(f"  after dedupe    : {len(records)}  ({len(dupes)} duplicates removed)")

    problems = validate(records)
    print(f"  schema problems : {len(problems)}")
    if problems:
        print(json.dumps(problems[:5], indent=2))

    rows, per_type = completeness(records)

    save(HERE / "facebook_normalized_records.json", {
        "schema_version": "canonical-v1 (fixed, unmodified)",
        "produced_at": now_iso(),
        "scope": "COLLECTION + NORMALIZATION ONLY. No intelligence fields populated.",
        "canonical_fields": CANONICAL_FIELDS,
        "intelligence_fields_deliberately_absent": FORBIDDEN_FIELDS,
        "record_count": len(records),
        "counts_by_source_step": counts,
        "duplicates_removed": dupes,
        "schema_validation_problems": problems,
        "records": records,
    })

    save(HERE / "facebook_field_completeness.json", {
        "produced_at": now_iso(),
        "total_records": len(records),
        "overall": rows,
        "by_content_type": per_type,
    })

    print("\n=== FIELD COMPLETENESS (all records) ===")
    print(f"{'Field':<22} {'Available':>9} {'Missing':>8} {'Percentage':>11}")
    for row in rows:
        print(f"{row['field']:<22} {row['available']:>9} {row['missing']:>8} "
              f"{str(row['percentage']) + '%':>11}")

    print("\n=== RECORDS BY content_type ===")
    for ct, v in per_type.items():
        print(f"  {ct:<10} {v['record_count']}")


if __name__ == "__main__":
    main()
