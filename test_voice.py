import os
import re
import subprocess

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

os.makedirs("output", exist_ok=True)
WAV = "output/voice.wav"

# 1. Convert the voice note to clean mono 16 kHz WAV
subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-i", "voice.m4a",
     "-ac", "1", "-ar", "16000", WAV],
    check=True,
)
print("1. Converted voice.m4a to output/voice.wav")

# 2. Find the length and the natural pauses (backup plan, no AI)
result = subprocess.run(
    ["ffmpeg", "-i", WAV, "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
    capture_output=True, text=True,
)
duration = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
if duration:
    h, m, s = duration.groups()
    print(f"2. Voice length: {int(h) * 3600 + int(m) * 60 + float(s):.1f} seconds")
pauses = re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", result.stderr)
print(f"   Found {len(pauses)} pauses:")
for end, length in pauses:
    start = float(end) - float(length)
    print(f"   - pause from {start:.2f}s to {float(end):.2f}s")

# 3. Try Muse Voice Transcribe with timings
print("\n3. Asking Muse Voice Transcribe...")
try:
    with open(WAV, "rb") as audio:
        response = client.audio.transcriptions.create(
            model="muse-voice-transcribe-1.0",
            file=audio,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )
    print("   It worked! Here is what came back:")
    print(response.model_dump_json(indent=2)[:3000])
except Exception as error:
    print("   With timings failed:", error)
    print("\n   Trying plain text instead...")
    try:
        with open(WAV, "rb") as audio:
            response = client.audio.transcriptions.create(
                model="muse-voice-transcribe-1.0",
                file=audio,
            )
        print("   Plain text worked:", response.text)
    except Exception as error2:
        print("   Plain text also failed:", error2)