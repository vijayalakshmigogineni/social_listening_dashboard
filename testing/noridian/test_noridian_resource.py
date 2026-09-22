import requests

BASE = "https://med.noridianmedicare.com"

url = (
    BASE
    + "/web/jfb/policies/cmd-articles"
    + "?p_p_id=com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_tu1rI7mxv8xO"
    + "&p_p_lifecycle=2"
    + "&p_p_state=normal"
    + "&p_p_mode=view"
    + "&p_p_resource_id=exportEntries"
)

headers = {
    "User-Agent": "Mozilla/5.0"
}

print("URL:")
print(url)
print()

try:
    response = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    print("STATUS:", response.status_code)
    print("FINAL URL:", response.url)
    print("CONTENT TYPE:", response.headers.get("content-type"))
    print("SIZE:", len(response.content))

    print("\nFIRST 2000 CHARACTERS:")
    print(response.text[:2000])

except requests.exceptions.ConnectTimeout:
    print("RESULT: CONNECTION TIMEOUT")

except requests.exceptions.ReadTimeout:
    print("RESULT: READ TIMEOUT")

except requests.exceptions.ConnectionError as e:
    print("RESULT: CONNECTION ERROR")
    print(e)

except Exception as e:
    print("RESULT:", type(e).__name__, e)