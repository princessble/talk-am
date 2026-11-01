import base64
import json
import os
import re
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

MODEL = "muse-spark-1.3"

BLIND_PROMPT = """Describe exactly what you see in this image, in 2 to 3 plain
sentences. Say who is there, what they are DOING with their hands and body,
what objects are around them, and where they seem to be.
Only describe what is clearly visible. Do not guess a story."""

JUDGE_PROMPT = """You are Cultural Eye, a strict art director for Talk Am, an app
that makes short videos for Nigerian creators. Most first-draft images have at
least one problem. A score of 9 or 10 is rare and must be earned.

What the creator says in this scene:
{narration}

Main character that should appear:
{main_character}

An independent viewer looked at the image WITHOUT knowing the story and wrote:
"{blind_description}"

Steps:
1. Pick the single most important action or object from the creator's words
   that a camera could actually show (for example "opening her shop" or
   "giving extra to a customer"). If the words are a slogan, an opinion or a
   time of day, pick the closest thing a photo can show, and judge only that.
2. Decide if the independent viewer's description clearly shows that key action.
   If they did not mention it, it is NOT clearly shown.
3. Look at the image yourself to check the Nigerian setting, the character and
   any visible text.

Reply with JSON only:
{{
  "key_action": "the key action from the creator's words",
  "checks": {{
    "matches_words": true,
    "nigerian_setting": true,
    "same_character": true,
    "no_text": true
  }},
  "score": 6,
  "problems": ["short, specific problem"],
  "better_prompt": "improved photorealistic vertical 9:16 image prompt in plain English that makes the key action obvious, or empty string if no problems"
}}

Scoring: 9-10 only if the key action is obvious at first glance and every check
passes. 7-8 if all checks pass but it could be clearer. 6 or below if any check fails."""


def image_to_data_url(path: str) -> str:
    """Shrink the image and turn it into text the model can read (saves credits)."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((768, 768))
    buffer = BytesIO()
    img.save(buffer, "JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{encoded}"


def ask_with_image(prompt: str, path: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_to_data_url(path)}},
                ],
            }
        ],
    )
    return response.choices[0].message.content.strip()


def review_image(path: str, scene: dict, main_character: str = "") -> dict:
    """Step 1: describe the image blind. Step 2: judge it against the creator's words."""
    blind = ask_with_image(BLIND_PROMPT, path)

    judge_prompt = JUDGE_PROMPT.format(
        narration=scene["narration"],
        main_character=main_character or "none",
        blind_description=blind.replace('"', "'"),
    )
    text = ask_with_image(judge_prompt, path)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    verdict = json.loads(text)

    verdict["what_i_see"] = blind
    verdict["passed"] = all(verdict["checks"].values()) and verdict["score"] >= 7
    return verdict


if __name__ == "__main__":
    with open("output/scenes.json", encoding="utf-8") as f:
        plan = json.load(f)

    for scene in plan["scenes"]:
        path = f"output/scene_{scene['number']}.png"
        verdict = review_image(path, scene, plan.get("main_character", ""))
        status = "PASS" if verdict["passed"] else "REDO"
        print(f"\n=== Scene {scene['number']}: {status}  (score {verdict['score']}/10) ===")
        print(f"Key action: {verdict['key_action']}")
        print(f"Blind look: {verdict['what_i_see']}")
        for problem in verdict.get("problems", []):
            print(f"   - {problem}")