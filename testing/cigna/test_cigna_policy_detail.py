import re
import requests
from io import BytesIO
from pypdf import PdfReader

POLICIES = {
    "Cigna_0525_Peripheral_Nerve_Destruction_RFA":
        "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/medical/mm_0525_coveragepositioncriteria_peripheral_nerve_destruction.pdf",

    "Cigna_0539_Peripheral_Nerve_Stimulation":
        "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/medical/mm_0539_coveragepositioncriteria_percut_periph_nerve_stim_field_stim.pdf",

    "Cigna_0551_Anesthesia_Interventional_Pain_Mgmt":
        "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/medical/mm_0551_coveragepositioncriteria_anesthesia_services_for_interventional_pain_management.pdf",

    "Cigna_0139_Invasive_Treatment_Back_Pain":
        "https://static.cigna.com/assets/chcp/pdf/coveragePolicies/medical/mm_0139_coveragepositioncriteria_invasive_treatment_for_back_pain.pdf",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

SECTION_HEADINGS = [
    "Coverage Policy", "General Background", "Coding Information",
    "Revision Details", "References", "Effective Date"
]


def find_field(text, label, max_len=120):
    match = re.search(rf"{re.escape(label)}\s*[:\-]?\s*(.{{1,{max_len}}})", text)
    return match.group(1).strip() if match else None


for name, url in POLICIES.items():

    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    try:
        response = requests.get(url, headers=headers, timeout=30)

        print("HTTP Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Size:", len(response.content), "bytes")

        if response.status_code != 200:
            print("FAILED - skipping")
            continue

        reader = PdfReader(BytesIO(response.content))
        print("Number of Pages:", len(reader.pages))

        first_page = reader.pages[0].extract_text() or ""
        full_text = first_page
        for page in reader.pages[1:]:
            full_text += "\n" + (page.extract_text() or "")

        print("\nFirst-page snippet (title/effective date area):")
        print("-" * 90)
        print(first_page[:600].strip())

        print("\nSections Found:")
        for heading in SECTION_HEADINGS:
            mark = "YES" if re.search(re.escape(heading), full_text, re.I) else "no"
            print(f"  [{mark:>3}] {heading}")

        # "Revision Details" appears twice: once in the Table of Contents, once as the
        # actual dated changelog table near the end of the document. Take the LAST match.
        rev_matches = list(re.finditer(r"Revision Details", full_text, re.I))
        if rev_matches:
            start = rev_matches[-1].end()
            print("\nRevision Details excerpt (actual changelog table, first 800 chars):")
            print(full_text[start:start + 800].strip())
        else:
            print("\nRevision Details excerpt: NOT FOUND in extracted text")

    except Exception as e:
        print("\nERROR:", type(e).__name__, str(e))
