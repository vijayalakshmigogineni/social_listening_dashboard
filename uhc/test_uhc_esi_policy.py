import requests
from io import BytesIO
from pypdf import PdfReader

URL = "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/epidural-steroid-injections-spinal-pain.pdf"

print("=" * 100)
print("UHC INDIVIDUAL MEDICAL POLICY TEST")
print("=" * 100)

response = requests.get(URL, timeout=30)

print("HTTP Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Size:", len(response.content), "bytes")

if response.status_code != 200:
    print("\nFAILED TO DOWNLOAD PDF")
    exit()

reader = PdfReader(BytesIO(response.content))

print("Number of Pages:", len(reader.pages))

text = ""

for page in reader.pages:
    page_text = page.extract_text() or ""
    text += page_text + "\n"

print("Total Extracted Characters:", len(text))

print("\n" + "=" * 100)
print("FIRST 8000 CHARACTERS")
print("=" * 100)

print(text[:8000])

print("\n" + "=" * 100)
print("IMPORTANT TERM COUNTS")
print("=" * 100)

terms = [
    "Effective Date",
    "Policy Number",
    "Last Published",
    "Coverage Rationale",
    "Coverage",
    "Indications",
    "Limitations",
    "Medical Necessity",
    "Authorization",
    "Prior Authorization",
    "CPT",
    "HCPCS",
    "ICD",
    "Procedure",
    "Injection",
    "Epidural",
    "Spinal",
    "Radiofrequency",
    "Denial",
    "Policy History",
    "Revision Information",
]

lower_text = text.lower()

for term in terms:
    print(f"{term}: {lower_text.count(term.lower())}")