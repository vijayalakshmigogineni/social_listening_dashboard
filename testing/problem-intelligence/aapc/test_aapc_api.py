import requests

BASE = "https://www.aapc.com"

paths = [
    "/discuss/api/",
    "/discuss/api",
    "/discuss/api.php",
    "/api/",
    "/api"
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for path in paths:

    url = BASE + path

    print("\n==============================")
    print("TESTING:", url)
    print("==============================")

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Final URL:", response.url)

        print("Preview:")
        print(response.text[:300])

    except Exception as e:

        print("ERROR:", e)