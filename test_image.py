import base64
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

# Use the first scene from the scenes we just made
with open("output/scenes.json", encoding="utf-8") as f:
    plan = json.load(f)

prompt = plan["scenes"][0]["image_prompt"]
print("Drawing scene 1...\n")

response = client.images.generate(
    model="muse-image-1.0",
    prompt=prompt,
    n=1,
)

image = response.data[0]
os.makedirs("output", exist_ok=True)

if getattr(image, "b64_json", None):
    with open("output/scene_1.png", "wb") as f:
        f.write(base64.b64decode(image.b64_json))
    print("Saved: output/scene_1.png")
elif getattr(image, "url", None):
    print("Image URL:", image.url)
else:
    print("Unexpected response:", response)