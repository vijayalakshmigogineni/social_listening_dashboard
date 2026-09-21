import requests
import xml.etree.ElementTree as ET
import json


RSS_URL = (
    "https://www.aapc.com/discuss/"
    "forums/billing-reimbursement.583/index.rss"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


response = requests.get(
    RSS_URL,
    headers=HEADERS,
    timeout=30
)

print("Status:", response.status_code)

response.raise_for_status()


root = ET.fromstring(response.content)

channel = root.find("channel")

items = channel.findall("item")


threads = []


for item in items:

    title = item.findtext("title")
    link = item.findtext("link")
    pub_date = item.findtext("pubDate")
    guid = item.findtext("guid")

    threads.append({
        "source": "AAPC",
        "source_item_id": guid,
        "title": title,
        "url": link,
        "published_at": pub_date
    })


output_file = "aapc_rss_threads.json"


with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        threads,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\nRSS items:", len(threads))

print(
    f"Saved to: {output_file}"
)


print("\nFirst 5 threads:")

for thread in threads[:5]:

    print(
        f"- {thread['title']}"
    )

    print(
        f"  {thread['url']}"
    )

    print(
        f"  ID: {thread['source_item_id']}"
    )