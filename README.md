# yt-vid-to-shorts

A Claude Code skill that turns any YouTube video into a gallery of AI-picked vertical short-form clips — each with a generated title, caption, hashtags, and its own download button — rendered as a styled HTML page.

![gallery screenshot](./docs/demo/gallery_mcp_talk.png)

## Demo

Ran against [`The Future of MCP — David Soria Parra, Anthropic`](https://www.youtube.com/watch?v=v3Fr2JR47KA).

### 01 · MCP Apps Ship Their Own Interface
An MCP server can now ship a full application — not a plugin, not rendered on the fly, not hardcoded. Drop the server into Claude, ChatGPT, or VS Code and it just works. But to pull that off you need something most AI tooling skips: semantics.

`#mcp` `#agentbuilding` `#anthropic` `#aidev` `#shorts`

### 02 · MCP Hit 110M Downloads Faster Than React
110 million monthly downloads — and that's not just Anthropic's clients. OpenAI, Google ADK, LangChain, thousands of frameworks are all pulling MCP as a dependency. React took twice as long to hit this volume.

`#mcp` `#openstandards` `#aiengineering` `#anthropic` `#shorts`

### 03 · Our Agents Still Suck — Here's the Fix
Agents in 2026 aren't there yet — partly because of model limitations, but mostly because we haven't talked about the right techniques. The number-one thing to build: progressive discovery.

`#agentbuilding` `#mcp` `#llmtips` `#aidev` `#shorts`

### 04 · Stop Wrapping REST APIs in MCP
Every time a REST-to-MCP conversion tool shows up, it's a bit cringe. Design for an agent the same way you'd design for a human — then give the model an execution environment so it can compose tools in code.

`#mcp` `#mcpserver` `#agentdesign` `#aiengineering` `#shorts`

## Install

Drop this directory into your Claude skills path:

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
4. `scripts/cut_clips.py` — ffmpeg re-encode with `blur-pad` (default) / `crop` / `letterbox` / `source` fit modes, audio loudness normalized to -16 LUFS.
5. `scripts/render_gallery.py` — injects the clips into an editorial-style HTML template.
6. `scripts/serve.py` — serves the gallery on `http://127.0.0.1:8723/gallery.html` so `<video>` playback works (Chrome blocks it over `file://`).

## Use it

Paste a YouTube URL to Claude along with any of: "make shorts", "clip this", "pull the highlights", "break this up". The skill handles the rest.

## Manual run

```bash
WORK=./work && mkdir -p "$WORK/clips"
python3 scripts/fetch.py 'https://www.youtube.com/watch?v=v3Fr2JR47KA' "$WORK"
python3 scripts/parse_vtt.py "$WORK/captions.vtt" "$WORK/transcript.json"
# ... write $WORK/proposals.json (see SKILL.md schema) ...
python3 scripts/cut_clips.py "$WORK/proposals.json" "$WORK/video.mp4" "$WORK/clips"
python3 scripts/render_gallery.py "$WORK/proposals.json" "$WORK/clips" "$WORK/meta.json" assets/gallery.html.template "$WORK/gallery.html"
python3 scripts/serve.py "$WORK"  # opens http://127.0.0.1:8723/gallery.html
```

## Fit modes

| Mode | When to use |
| --- | --- |
| `blur-pad` (default) | Any source. Blurred, zoomed-to-fill backdrop with the unmodified frame centered on top. The Reels/TikTok look. |
| `crop` | Talking-head videos where the subject is centered. Center-crops 16:9 → 9:16. |
| `letterbox` | Preserve everything with solid black bars top and bottom. |
| `source` | Keep original aspect ratio (no 9:16 conversion). |

## Layout

```
yt-vid-to-shorts/
├── SKILL.md                     # orchestrator Claude reads
├── scripts/
│   ├── fetch.py
│   ├── parse_vtt.py
│   ├── cut_clips.py
│   ├── render_gallery.py
│   └── serve.py
├── assets/
│   └── gallery.html.template    # editorial / newsprint aesthetic
└── docs/demo/                   # sample run against the MCP talk video
```

## License

MIT
