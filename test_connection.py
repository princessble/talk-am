import os
from dotenv import load_dotenv
from openai import OpenAI

# Load the secret key from the .env file
load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

# 1. List the models this account can use
print("=== Models available to you ===")
for model in client.models.list():
    print(model.id)

# 2. Ask Muse Spark a simple question
print("\n=== Muse Spark says ===")
response = client.chat.completions.create(
    model="muse-spark-1.3",
    messages=[
        {"role": "user", "content": "Say hello to a Nigerian creator in one short Pidgin sentence."}
    ],
)
print(response.choices[0].message.content)