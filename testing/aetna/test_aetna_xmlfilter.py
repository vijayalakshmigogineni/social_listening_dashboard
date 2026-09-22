import requests
from urllib.parse import urljoin
import xml.dom.minidom as minidom

BASE = "https://www.aetna.com/content/services/aetna/xmlfilter"

ENDPOINTS = {
    "whats_new (mcpb-changes.xml, by status)": {
        "source": "/content/dam/aetna/xml/aetnacom/health-care-professionals/mcpb-changes.xml/jcr:content/renditions/original",
        "returnBy": "status",
        "sortBy": "status",
    },
    "cpb_listing (mcpb-alpha.xml, alphabetical)": {
        "source": "/content/dam/aetna/xml/aetnacom/health-care-professionals/mcpb-alpha.xml/jcr:content/renditions/original",
        "returnBy": "listing",
        "sortBy": "listing",
    },
    "periodic_reviews (mcpb-review.xml, by month)": {
        "source": "/content/dam/aetna/xml/aetnacom/health-care-professionals/mcpb-review.xml/jcr:content/renditions/original",
        "returnBy": "month",
        "sortBy": "month",
    },
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html",
}

for name, params in ENDPOINTS.items():

    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    try:
        response = requests.get(BASE, params=params, headers=headers, timeout=30)

        print("Request URL:", response.url)
        print("HTTP Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Size:", len(response.content), "bytes")

        if response.status_code != 200:
            print("FAILED")
            print(response.text[:500])
            continue

        print("\nFIRST 2000 CHARACTERS (raw)")
        print("-" * 90)
        print(response.text[:2000])

    except Exception as e:
        print("\nERROR:", type(e).__name__, str(e))
