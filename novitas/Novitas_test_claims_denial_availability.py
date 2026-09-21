import requests
import json

BASE_URL = "https://api.coverage.cms.gov/v1"

print("=" * 80)
print("NOVITAS - CLAIMS / DENIAL / UTILIZATION TEST")
print("=" * 80)


# -------------------------------------------------------------------
# STEP 1 - GET CMS API DOCUMENTATION INFORMATION
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 1 - CHECK CMS API ROOT / DOCUMENTATION")
print("=" * 80)

urls_to_test = [
    f"{BASE_URL}/",
    "https://api.coverage.cms.gov/docs",
    "https://api.coverage.cms.gov/docs/v1",
]

for url in urls_to_test:

    try:
        response = requests.get(url, timeout=20)

        print("\nURL:", url)
        print("STATUS:", response.status_code)
        print("CONTENT TYPE:", response.headers.get("content-type"))

        if response.text:
            print("RESPONSE:")
            print(response.text[:1000])

    except Exception as e:
        print("\nURL:", url)
        print("ERROR:", e)


# -------------------------------------------------------------------
# STEP 2 - TEST LIKELY CLAIMS-RELATED ENDPOINTS
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 2 - TEST CLAIMS-RELATED CMS ENDPOINTS")
print("=" * 80)

possible_endpoints = [
    "/data/claim/",
    "/data/claims/",
    "/data/denial/",
    "/data/denials/",
    "/data/payment/",
    "/data/payments/",
    "/data/utilization/",
    "/reports/claims/",
    "/reports/denials/",
    "/reports/utilization/",
]

for endpoint in possible_endpoints:

    url = BASE_URL + endpoint

    try:

        response = requests.get(
            url,
            timeout=20
        )

        print("\n" + "-" * 70)
        print("ENDPOINT:", endpoint)
        print("STATUS:", response.status_code)
        print("CONTENT TYPE:", response.headers.get("content-type"))

        if response.text:
            print("RESPONSE:")
            print(response.text[:500])

    except Exception as e:

        print("\n" + "-" * 70)
        print("ENDPOINT:", endpoint)
        print("ERROR:", e)


# -------------------------------------------------------------------
# STEP 3 - SUMMARY
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)