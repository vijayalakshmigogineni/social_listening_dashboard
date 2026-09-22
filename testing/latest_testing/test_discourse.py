import requests

url = "https://medical-billing-forum.discourse.group/latest.json"

response = requests.get(url)
data = response.json()

topics = data["topic_list"]["topics"]

for topic in topics:
    print("--------------------------------")
    print("Title:", topic["title"])
    print("Topic ID:", topic["id"])
    print("Replies:", topic["reply_count"])
    print("Views:", topic["views"])
    print("Created:", topic["created_at"])