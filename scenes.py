
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

SYSTEM_PROMPT = """You are the scene director for Talk Am, an app that turns
Nigerian voice notes into short vertical videos.

You will receive a short story or advert written in Nigerian English or Pidgin.
Split it into 4 to 6 scenes.

Rules:
1. "narration" must use the creator's EXACT words, in order. Do not translate,
   correct grammar or change the Pidgin. Every word of the story must appear in
   exactly one scene.
2. "image_prompt" describes one photorealistic vertical (9:16) image for that
   scene, set in Nigeria. Be specific about Nigerian details: clothing (ankara,
   gele, buba), food, markets, streets, buildings, weather and light.
   Write every image_prompt in plain English only, with no other scripts or languages.
3. If the story has a main character, describe how they look in
   "main_character" (age, skin tone, hair, clothing). Repeat that description
   inside every image_prompt where they appear, so they look the same in
   every scene.
4. No written words, signs or captions inside the images.
5. Reply with JSON only, no extra text, in this shape:

{
  "title": "short title",
  "main_character": "visual description, or empty string",
  "scenes": [
    {"number": 1, "narration": "exact words", "image_prompt": "description"}
  ]
}
"""


def plan_scenes(script: str) -> dict:
    """Ask Muse Spark to split a script into scenes with image prompts."""
    response = client.chat.completions.create(
        model="muse-spark-1.3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": script},
        ],
    )
    text = response.choices[0].message.content.strip()
    # Remove ```json fences if the model adds them
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


if __name__ == "__main__":
    test_script = (
        "Mama Ngozi don open her shop for Ariaria market! Fresh smoked fish, "
        "dry pepper, crayfish wey go make your soup sweet well well. You no need "
        "waka far again. Her prices dey reasonable, and she go even dash you small "
        "extra if you be regular customer. Come early in the morning before "
        "everything finish. Ask anybody for the market, dem go show you Mama Ngozi "
        "stall. Na quality she dey sell, no be story!"
    )

    plan = plan_scenes(test_script)

    os.makedirs("output", exist_ok=True)
    with open("output/scenes.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(json.dumps(plan, indent=2, ensure_ascii=False))