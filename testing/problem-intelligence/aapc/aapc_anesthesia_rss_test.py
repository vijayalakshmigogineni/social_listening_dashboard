import requests
import xml.etree.ElementTree as ET


RSS_URL = "https://www.aapc.com/discuss/forums/anesthesia.440/index.rss"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def main():

    print("=" * 50)
    print("AAPC ANESTHESIA RSS TEST")
    print("=" * 50)

    response = requests.get(
        RSS_URL,
        headers=HEADERS,
        timeout=30
    )

    print("\nURL:")
    print(RSS_URL)

    print("\nStatus:")
    print(response.status_code)

    print("\nContent-Type:")
    print(response.headers.get("Content-Type"))

    response.raise_for_status()

    root = ET.fromstring(response.content)

    channel = root.find("channel")

    print("\nChannel title:")
    print(channel.findtext("title"))

    print("\nChannel description:")
    print(channel.findtext("description"))

    items = channel.findall("item")

    print("\nRSS items:", len(items))

    print("\nFirst 10 items:")
    print("-" * 50)

    for i, item in enumerate(items[:10], start=1):

        title = item.findtext("title")
        link = item.findtext("link")
        pub_date = item.findtext("pubDate")
        guid = item.findtext("guid")
        description = item.findtext("description")

        print(f"\n{i}. {title}")
        print("URL:", link)
        print("Published:", pub_date)
        print("GUID:", guid)
        print("Description:", description)


if __name__ == "__main__":
    main()