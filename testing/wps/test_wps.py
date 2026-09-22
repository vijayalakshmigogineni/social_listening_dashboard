import requests
import json

API_URL = "https://www.wpsgha.com/api/content/news-items"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json",
}

payload = {
    "filters": {},
    "pagination": {
        "page": 1,
        "pageSize": 20
    },
    "sort": [
        "NewsPublishedDate:desc"
    ]
}

print("=" * 70)
print("WPS NEWS API TEST")
print("=" * 70)

print("\nURL:")
print(API_URL)

print("\nSending request...")

try:

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    print("\nSTATUS:")
    print(response.status_code)

    print("\nCONTENT TYPE:")
    print(response.headers.get("content-type"))

    print("\nRESPONSE LENGTH:")
    print(len(response.text))

    print("\n" + "=" * 70)
    print("RAW RESPONSE")
    print("=" * 70)

    print(response.text[:5000])

    # Try JSON
    try:

        data = response.json()

        print("\n" + "=" * 70)
        print("JSON STRUCTURE")
        print("=" * 70)

        print(json.dumps(
            data,
            indent=2
        )[:10000])

        with open(
            "wps_news_api_response.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        print("\nSaved:")
        print("wps_news_api_response.json")

    except Exception as e:

        print("\nCould not parse JSON:")
        print(e)

except Exception as e:

    print("\nREQUEST ERROR:")
    print(e)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)