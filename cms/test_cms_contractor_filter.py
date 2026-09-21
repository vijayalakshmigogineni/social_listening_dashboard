import requests

BASE_URL = "https://api.coverage.cms.gov/v1/reports/local-coverage-final-lcds/"

contractors = {
    357: "Noridian contractor 02102",
    356: "Noridian contractor 02202",
    999999: "INVALID contractor ID",
}

for contractor_id, label in contractors.items():

    print("\n" + "=" * 80)
    print(label)
    print("CONTRACTOR ID:", contractor_id)
    print("=" * 80)

    params = {
        "contractor_id": contractor_id
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print()

        if response.status_code != 200:
            print("ERROR:")
            print(response.text[:3000])
            continue

        data = response.json()
        records = data.get("data", [])

        print("NUMBER OF RECORDS:", len(records))
        print()

        for record in records[:10]:

            print("-" * 70)

            print("DOCUMENT:", record.get("document_display_id"))
            print("TYPE:", record.get("document_type"))
            print("TITLE:", record.get("title"))
            print("CONTRACTOR:", record.get("contractor_name_type"))
            print("UPDATED:", record.get("updated_on"))
            print("EFFECTIVE:", record.get("effective_date"))

    except Exception as e:
        print("ERROR:", type(e).__name__, e)