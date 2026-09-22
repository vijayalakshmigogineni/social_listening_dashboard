import requests
from io import BytesIO
from pypdf import PdfReader

URL = "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/epidural-steroid-injections-spinal-pain.pdf"

response = requests.get(URL, timeout=30)

print("HTTP Status:", response.status_code)

reader = PdfReader(BytesIO(response.content))

text = ""

for page_number, page in enumerate(reader.pages, start=1):
    page_text = page.extract_text() or ""
    text += f"\n===== PAGE {page_number} =====\n"
    text += page_text

term = "Policy History/Revision Information"

print("\n" + "=" * 100)
print("SEARCHING FOR ACTUAL POLICY HISTORY")
print("=" * 100)

start = 0
matches = []

while True:
    index = text.lower().find(term.lower(), start)

    if index == -1:
        break

    matches.append(index)
    start = index + len(term)

print("Number of matches:", len(matches))

for i, index in enumerate(matches, start=1):
    print(f"\nMatch {i} at character position: {index}")

print("\n" + "=" * 100)
print("LAST OCCURRENCE")
print("=" * 100)

if matches:
    index = matches[-1]

    # Print 8000 characters after the LAST occurrence
    print(text[index:index + 8000])
else:
    print("Policy history section not found.")