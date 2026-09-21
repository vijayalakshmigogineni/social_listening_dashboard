import requests
import time

urls = [
    "https://med.noridianmedicare.com/",
    "https://med.noridianmedicare.com/web/jfb/",
    "https://med.noridianmedicare.com/web/jfb/policies",
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for url in urls:
    print("\n" + "=" * 80)
    print("TESTING:", url)

    try:
        start = time.time()

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        elapsed = time.time() - start

        print("STATUS:", response.status_code)
        print("TIME:", round(elapsed, 2), "seconds")
        print("FINAL URL:", response.url)
        print("CONTENT TYPE:", response.headers.get("content-type"))
        print("SIZE:", len(response.content))

    except requests.exceptions.ConnectTimeout:
        print("RESULT: CONNECTION TIMEOUT")

    except requests.exceptions.ReadTimeout:
        print("RESULT: READ TIMEOUT")

    except requests.exceptions.ConnectionError as e:
        print("RESULT: CONNECTION ERROR")
        print(e)

    except Exception as e:
        print("RESULT: OTHER ERROR")
        print(type(e).__name__, e)