"""Put Talk Am online with Modal.

Run from the talk-am folder:  modal deploy modal_app.py
"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "fonts-liberation", "fontconfig")
    .pip_install("openai", "python-dotenv", "flask", "requests", "pillow")
    # Copy the app's code, but never secrets, the virtual environment or test files
    .add_local_dir(
        ".",
        remote_path="/root/talkam",
        ignore=[".env", "venv", ".git", "output", "jobs", "__pycache__", "voice.m4a", "*.mp4"],
    )
)

app = modal.App("talk-am", image=image)


@app.function(
    secrets=[modal.Secret.from_name("talkamsecrets")],  # MODEL_API_KEY and APP_PASSCODE
    cpu=2,                  # enough power to film the scenes
    memory=2048,
    max_containers=1,       # one copy of the app, so every job lives in one place
    scaledown_window=300,   # go to sleep 5 minutes after the last visit, to save credit
    timeout=3600,
)
@modal.concurrent(max_inputs=50)  # the page can check progress while a video is being made
@modal.wsgi_app()
def web():
    import os
    import sys

    os.chdir("/root/talkam")
    sys.path.insert(0, "/root/talkam")
    os.makedirs("jobs", exist_ok=True)
    from app import app as flask_app

    return flask_app