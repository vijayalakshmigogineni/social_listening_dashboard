import boto3

client = boto3.client(
    "bedrock-runtime",
    region_name="ap-south-1"
)

response = client.converse(
    modelId="global.amazon.nova-2-lite-v1:0",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "text": "Explain prior authorization in healthcare billing in 3 simple points."
                }
            ]
        }
    ]
)

print(response["output"]["message"]["content"][0]["text"])