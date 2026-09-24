"""Run the YouTube collector (videos -> comments) and store comments in the DB.

Usage:
    python scripts/collect_youtube.py                                  # all query families
    python scripts/collect_youtube.py --families claims_denials payers \
        --max-videos-per-query 3 --max-comments-per-video 20
    python scripts/collect_youtube.py --video-date-filter year --comment-days 180

Cost (Apify pay-per-result): ~$0.004/video discovered + ~$0.002/comment.
Worst case is roughly max-videos-total x max-comments-per-video comments.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors import youtube
from app.collectors.common import upsert_normalized_items
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--families", nargs="*", default=None, choices=sorted(youtube.QUERY_FAMILIES))
    parser.add_argument("--max-videos-per-query", type=int, default=youtube.DEFAULT_MAX_VIDEOS_PER_QUERY)
    parser.add_argument("--max-videos-total", type=int, default=youtube.DEFAULT_MAX_VIDEOS_TOTAL)
    parser.add_argument("--max-comments-per-video", type=int, default=youtube.DEFAULT_MAX_COMMENTS_PER_VIDEO)
    parser.add_argument("--video-date-filter", default=None, choices=sorted(youtube.VIDEO_DATE_FILTERS),
                        help="Only discover videos uploaded within this window")
    parser.add_argument("--comment-days", type=int, default=None,
                        help="Only collect comments newer than this many days")
    args = parser.parse_args()

    families = (
        {f: youtube.QUERY_FAMILIES[f] for f in args.families} if args.families else None
    )
    records = youtube.collect_families(
        query_families=families,
        max_videos_per_query=args.max_videos_per_query,
        max_videos_total=args.max_videos_total,
        max_comments_per_video=args.max_comments_per_video,
        video_date_filter=args.video_date_filter,
        comment_days=args.comment_days,
    )
    print(f"\nCollected {len(records)} normalized records total.")

    db = SessionLocal()
    try:
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
