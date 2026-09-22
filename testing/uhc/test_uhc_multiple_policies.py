import requests
from io import BytesIO
from pypdf import PdfReader

POLICIES = {
    "ESI": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/epidural-steroid-injections-spinal-pain.pdf",

    "ABLATIVE": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/ablative-treatment-spinal-pain.pdf",

    "FACET": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/facet-joint-injections-spinal-pain.pdf",

    "EPIDUROSCOPY": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/epiduroscopy-epidural-lysis-adhesions-discography.pdf",
}


def extract_pdf(url):

    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        return None, response

    reader = PdfReader(BytesIO(response.content))

    text = ""

    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"

    return text, response


def count_term(text, term):
    return text.lower().count(term.lower())


terms = [
    "Policy Number",
    "Effective Date",
    "Last Published",
    "Coverage Rationale",
    "Medical Records Documentation",
    "Definitions",
    "Applicable Codes",
    "CPT",
    "HCPCS",
    "ICD",
    "Coverage",
    "Limitations",
    "Medical Necessity",
    "Authorization",
    "Prior Authorization",
    "Procedure",
    "Policy History",
    "Revision Information",
    "Date",
    "Summary of Changes",
]


for name, url in POLICIES.items():

    print("\n" + "=" * 110)
    print(name)
    print("=" * 110)

    print("URL:", url)

    text, response = extract_pdf(url)

    if text is None:
        print("FAILED")
        print("HTTP Status:", response.status_code)
        continue

    reader = PdfReader(BytesIO(response.content))

    print("HTTP Status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Size:", len(response.content), "bytes")
    print("Pages:", len(reader.pages))
    print("Extracted Characters:", len(text))

    print("\nTERM COUNTS")
    print("-" * 80)

    for term in terms:
        print(f"{term}: {count_term(text, term)}")

    print("\nFIRST 1500 CHARACTERS")
    print("-" * 80)
    print(text[:1500])