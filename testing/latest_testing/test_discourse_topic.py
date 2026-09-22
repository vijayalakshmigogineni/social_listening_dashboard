import requests

topic_id = 71 # replace with your actual topic ID

url = f"https://medical-billing-forum.discourse.group/t/{topic_id}.json"

response = requests.get(url)

print("Status:", response.status_code)

data = response.json()

print("Available keys:")
print(data.keys())

if "title" in data:
    print("\nTITLE:")
    print(data["title"])

    print("\nPOSTS:")

    for post in data.get("post_stream", {}).get("posts", []):
        print("\n-------------------------")
        print("Author:", post.get("username"))
        print("Created:", post.get("created_at"))
        print("Post:")
        print(post.get("cooked", ""))

else:
    print("\nNo title found.")
    print("Response:")
    print(data)