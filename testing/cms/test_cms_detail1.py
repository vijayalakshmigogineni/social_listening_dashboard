import os

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("CMS_API_TOKEN")

if not TOKEN:
    raise ValueError("CMS_API_TOKEN not found in .env file")


headers = {
    "Authorization": f"Bearer {TOKEN}"
}

url = "https://api.coverage.cms.gov/v1/data/lcd/contractor"

params = {
    "lcdid": "40267",
    "ver": "6"
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print("Status:", response.status_code)

data = response.json()["data"][0]

fields = [
    "lcd_id",
    "lcd_version",
    "title",
    "orig_det_eff_date",
    "rev_eff_date",
    "rev_end_date",
    "indication",
    "coding_guidelines",
    "doc_reqs",
    "util_guide",
    "status",
    "last_updated",
    "keywords",
    "synopsis_changes",
    "issue",
    "issue_change",
    "mac_initiated"
]

for field in fields:
    value = data.get(field)

    print("\n" + "=" * 70)
    print(field.upper())
    print("=" * 70)

    if value is None:
        print("NULL")
    else:
        print(value)