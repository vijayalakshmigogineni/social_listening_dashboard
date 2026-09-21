import requests
from io import BytesIO
from pypdf import PdfReader

PDFS = {
    "UHC_Commercial_Medical_Bulletin":
        "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/mpub-archives/commercial/medical-policy-update-bulletin-june-2026.pdf",

    "UHC_Commercial_Reimbursement_Example":
        "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-reimbursement/COMM-Injection-and-Infusion-Services-Policy.pdf",

    "UHC_Medicare_Advantage_Bulletin":
        "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/medadv-mp/medicare-advantage-medical-policy-update-bulletin-september-2026.pdf",

    "UHC_Medicare_Advantage_Pain_Management":
        "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/medadv-mp/pain-management-rehabilitation.pdf",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

for name, url in PDFS.items():

    print("\n" + "=" * 100)
    print(name)
    print("=" * 100)

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=60
        )

        print("HTTP Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Size:", len(response.content), "bytes")

        if response.status_code != 200:
            print("FAILED")
            continue

        reader = PdfReader(BytesIO(response.content))

        print("Number of Pages:", len(reader.pages))

        full_text = ""

        for page in reader.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

        print("\nTotal Extracted Characters:", len(full_text))

        print("\nFIRST 5000 CHARACTERS")
        print("-" * 100)
        print(full_text[:5000])

        print("\nSEARCHING IMPORTANT TERMS")
        print("-" * 100)

        terms = [
            "Effective Date",
            "Last Published",
            "Policy",
            "Status",
            "Procedure",
            "CPT",
            "HCPCS",
            "ICD",
            "Reimbursement",
            "Coverage",
            "Medical Necessity",
            "Authorization",
            "Modifier",
            "Pain",
            "Spinal",
            "Injection",
            "Denial",
            "History"
        ]

        lower_text = full_text.lower()

        for term in terms:

            count = lower_text.count(term.lower())

            if count > 0:
                print(f"{term}: {count}")

    except Exception as e:

        print("ERROR:")
        print(type(e).__name__, str(e))