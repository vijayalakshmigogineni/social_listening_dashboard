import requests
import xml.etree.ElementTree as ET

URL = "https://www.aapc.com/discuss/forums/billing-reimbursement.583/index.rss"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

root = ET.fromstring(response.content)

channel = root.find("channel")

print("\n==============================")
print("CHANNEL")
print("==============================")

print(
    "Title:",
    channel.findtext("title")
)

print(
    "Description:",
    channel.findtext("description")
)

print(
    "Published:",
    channel.findtext("pubDate")
)


print("\n==============================")
print("ITEMS")
print("==============================")

items = channel.findall("item")

print("Number of RSS items:", len(items))


for index, item in enumerate(items, start=1):

    print("\n------------------------------")
    print(f"ITEM {index}")
    print("------------------------------")

    print(
        "Title:",
        item.findtext("title")
    )

    print(
        "Link:",
        item.findtext("link")
    )

    print(
        "Publication Date:",
        item.findtext("pubDate")
    )

    print(
        "GUID:",
        item.findtext("guid")
    )

    description = item.findtext("description")

    print("\nDescription:")
    print(description)