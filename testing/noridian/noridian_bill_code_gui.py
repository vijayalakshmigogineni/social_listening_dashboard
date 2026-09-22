import requests
import json

BASE_URL = "https://api.coverage.cms.gov/v1"

print("=" * 80)
print("NORIDIAN - CLAIMS / BILLING INFORMATION TEST")
print("=" * 80)

# -------------------------------------------------------------------
# STEP 1 - Get CMS API documentation / discover available endpoints
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 1 - CHECK CMS API OPENAPI")
print("=" * 80)

openapi_url = f"{BASE_URL}/openapi.json"

response = requests.get(openapi_url, timeout=30)

print("OPENAPI STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text[:2000])
    raise SystemExit()

openapi = response.json()

paths = openapi.get("paths", {})

print("TOTAL ENDPOINTS:", len(paths))

print("\nCLAIMS / BILLING RELATED ENDPOINTS:")

matches = []

for path in paths.keys():

    path_lower = path.lower()

    if any(word in path_lower for word in [
        "claim",
        "billing",
        "payment",
        "denial",
        "utilization"
    ]):
        matches.append(path)

if matches:
    for path in matches:
        print("-", path)
else:
    print("NO CLAIMS/BILLING/DENIAL ENDPOINTS FOUND")


# -------------------------------------------------------------------
# STEP 2 - Show endpoint descriptions
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 2 - ENDPOINT DETAILS")
print("=" * 80)

for path in matches:

    print("\n" + "-" * 70)
    print("ENDPOINT:", path)

    methods = paths[path]

    for method, details in methods.items():

        if method.lower() not in [
            "get",
            "post"
        ]:
            continue

        print("\nMETHOD:", method.upper())

        print("SUMMARY:")
        print(details.get("summary"))

        print("\nDESCRIPTION:")
        print(details.get("description"))

        parameters = details.get("parameters", [])

        if parameters:
            print("\nPARAMETERS:")

            for param in parameters:

                print(
                    f"  {param.get('name')} "
                    f"| location={param.get('in')} "
                    f"| required={param.get('required')}"
                )


# -------------------------------------------------------------------
# STEP 3 - Search CMS OpenAPI for useful terms
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 3 - SEARCH API DOCUMENTATION FOR CLAIMS TERMS")
print("=" * 80)

terms = [
    "claim",
    "denial",
    "payment",
    "billing",
    "utilization",
    "remittance"
]

for term in terms:

    print(f"\nSEARCH TERM: {term}")

    found = []

    for path, methods in paths.items():

        path_text = json.dumps(methods).lower()

        if term.lower() in path.lower() or term.lower() in path_text:
            found.append(path)

    if found:
        for path in sorted(set(found)):
            print(" ", path)
    else:
        print("  No matching endpoint/documentation found.")


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)