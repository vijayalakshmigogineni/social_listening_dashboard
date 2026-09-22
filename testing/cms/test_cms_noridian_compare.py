import requests
import json

BASE_URL = "https://api.coverage.cms.gov/v1/reports/whats-new/local/"

contractors = {
    357: "Noridian 02102",
    356: "Noridian 02202",
}

for contractor_id, name in contractors.items():

    print("\n" + "=" * 80)
    print(name)
    print("CONTRACTOR ID:", contractor_id)
    print("=" * 80)

    params = {
        "page": 1,
        "size": 20,
        "contractor_id": contractor_id
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("URL:", response.url)
    print()

    if response.status_code != 200:
        print(response.text[:3000])
        continue

    data = response.json()

    print("NUMBER OF RECORDS:", len(data.get("data", [])))
    print()

    for record in data.get("data", []):

        print("-" * 80)

        print("DOCUMENT:", record.get("document_display_id"))
        print("TYPE:", record.get("document_type"))
        print("TITLE:", record.get("title"))
        print("VERSION:", record.get("document_version"))
        print("UPDATED:", record.get("updated_on"))
        print("EFFECTIVE:", record.get("effective_date"))
        print("RETIREMENT:", record.get("retirement_date"))
        print("CONTRACTOR:", record.get("contractor_name_type"))
        print("URL:", record.get("url"))