import base64
import json
import os
from io import BytesIO

import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

IMAGE_MODEL = "muse-image-1.0"


def save_image(response, path: str) -> str:
    """Save the image Meta sends back as a real PNG file (Meta sends WebP)."""
    image = response.data[0]
    if getattr(image, "b64_json", None):
        data = base64.b64decode(image.b64_json)
    else:
        data = requests.get(image.url, timeout=60).content
    Image.open(BytesIO(data)).convert("RGB").save(path, "PNG")
    return path


def draw_scene(prompt: str, path: str, reference: str | None = None) -> str:
    """Draw one scene. If a reference picture is given, keep the same character."""
    if reference:
        with open(reference, "rb") as ref:
            response = client.images.edit(
                model=IMAGE_MODEL,
                image=ref,
                prompt=(
                    "Keep the exact same main character as in the reference image: "
                    "same face, skin tone, hair, outfit and head tie. "
                    "New scene: " + prompt
                ),
                n=1,
            )
    else:
        response = client.images.generate(model=IMAGE_MODEL, prompt=prompt, n=1)
    return save_image(response, path)


def draw_all(plan: dict, folder: str = "output") -> list[str]:
    """Draw every scene. Scene 1 becomes the reference for the rest."""
    os.makedirs(folder, exist_ok=True)
    has_character = bool(plan.get("main_character"))
    reference = None
    paths = []

    for scene in plan["scenes"]:
        path = os.path.join(folder, f"scene_{scene['number']}.png")
        print(f"Drawing scene {scene['number']}...")
        draw_scene(scene["image_prompt"], path, reference if has_character else None)
        if reference is None:
            reference = path
        paths.append(path)

    print("All scenes drawn!")
    return paths


if __name__ == "__main__":
    with open("output/scenes.json", encoding="utf-8") as f:
        plan = json.load(f)
    draw_all(plan)