import json
import os
import shutil

from cultural_eye import review_image
from images import draw_scene

MAX_TRIES = 2  # first drawing + one redraw


def print_report(event: dict):
    """Default reporter: print the agent's notes in the terminal."""
    if event.get("text"):
        print(event["text"])


def make_scene(scene: dict, main_character: str, reference: str | None, folder: str,
               report=print_report):
    """Draw a scene, let Cultural Eye check it, redraw if needed, keep the best."""
    number = scene["number"]
    prompt = scene["image_prompt"]
    attempts = []
    best = None

    for attempt in range(1, MAX_TRIES + 1):
        name = f"scene_{number}_try{attempt}.png"
        path = os.path.join(folder, name)
        report({"type": "drawing", "scene": number, "try": attempt,
                "text": f"  Drawing (try {attempt})..."})
        draw_scene(prompt, path, reference)

        report({"type": "checking", "scene": number, "try": attempt,
                "text": "  Cultural Eye is looking..."})
        verdict = review_image(path, scene, main_character)
        status = "PASS" if verdict["passed"] else "REDO"

        result = {
            "try": attempt,
            "prompt": prompt,
            "image": name,
            "score": verdict["score"],
            "passed": verdict["passed"],
            "key_action": verdict.get("key_action", ""),
            "what_i_see": verdict.get("what_i_see", ""),
            "problems": verdict.get("problems", []),
        }
        attempts.append(result)
        lines = [f"  Cultural Eye: {status} ({verdict['score']}/10)"]
        lines += [f"     - {p}" for p in result["problems"]]
        report({"type": "verdict", "scene": number, **result, "text": "\n".join(lines)})

        if best is None or verdict["score"] > best["score"]:
            best = result
        if verdict["passed"]:
            break
        if verdict.get("better_prompt") and attempt < MAX_TRIES:
            prompt = verdict["better_prompt"]
            report({"type": "fixing", "scene": number,
                    "text": "  Fixing the prompt and trying again..."})

    final = os.path.join(folder, f"scene_{number}.png")
    shutil.copyfile(os.path.join(folder, best["image"]), final)
    report({"type": "kept", "scene": number, "try": best["try"], "score": best["score"],
            "image": best["image"],
            "text": f"  Kept try {best['try']} (score {best['score']}/10)"})
    return final, attempts


def run_agent(plan: dict, folder: str = "output", report=print_report):
    """Make every scene. The final scene 1 is the reference for the rest."""
    os.makedirs(folder, exist_ok=True)
    main_character = plan.get("main_character", "")
    reference = None
    finals, log = [], []

    for scene in plan["scenes"]:
        report({"type": "scene", "scene": scene["number"], "narration": scene["narration"],
                "text": f"\nScene {scene['number']}: \"{scene['narration']}\""})
        final, attempts = make_scene(
            scene, main_character, reference if main_character else None, folder, report
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
    report({"type": "agent_done", "text": f"\nDone! The agent's notes are saved in {folder}/agent_log.json"})
    return finals, log


if __name__ == "__main__":
    with open("output/scenes.json", encoding="utf-8") as f:
        plan = json.load(f)
    run_agent(plan)