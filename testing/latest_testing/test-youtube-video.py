import requests
import os
from datetime import datetime, timezone

API_KEY = "REDACTED"

VIDEO_ID = "hQIGgy55bsw"

response = requests.get(
    "https://www.googleapis.com/youtube/v3/videos",
    params={
        "part": "snippet,statistics,contentDetails",
        "id": VIDEO_ID,
        "key": API_KEY
    },
    timeout=30
)

data = response.json()

if not data.get("items"):
    print("Video not found")
    exit()

video = data["items"][0]

snippet = video["snippet"]
stats = video.get("statistics", {})
content = video.get("contentDetails", {})

normalized = {
    # Universal fields
    "source": "youtube",

    "source_item_id": VIDEO_ID,

    "url": f"https://www.youtube.com/watch?v={VIDEO_ID}",

    "title": snippet.get("title"),

    "text": snippet.get("description"),

    "author_id": snippet.get("channelId"),

    "author_name": snippet.get("channelTitle"),

    "author_profile_url": (
        f"https://www.youtube.com/channel/{snippet.get('channelId')}"
        if snippet.get("channelId")
        else None
    ),

    "author_role": None,

    "organization_name": None,

    "organization_url": None,

    "location": None,

    "created_at": snippet.get("publishedAt"),

    "collected_at": datetime.now(timezone.utc).isoformat(),

    "engagement": {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0))
    },

    "parent_id": None,

    "conversation_id": VIDEO_ID,

    "media_type": "video",

    # Platform-specific
    "source_metadata": {
        "category_id": snippet.get("categoryId"),
        "default_language": snippet.get("defaultLanguage"),
        "default_audio_language": snippet.get(
            "defaultAudioLanguage"
        ),
        "duration": content.get("duration"),
        "tags": snippet.get("tags", [])
    },

    # Preserve original API response
    "raw_data": video
}

print("\nNORMALIZED RECORD")
print("=" * 80)

for key, value in normalized.items():
    print(f"\n{key}:")
    print(value)