import requests

urls = [
    "https://www.beckersspine.com/?a=index&format=feed&m=wap&siteid=1&type=rss",
    "https://www.beckersspine.com/?c=index&format=feed&m=member&siteid=1&type=rss",
    "https://www.beckersspine.com/?a=index&format=feed&m=wap&siteid=1&type=atom"
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for url in urls:
    print("\n" + "=" * 100)
    print("URL:", url)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Length:", len(response.content))

    except Exception as e:
        print("ERROR:", e)