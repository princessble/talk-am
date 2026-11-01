import json
import os
import re
import subprocess

FPS = 30
WIDTH, HEIGHT = 1080, 1920
CLIPS = "output/clips"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run ffmpeg. If it fails, show the last lines of its error message."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:\n" + "\n".join(result.stderr.strip().splitlines()[-15:]))
        raise SystemExit(1)
    return result


def prepare_voice(voice_in: str, wav_out: str = "output/voice.wav") -> str:
    """Turn the voice note into clean mono WAV."""
    run(["ffmpeg", "-y", "-i", voice_in, "-ac", "1", "-ar", "48000", wav_out])
    return wav_out


def listen(wav: str) -> tuple[float, list[tuple[float, float]]]:
    """Find how long the voice is and where the natural pauses are."""
    result = subprocess.run(
        ["ffmpeg", "-i", wav, "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr).groups()
    duration = int(h) * 3600 + int(m) * 60 + float(s)
    pauses = []
    for end, length in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", result.stderr):
        pauses.append((float(end) - float(length), float(end)))
    return duration, pauses


def plan_timing(scenes: list[dict], duration: float, pauses: list[tuple[float, float]]):
    """Decide when each scene starts and ends, cutting on natural pauses."""
    speech_start, speech_end = 0.0, duration
    inner = list(pauses)
    if inner and inner[0][0] < 0.2:
        speech_start = inner.pop(0)[1]
    if inner and inner[-1][1] > duration - 0.3:
        speech_end = inner.pop()[0]

    words = [len(s["narration"].split()) for s in scenes]
    total = sum(words)
    cuts, done = [], 0
    for count in words[:-1]:
        done += count
        ideal = speech_start + (speech_end - speech_start) * done / total
        earliest = (cuts[-1] if cuts else speech_start) + 1.0
        options = [(a + b) / 2 for a, b in inner if (a + b) / 2 > earliest]
        best = min(options, key=lambda t: abs(t - ideal), default=None)
        cuts.append(best if best is not None and abs(best - ideal) < 2.5 else ideal)

    starts = [0.0] + cuts
    ends = cuts + [duration]
    talk = [(max(a, speech_start), min(b, speech_end)) for a, b in zip(starts, ends)]
    return list(zip(starts, ends)), talk


def ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_captions(scenes: list[dict], talk: list[tuple[float, float]], path: str, chunk: int = 4):
    """Write bold TikTok-style captions using the creator's exact words."""
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Talk,Arial,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,6,2,2,80,80,380,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for scene, (start, end) in zip(scenes, talk):
        words = scene["narration"].replace("{", "").replace("}", "").split()
        groups = [words[i:i + chunk] for i in range(0, len(words), chunk)]
        step = (end - start) / max(len(words), 1)
        t = start
        for group in groups:
            t_end = t + step * len(group)
            text = " ".join(group)
            lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t_end)},Talk,,0,0,0,,{text}")
            t = t_end
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


# Four camera moves, used in turn: (start zoom, end zoom, start x, end x, start y, end y)
# x and y say where the camera looks: 0 = left/top, 0.5 = middle, 1 = right/bottom
MOVES = [
    (1.00, 1.30, 0.5, 0.5, 0.5, 0.35),  # push in towards her face
    (1.30, 1.05, 0.5, 0.5, 0.3, 0.6),   # pull back to show the stall
    (1.25, 1.25, 0.15, 0.85, 0.5, 0.5), # glide from left to right
    (1.05, 1.30, 0.5, 0.5, 0.6, 0.4),   # rise and push in
]
FADE = 0.4  # seconds of cross-fade between scenes


def render_scene(image: str, seconds: float, out: str, move: int) -> str:
    """Turn one still picture into a moving clip with a smooth camera move."""
    frames = max(int(round(seconds * FPS)), 1)
    z0, z1, x0, x1, y0, y1 = MOVES[move % len(MOVES)]
    ease = f"((1-cos(PI*on/{frames}))/2)"  # starts and ends gently
    zoom = f"{z0}+({z1 - z0})*{ease}"
    x = f"(iw-iw/zoom)*({x0}+({x1 - x0})*{ease})"
    y = f"(ih-ih/zoom)*({y0}+({y1 - y0})*{ease})"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zoom}':x='{x}':y='{y}'"
        f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p"
    )
    run(["ffmpeg", "-y", "-i", image, "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
    return out


def make_video(plan: dict, voice_in: str, out: str = "output/talk_am_video.mp4") -> str:
    os.makedirs(CLIPS, exist_ok=True)
    wav = prepare_voice(voice_in)
    duration, pauses = listen(wav)
    print(f"Voice: {duration:.1f}s with {len(pauses)} pauses")

    scenes = plan["scenes"]
    timing, talk = plan_timing(scenes, duration, pauses)

    # Each clip is a little longer so neighbours can blend into each other
    last = len(scenes) - 1
    clips = []
    for i, (scene, (start, end)) in enumerate(zip(scenes, timing)):
        extra = (FADE / 2 if i in (0, last) else FADE) if last > 0 else 0
        path = os.path.join(CLIPS, f"clip_{scene['number']}.mp4")
        print(f"Scene {scene['number']}: {start:.2f}s to {end:.2f}s")
        render_scene(f"output/scene_{scene['number']}.png", end - start + extra, path, move=i)
        clips.append(path)

    write_captions(scenes, talk, "output/captions.ass")

    # Blend the clips together, then add captions and gentle fades
    inputs, chain, label = [], [], "0:v"
    for path in clips:
        inputs += ["-i", path]
    for i in range(1, len(clips)):
        offset = timing[i][0] - FADE / 2
        chain.append(f"[{label}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[v{i}]")
        label = f"v{i}"
    fade_out = max(duration - 0.6, 0)
    chain.append(
        f"[{label}]subtitles=output/captions.ass,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out:.2f}:d=0.6[vout]"
    )
    run([
        "ffmpeg", "-y", *inputs, "-i", wav,
        "-filter_complex", ";".join(chain),
        "-af", f"afade=t=out:st={fade_out:.2f}:d=0.6",
        "-map", "[vout]", "-map", f"{len(clips)}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        out,
    ])
    print(f"Video ready: {out}")
    return out


if __name__ == "__main__":
    with open("output/scenes.json", encoding="utf-8") as f:
        plan = json.load(f)
    make_video(plan, "voice.m4a")