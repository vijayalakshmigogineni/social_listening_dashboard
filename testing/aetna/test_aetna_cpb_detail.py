import re
import requests
from bs4 import BeautifulSoup

CPBS = {
    "CPB_0016_Back_Pain_Invasive_Procedures":
        "https://www.aetna.com/cpb/medical/data/1_99/0016.html",

    "CPB_0722_Transforaminal_Epidural_Injections":
        "https://www.aetna.com/cpb/medical/data/700_799/0722.html",

    "CPB_0863_Nerve_Blocks":
        "https://www.aetna.com/cpb/medical/data/800_899/0863.html",

    "CPB_0934_Epidural_Injection_Technologies":
        "https://www.aetna.com/cpb/medical/data/900_999/0934.html",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

SECTION_HEADINGS = [
    "Policy", "Background", "References",
    "CPT codes covered", "CPT codes not covered",
    "ICD-10 codes covered", "ICD-10 codes not covered",
]


def get_meta(soup, name):
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content") if tag else None


for name, url in CPBS.items():

    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    try:
        response = requests.get(url, headers=headers, timeout=30)

        print("HTTP Status:  ", response.status_code)
        print("Content-Type: ", response.headers.get("Content-Type"))
        print("Size:         ", len(response.content), "bytes")
        print("Last-Modified:", response.headers.get("Last-Modified"))

        if response.status_code != 200:
            print("FAILED - skipping")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text("\n", strip=True)

        title = soup.title.get_text(strip=True) if soup.title else "NO TITLE"

        print("\nTitle:            ", title)
        print("CPB Number:       ", get_meta(soup, "aet.cpbNumber"))
        print("CPB Type:         ", get_meta(soup, "aet.cpbType"))
        print("Last Review Date: ", get_meta(soup, "aet.lastReviewDate"))
        print("Next Review Date: ", get_meta(soup, "aet.anticipatedReviewDate"))

        print("\nSections Found:")
        for heading in SECTION_HEADINGS:
            mark = "YES" if re.search(re.escape(heading), page_text, re.I) else "no"
            print(f"  [{mark:>3}] {heading}")

        covered_cpt = len(re.findall(r"\b\d{5}\b", page_text.split("CPT codes covered", 1)[-1].split("Background", 1)[0])) \
            if "CPT codes covered" in page_text else 0

        print("\nApprox. CPT/HCPCS code lines found (covered + not covered + related):", covered_cpt)

    except Exception as e:
        print("\nERROR:", type(e).__name__, str(e))
