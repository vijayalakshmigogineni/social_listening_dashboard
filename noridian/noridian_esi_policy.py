import requests
import json

LICENSE_URL = "https://api.coverage.cms.gov/v1/metadata/license-agreement/"
LCD_URL = "https://api.coverage.cms.gov/v1/data/lcd/"

LCD_ID = "39240"

# ---------------------------------------------------------
# STEP 1: Get temporary CMS license token
# ---------------------------------------------------------

print("=" * 80)
print("STEP 1 - GET CMS LICENSE TOKEN")
print("=" * 80)

license_response = requests.get(
    LICENSE_URL,
    timeout=30
)

print("LICENSE STATUS:", license_response.status_code)

if license_response.status_code != 200:
    print(license_response.text)
    raise SystemExit

license_data = license_response.json()

token = license_data["data"][0]["Token"]

print("TOKEN FOUND: YES")
print("TOKEN LENGTH:", len(token))


# ---------------------------------------------------------
# STEP 2: Get L39240
# ---------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 2 - GET NORIDIAN LCD L39240")
print("=" * 80)

headers = {
    "Authorization": f"Bearer {token}"
}

params = {
    "lcdid": LCD_ID
}

lcd_response = requests.get(
    LCD_URL,
    params=params,
    headers=headers,
    timeout=30
)

print("LCD STATUS:", lcd_response.status_code)

if lcd_response.status_code != 200:
    print(lcd_response.text)
    raise SystemExit

lcd_data = lcd_response.json()


# ---------------------------------------------------------
# STEP 3: Inspect the structure
# ---------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 3 - TOP LEVEL STRUCTURE")
print("=" * 80)

print("TOP-LEVEL KEYS:")
print(list(lcd_data.keys()))

print("\nDATA TYPE:")
print(type(lcd_data.get("data")))


# ---------------------------------------------------------
# STEP 4: Search recursively for useful policy-change fields
# ---------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 4 - SEARCH FOR POLICY CHANGE FIELDS")
print("=" * 80)

TARGET_FIELDS = {
    "ISSUE",
    "ISSUE_CHANGE",
    "LAST_UPDATED",
    "EFFECTIVE_DATE",
    "REV_EFF_DATE",
    "ORIG_DET_EFF_DATE",
    "REV_END_DATE",
    "STATUS",
    "LCD_ID",
    "LCD_VERSION",
    "TITLE",
    "CONTRACTOR",
    "JURISDICTION"
}


def search_fields(obj, path="root"):

    if isinstance(obj, dict):

        for key, value in obj.items():

            key_upper = str(key).upper()

            if key_upper in TARGET_FIELDS:

                print("\nFIELD:", key)
                print("PATH :", path + "." + str(key))
                print("TYPE :", type(value).__name__)

                # Avoid dumping huge HTML/text fields
                if isinstance(value, str):

                    if len(value) > 3000:
                        print("VALUE: [LONG TEXT - first 3000 characters]")
                        print(value[:3000])
                    else:
                        print("VALUE:")
                        print(value)

                else:
                    print("VALUE:")
                    print(json.dumps(value, indent=2))

            search_fields(
                value,
                path + "." + str(key)
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            search_fields(
                item,
                path + f"[{index}]"
            )


search_fields(lcd_data)


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)