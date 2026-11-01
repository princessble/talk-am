import json
import os
import threading
import time
import traceback
import uuid

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request, send_from_directory

load_dotenv()

from agent import run_agent  # noqa: E402  (needs the key loaded first)
from scenes import plan_scenes  # noqa: E402
from video import make_video  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # voice notes up to 25 MB

JOBS_DIR = "jobs"
PASSCODE = os.environ.get("APP_PASSCODE", "")  # optional: protects your credits online
MAX_SCRIPT = 1500
AUDIO_TYPES = {".m4a", ".mp3", ".mp4", ".ogg", ".opus", ".wav", ".webm", ".aac", ".amr"}

jobs: dict[str, dict] = {}
one_at_a_time = threading.Semaphore(1)  # make one video at a time


def add_event(job_id: str, event: dict):
    event = {k: v for k, v in event.items() if k != "text" or v}
    event["time"] = round(time.time() - jobs[job_id]["started"], 1)
    jobs[job_id]["events"].append(event)
    if event.get("text"):
        print(f"[{job_id}] {event['text']}")


def make_talk_am_video(job_id: str, script: str, voice_path: str):
    """The full Talk Am pipeline, run in the background for one job."""
    folder = f"{JOBS_DIR}/{job_id}"
    say = lambda text: add_event(job_id, {"type": "log", "text": text})  # noqa: E731
    try:
        with one_at_a_time:
            jobs[job_id]["status"] = "running"
            say("The scene director is reading your story...")
            plan = plan_scenes(script)
            with open(f"{folder}/scenes.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            add_event(job_id, {
                "type": "plan",
                "title": plan.get("title", ""),
                "main_character": plan.get("main_character", ""),
                "scenes": [{"number": s["number"], "narration": s["narration"]} for s in plan["scenes"]],
                "text": f"Planned {len(plan['scenes'])} scenes.",
            })

            run_agent(plan, folder, report=lambda e: add_event(job_id, e))

            say("Putting your voice, the scenes and the captions together...")
            make_video(plan, voice_path, folder, say=say)
            jobs[job_id]["video"] = "talk_am_video.mp4"
            jobs[job_id]["status"] = "done"
            add_event(job_id, {"type": "done", "text": "Your video is ready!"})
    except Exception as error:  # show the problem on the page instead of failing silently
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        add_event(job_id, {"type": "error", "text": f"Something went wrong: {error}"})


@app.get("/")
def home():
    return render_template("index.html", needs_passcode=bool(PASSCODE))


@app.post("/make")
def make():
    if PASSCODE and request.form.get("passcode", "") != PASSCODE:
        return jsonify(error="Wrong passcode."), 403

    script = request.form.get("script", "").strip()
    voice = request.files.get("voice")
    if not script:
        return jsonify(error="Please paste your script."), 400
    if len(script) > MAX_SCRIPT:
        return jsonify(error=f"Please keep the script under {MAX_SCRIPT} characters."), 400
    if not voice or not voice.filename:
        return jsonify(error="Please add your voice note."), 400
    ext = os.path.splitext(voice.filename)[1].lower()
    if ext not in AUDIO_TYPES:
        return jsonify(error="That file doesn't look like a voice note. Try .m4a, .mp3, .ogg or .wav."), 400

    job_id = uuid.uuid4().hex[:10]
    folder = f"{JOBS_DIR}/{job_id}"
    os.makedirs(folder, exist_ok=True)
    voice_path = f"{folder}/voice_in{ext}"
    voice.save(voice_path)

    waiting = one_at_a_time._value == 0  # another video is being made right now
    jobs[job_id] = {"status": "waiting" if waiting else "starting", "events": [],
                    "started": time.time(), "video": None}
    if waiting:
        add_event(job_id, {"type": "log", "text": "Another video is being made. Yours is next in line..."})
    threading.Thread(target=make_talk_am_video, args=(job_id, script, voice_path), daemon=True).start()
    return jsonify(job_id=job_id)


@app.get("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        abort(404)
    since = request.args.get("since", 0, type=int)
    return jsonify(status=job["status"], events=job["events"][since:], total=len(job["events"]),
                   video=job["video"])


@app.get("/jobs/<job_id>/<path:filename>")
def job_file(job_id, filename):
    if job_id not in jobs or "/" in filename or "\\" in filename:
        abort(404)
    return send_from_directory(os.path.abspath(f"{JOBS_DIR}/{job_id}"), filename)


if __name__ == "__main__":
    os.makedirs(JOBS_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)