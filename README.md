# Talk Am 🎙️➜🎬

**Send a voice note, get a video.**
*Talk am. We go show am.*

Talk Am turns a story told in **Nigerian English, Pidgin or Igbo-flavoured Pidgin** into a short vertical video, in the creator's own voice and exact words. An agent built on Meta's Muse models plans the scenes, draws them, **checks each picture with its own eyes**, and redraws anything that doesn't match the story.

**Live app:** https://princessble--talk-am-web.us-east.modal.run
*(Protected by a passcode so strangers can't spend the API credits. The passcode is in the hackathon submission.)*

Built for the **Meta Global AI Developer Hackathon** (Indie track, theme: *Build for Your World*).

---

## Why

Most AI video tools are built around American or British English. Nigerian creators either rewrite their scripts to suit the tool or give up. I'm Nigerian and I run an education community on Facebook, and I see people with good ideas held back because video is slow and expensive to make. Talk Am keeps the creator's words exactly as they say them: "Gba ga mgbam!", "nkoo", "ogbonge soup sweet wella" and all.

## How it works

| Step | What happens | Meta model |
|---|---|---|
| 1. Scene director | Splits the script into 4–6 scenes, keeps every word exactly as written, writes a detailed Nigerian-setting picture prompt and one main-character description | **Muse Spark 1.3** |
| 2. Artist | Draws scene 1, then uses it as a **reference image** so the same character appears in every scene | **Muse Image 1.0** (generate + edit) |
| 3. Cultural Eye agent | Checks every picture (see below). Failed pictures get a better prompt and are redrawn; the best try is kept | **Muse Spark 1.3** (vision) |
| 4. Editor | Finds the natural pauses in the voice note, cuts scenes on those pauses, adds camera moves, cross-fades and captions in the creator's own words | ffmpeg |

### Cultural Eye: a verifiable agent

An AI that sees both the picture *and* the prompt tends to "see" what it was told to see. My first version scored every image 9/10. So Cultural Eye works in two steps:

1. **Blind look:** Muse Spark describes the picture *without knowing the story*.
2. **Judge:** a second call compares that honest description with the creator's words, checks the Nigerian setting, the character and stray text, and scores it.

The **code**, not the model, decides PASS or REDO (all checks true and score ≥ 7). If it fails, the agent uses Cultural Eye's improved prompt and redraws once, then keeps the best-scoring version. Every step is shown live on the web page, so you can watch the agent think.

Example from a real run: *"REDO 6/10: viewer sees her holding a cloth, not clearly opening the shop"* → redrawn → she's pulling back the stall curtain.

## Built during the hackathon

All code in this repo was written between **Oct 27 and Nov 4, 2026**; see the commit history.
- Scene director with exact-words rule and character description
- Consistent characters using Muse Image reference editing (with a WebP→PNG fix)
- Cultural Eye blind-look agent and redraw loop
- Pause-timed video editor with camera moves, cross-fades and captions
- Flask web app with a live agent view (PASS/REDO cards, blind look, ★ Kept)
- Online deployment on Modal

## Run it yourself

Requires Python 3.12+, ffmpeg, and a Meta Model API key.

```bash
git clone https://github.com/princessble/talk-am.git
cd talk-am
python -m venv venv
venv\Scripts\activate        # Windows  (source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
echo MODEL_API_KEY=your-key-here > .env
python app.py                # then open http://localhost:5000
```

Deploy: `modal deploy modal_app.py` (needs a Modal secret called `talkamsecrets` with `MODEL_API_KEY` and `APP_PASSCODE`).

## Files

| File | Job |
|---|---|
| `scenes.py` | Scene director (Muse Spark) |
| `images.py` | Draws scenes with a consistent character (Muse Image) |
| `cultural_eye.py` | Blind-look checker (Muse Spark vision) |
| `agent.py` | Draw → check → fix → redraw loop |
| `video.py` | Pause-timed editing, camera moves, captions (ffmpeg) |
| `app.py` + `templates/index.html` | Web app with live agent view |
| `modal_app.py` | Online deployment |

## What's next

- **Muse Voice Transcribe:** transcribe the voice note itself, so creators don't need to type a script and captions are timed word by word.
- **SAM 3.1 "living photo":** cut the characters out of each scene so the background and people move in separate layers.
- More Nigerian languages: Yoruba, Hausa and Igbo.

## Built by

**Blessing Fortune Kwomo**, Limerick, Ireland.

MIT License
