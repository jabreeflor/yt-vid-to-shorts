---
name: yt-vid-to-shorts
description: Turn any YouTube video into a gallery of AI-picked vertical short-form clips with generated titles, descriptions, and hashtags. Use this whenever a user pastes a YouTube URL and asks for shorts, clips, highlights, reels, TikToks, a compilation, or "break this video up" — even if they don't say the word "shorts" explicitly. Also use when the user wants the best moments from a long video auto-extracted and rendered as a shareable HTML page with per-clip download buttons.
user-invocable: true
---

# yt-vid-to-shorts

Turn one long YouTube video into a gallery of vertical (9:16) short-form clips, each with a generated title, caption, and hashtags, rendered as a styled HTML page with per-clip download buttons.

## When to use

Trigger on any of:
- A YouTube URL + words like "shorts", "clips", "highlights", "reels", "TikToks"
- "Break this video up", "pull the best moments", "make me a compilation"
- A request to summarize a video visually or generate social-ready snippets

## Inputs

- `url` — YouTube URL (required)
- `count` — number of shorts to propose (default **4**)
- `vertical` — crop to 9:16 vertical (default **true**; pass `--no-vertical` to preserve source aspect)

## What it does

1. Downloads the video (≤1080p, single mp4) and its auto-generated YouTube captions.
2. Parses the captions into a word-level-timestamped transcript.
3. **You (Claude) read the transcript and pick the clips.** Write your selections to `work/proposals.json` using the schema below.
4. Cuts each clip with `ffmpeg` (frame-accurate re-encode, optional 9:16 center-crop).
5. Renders a styled HTML gallery with inline video players, download buttons, titles, descriptions, and hashtag chips.

## End-to-end flow

Let `SKILL_DIR` = this skill's directory, `WORK` = a fresh `work/` subdirectory next to where you're running (or `/tmp/yt-vid-to-shorts-<id>/` if you don't have a good local choice), and `URL` = the user's YouTube URL.

```bash
mkdir -p "$WORK/clips"

# 1. Fetch video + auto-captions + meta
python3 "$SKILL_DIR/scripts/fetch.py" "$URL" "$WORK"

# 2. Parse VTT -> transcript.json
python3 "$SKILL_DIR/scripts/parse_vtt.py" "$WORK/captions.vtt" "$WORK/transcript.json"
```

### 3. Pick the clips (your job)

Read `$WORK/transcript.json`. It has:
- `duration` (seconds)
- `text` (full plaintext)
- `segments` — caption-cue-level chunks with `start`/`end`
- `words` — word-level onsets, `[{"t": 12.345, "w": "word"}, ...]`

**Selection rubric** (default N = 4 clips):
- **Length**: 20–60 seconds. Shorter is fine if the moment is self-contained. Avoid <15s unless it's an unusually tight punchline.
- **Hook**: first 3 seconds of the clip must grab — a question, a strong claim, a surprising line, a number, a name. Not "so, um, anyway…"
- **Self-contained**: the clip should make sense without the surrounding context. If it references "this" or "what I was saying before," it's not self-contained — push the start earlier or skip it.
- **Payoff before the end**: the clip should resolve — reach a punchline, insight, or natural pause — rather than cutting mid-sentence.
- **Snap to word boundaries**: align `start` to a word's onset from the `words` array, and `end` to just after a word (add ~0.2s of tail). Never cut mid-word.
- **Distribute across the video**: unless the first third is disproportionately rich, pick clips from across the runtime.
- **Non-overlapping**: clips must not overlap each other.

Write `$WORK/proposals.json`:

```json
{
  "source_url": "<URL>",
  "source_title": "<title from work/meta.json>",
  "clips": [
    {
      "id": "clip_01",
      "start": 73.2,
      "end": 112.8,
      "title": "Punchy hook, <=60 chars, no clickbait fluff",
      "description": "2-3 sentence caption in the creator's voice. Sets up the moment without spoiling the payoff.",
      "hashtags": ["#topic", "#niche", "#broad", "#shorts"],
      "rationale": "One sentence on why this moment works — for the user's review."
    }
  ]
}
```

Notes on the metadata you generate:
- **Title**: short, declarative, ideally starts with a strong noun or verb. Avoid "you won't believe…" / "this will shock you…" and similar generic bait. If the speaker has a signature phrasing or named concept, use it.
- **Description**: 2–3 sentences max. Match the tone of the source. End with a call-to-action only if natural.
- **Hashtags**: 3–5 tags, mix of specific-to-topic and broader-reach. Include `#shorts` as one of them. Lowercase, no spaces.

### 4. Cut and render

```bash
# 4. Cut clips (9:16 by default; add --no-vertical to preserve source aspect)
python3 "$SKILL_DIR/scripts/cut_clips.py" "$WORK/proposals.json" "$WORK/video.mp4" "$WORK/clips"

# 5. Render the gallery
python3 "$SKILL_DIR/scripts/render_gallery.py" \
    "$WORK/proposals.json" \
    "$WORK/clips" \
    "$WORK/meta.json" \
    "$SKILL_DIR/assets/gallery.html.template" \
    "$WORK/gallery.html"

# 6. Serve + open in browser. Do NOT `open` the file directly — Chrome's file://
# policy silently breaks <video> playback (no audio, frozen frame).
python3 "$SKILL_DIR/scripts/serve.py" "$WORK" &
SERVE_PID=$!
# Tell the user the URL; they stop the server with Ctrl+C or `kill $SERVE_PID`.
```

## Output contract

After the skill finishes, tell the user:
- The path to `gallery.html` (open it to preview clips in-browser)
- Each clip's filename under `work/clips/clip_NN.mp4` is independently downloadable from the gallery
- If any proposals feel off, the user can edit `proposals.json` by hand and rerun `cut_clips.py` + `render_gallery.py`

## Troubleshooting

- **"no auto-captions available"**: the video has captions disabled. Suggest the user pick a different video, or install `whisper` / `faster-whisper` and transcribe locally (outside this skill's scope).
- **Region-locked / age-gated video**: `yt-dlp` may need cookies. Run `yt-dlp --cookies-from-browser firefox <url>` (or another browser) and see if that helps before falling back.
- **ffmpeg fails on a specific clip**: usually the `end` exceeds the video duration — check `work/meta.json` `duration` and clamp.
- **Source video is already ≤9:16 vertical**: `cut_clips.py` detects this via `ffprobe` and skips the crop filter automatically.
- **Non-ASCII title**: `fetch.py` uses fixed filename templates (`video.mp4`, `captions.vtt`) so unicode titles don't break the pipeline.
- **Videos look frozen / play with no audio**: you opened `gallery.html` directly via `file://`. Chrome blocks reliable `<video>` playback from local files. Run `scripts/serve.py` and open the `http://127.0.0.1:8723/gallery.html` URL it prints.

## Tips

- The default of 4 clips is a good volume for most 10–30 minute videos. For very long videos (podcast-length, 1hr+), consider 6–8.
- If the video is a tight monologue, the `segments` array is more useful than `words`. If it's conversational, `words` gives you finer control.
- To iterate without re-downloading: edit `proposals.json` and rerun only `cut_clips.py` + `render_gallery.py`.
