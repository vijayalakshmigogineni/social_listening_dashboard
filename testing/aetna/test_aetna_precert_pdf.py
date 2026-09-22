import re
import requests
from io import BytesIO
from pypdf import PdfReader

URL = "https://www.aetna.com/content/dam/aetna/pdfs/aetnacom/healthcare-professionals/2026_Precert_List.pdf"

headers = {
    "User-Agent": "Mozilla/5.0"
}

PAIN_CODES_OF_INTEREST = [
    "64483", "64484", "64635", "64636", "62323", "62327",  # ESI / facet RF ablation
    "63650", "63685",  # spinal cord stimulator trial/implant
    "22513", "22514",  # kyphoplasty
    "64553", "64555", "64561",  # peripheral nerve stimulation
]

print("=" * 90)
print("AETNA 2026 PRECERTIFICATION LIST")
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

    print("\nFIRST 1500 CHARACTERS (cover / structure)")
    print("-" * 90)
    print(full_text[:1500])

    print("\nPAIN-MANAGEMENT-RELEVANT CPT CODE CHECK")
    print("-" * 90)
    for code in PAIN_CODES_OF_INTEREST:
        present = code in full_text
        print(f"  [{'YES' if present else 'no':>3}] {code}")

    print("\nLines mentioning 'pain', 'spinal', 'nerve', 'injection', 'stimulator' (first 25)")
    print("-" * 90)
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    count = 0
    for line in lines:
        if re.search(r"pain|spinal|nerve|injection|stimulat", line, re.I):
            print("-", line[:150])
            count += 1
            if count >= 25:
                break
