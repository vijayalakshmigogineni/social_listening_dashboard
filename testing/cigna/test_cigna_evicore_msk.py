import re
import requests
from io import BytesIO
from pypdf import PdfReader

URL = "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/medical/eviCore_Guidelines-MSK_Services_Procedures.pdf"

headers = {
    "User-Agent": "Mozilla/5.0"
}

PAIN_KEYWORDS = [
    "pain", "spine", "spinal", "epidural", "facet", "nerve",
    "ablation", "stimulator", "stimulation", "kyphoplasty",
    "sacroiliac", "denervation", "prior authorization",
    "medical necessity", "cpt"
]

print("=" * 90)
print("CIGNA / EVICORE MSK SERVICES & PROCEDURES GUIDELINES")
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

    print("\nFIRST 1500 CHARACTERS")
    print("-" * 90)
    print(full_text[:1500])

    print("\nTABLE OF CONTENTS / SECTION HEADINGS (lines that look like a guideline number, e.g. 'CMM-2xx')")
    print("-" * 90)
    toc_lines = re.findall(r"(CMM[- ]?\d{2,3}[^\n]{0,80})", full_text)
    for line in toc_lines[:40]:
        print("-", line.strip())

    print(f"\nTotal CMM guideline references found: {len(toc_lines)}")

    print("\nPAIN-MANAGEMENT KEYWORD COUNTS")
    print("-" * 90)
    lower_text = full_text.lower()
    for term in PAIN_KEYWORDS:
        count = lower_text.count(term)
        if count > 0:
            print(f"  {term}: {count}")
