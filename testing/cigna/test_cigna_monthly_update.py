import re
import requests
from io import BytesIO
from pypdf import PdfReader

URL = "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/policy_updates/september_2026_policy_updates.pdf"

headers = {
    "User-Agent": "Mozilla/5.0"
}

PAIN_KEYWORDS = [
    "pain", "spine", "spinal", "epidural", "facet", "nerve block",
    "nerve stimulation", "nerve destruction", "radiofrequency",
    "stimulator", "kyphoplasty", "sacroiliac", "denervation",
    "interventional pain"
]

print("=" * 90)
print("CIGNA MONTHLY POLICY UPDATES - SEPTEMBER 2026")
print("=" * 90)

response = requests.get(URL, headers=headers, timeout=30)

print("HTTP Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Size:", len(response.content), "bytes")

if response.status_code != 200:
    print("FAILED")
else:
    reader = PdfReader(BytesIO(response.content))
    print("Number of Pages:", len(reader.pages))

    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"

    print("Total Extracted Characters:", len(full_text))

    print("\nFIRST 2000 CHARACTERS (to see the document's structure/columns)")
    print("-" * 90)
    print(full_text[:2000])

    print("\nLINES CONTAINING PAIN-MANAGEMENT KEYWORDS")
    print("-" * 90)

    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    matched = 0
    for i, line in enumerate(lines):
        low = line.lower()
        if any(k in low for k in PAIN_KEYWORDS):
            matched += 1
            context = " | ".join(lines[max(0, i - 1):i + 2])
            print(f"- {context[:200]}")

    print(f"\nTotal matching lines: {matched}")
