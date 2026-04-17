# yt-vid-to-shorts

A Claude Code skill that turns any YouTube video into a gallery of AI-picked vertical short-form clips — each with a generated title, caption, hashtags, and its own download button — rendered as a styled HTML page.

## Install

Drop this directory into your Claude skills path, e.g.:

```bash
git clone https://github.com/jabreeflor/yt-vid-to-shorts.git ~/.claude/skills/yt-vid-to-shorts
```

## Requirements

- `yt-dlp`
- `ffmpeg` (with `ffprobe`)
- `python3`

On macOS: `brew install yt-dlp ffmpeg`.

## How it works

1. `scripts/fetch.py` — downloads the video (≤1080p mp4) and YouTube's auto-caption VTT.
2. `scripts/parse_vtt.py` — turns the VTT into a word-level-timestamped `transcript.json`.
3. **Claude reads the transcript and picks clips**, writing `proposals.json`.
4. `scripts/cut_clips.py` — frame-accurate ffmpeg re-encode + center-crop to 9:16.
5. `scripts/render_gallery.py` — injects the clips into an editorial-style HTML template.

## Use it

Paste a YouTube URL to Claude along with any of: "make shorts", "clip this", "pull the highlights", "break this up". The skill handles the rest.

## Manual run

```bash
WORK=./work && mkdir -p "$WORK/clips"
python3 scripts/fetch.py 'https://www.youtube.com/watch?v=LvseZAGAIjU' "$WORK"
python3 scripts/parse_vtt.py "$WORK/captions.vtt" "$WORK/transcript.json"
# ... write $WORK/proposals.json (see SKILL.md schema) ...
python3 scripts/cut_clips.py "$WORK/proposals.json" "$WORK/video.mp4" "$WORK/clips"
python3 scripts/render_gallery.py "$WORK/proposals.json" "$WORK/clips" "$WORK/meta.json" assets/gallery.html.template "$WORK/gallery.html"
python3 scripts/serve.py "$WORK"  # opens http://127.0.0.1:8723/gallery.html
```

## Layout

```
yt-vid-to-shorts/
├── SKILL.md                     # orchestrator Claude reads
├── scripts/
│   ├── fetch.py
│   ├── parse_vtt.py
│   ├── cut_clips.py
│   └── render_gallery.py
└── assets/
    └── gallery.html.template    # editorial / newsprint aesthetic
```

## License

MIT
