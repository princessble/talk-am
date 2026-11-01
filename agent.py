import json
import os
import shutil

from cultural_eye import review_image
from images import draw_scene

MAX_TRIES = 2  # first drawing + one redraw


def make_scene(scene: dict, main_character: str, reference: str | None, folder: str):
    """Draw a scene, let Cultural Eye check it, redraw if needed, keep the best."""
    prompt = scene["image_prompt"]
    attempts = []
    best = None

    for attempt in range(1, MAX_TRIES + 1):
        path = os.path.join(folder, f"scene_{scene['number']}_try{attempt}.png")
        print(f"  Drawing (try {attempt})...")
        draw_scene(prompt, path, reference)

        verdict = review_image(path, scene, main_character)
        status = "PASS" if verdict["passed"] else "REDO"
        print(f"  Cultural Eye: {status} ({verdict['score']}/10)")
        for problem in verdict.get("problems", []):
            print(f"     - {problem}")

        attempts.append({
            "try": attempt,
            "prompt": prompt,
            "image": path,
            "score": verdict["score"],
            "passed": verdict["passed"],
            "key_action": verdict.get("key_action", ""),
            "what_i_see": verdict.get("what_i_see", ""),
            "problems": verdict.get("problems", []),
        })

        if best is None or verdict["score"] > best["score"]:
            best = attempts[-1]
        if verdict["passed"]:
            break
        if verdict.get("better_prompt") and attempt < MAX_TRIES:
            prompt = verdict["better_prompt"]
            print("  Fixing the prompt and trying again...")

    final = os.path.join(folder, f"scene_{scene['number']}.png")
    shutil.copyfile(best["image"], final)
    print(f"  Kept try {best['try']} (score {best['score']}/10)")
    return final, attempts


def run_agent(plan: dict, folder: str = "output"):
    """Make every scene. The final scene 1 is the reference for the rest."""
    os.makedirs(folder, exist_ok=True)
    main_character = plan.get("main_character", "")
    reference = None
    finals, log = [], []

    for scene in plan["scenes"]:
        print(f"\nScene {scene['number']}: \"{scene['narration']}\"")
        final, attempts = make_scene(
            scene, main_character, reference if main_character else None, folder
        )
        if reference is None:
            reference = final
        finals.append(final)
        log.append({
            "scene": scene["number"],
            "narration": scene["narration"],
            "final_image": final,
            "attempts": attempts,
        })

    with open(os.path.join(folder, "agent_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print("\nDone! The agent's notes are saved in output/agent_log.json")
    return finals, log


if __name__ == "__main__":
    with open("output/scenes.json", encoding="utf-8") as f:
        plan = json.load(f)
    run_agent(plan)