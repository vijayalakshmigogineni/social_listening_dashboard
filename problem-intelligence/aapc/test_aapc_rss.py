import requests

urls = [
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/index.rss",
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/feed",
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/rss",
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for url in urls:

    print("\n==============================")
    print("TESTING")
    print(url)
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

        print("\nPreview:")
        print(response.text[:500])

    except Exception as e:

        print("ERROR:", e)

urls = [
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/index.rss",
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/feed",
    "https://www.aapc.com/discuss/forums/billing-reimbursement.583/rss",
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for url in urls:

    print("\n==============================")
    print("TESTING")
    print(url)
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

        print("\nPreview:")
        print(response.text[:500])

    except Exception as e:

        print("ERROR:", e)