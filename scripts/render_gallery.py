#!/usr/bin/env python3
"""Render the HTML gallery from template + proposals + clips.

Usage:
    python render_gallery.py <proposals.json> <clips_dir> <meta.json> <template.html> <out.html>

The template contains tokens replaced here:
    {{SOURCE_TITLE}}, {{SOURCE_URL}}, {{SOURCE_CHANNEL}}, {{GENERATED_AT}},
    {{CLIP_COUNT}}, {{CLIP_CARDS}}

A separate per-card block between <!--CARD--> ... <!--/CARD--> is used as a
sub-template for each clip, with tokens:
    {{CLIP_ID}}, {{CLIP_INDEX}}, {{CLIP_SRC}}, {{CLIP_TITLE}},
    {{CLIP_DESCRIPTION}}, {{CLIP_HASHTAGS_HTML}}, {{CLIP_HASHTAGS_TEXT}},
    {{CLIP_START}}, {{CLIP_END}}, {{CLIP_DURATION}}, {{CLIP_CAPTION_TEXT}}
"""
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path


CARD_RE = re.compile(r"<!--CARD-->(.*?)<!--/CARD-->", re.DOTALL)


def fmt_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def render_card(template: str, clip: dict, index: int) -> str:
    start = float(clip["start"])
    end = float(clip["end"])
    title = clip.get("title", "Untitled short")
    description = clip.get("description", "")
    hashtags = clip.get("hashtags", [])
    tags_html = " ".join(
        f'<span class="tag">{html.escape(t.lstrip("#"))}</span>'
        for t in hashtags
    )
    tags_text = " ".join(
        (t if t.startswith("#") else f"#{t}") for t in hashtags
    )
    caption_text = description + ("\n\n" + tags_text if tags_text else "")
    mapping = {
        "{{CLIP_ID}}": clip["id"],
        "{{CLIP_INDEX}}": f"{index + 1:02d}",
        "{{CLIP_SRC}}": f"clips/{clip['id']}.mp4",
        "{{CLIP_TITLE}}": html.escape(title),
        "{{CLIP_DESCRIPTION}}": html.escape(description),
        "{{CLIP_HASHTAGS_HTML}}": tags_html,
        "{{CLIP_HASHTAGS_TEXT}}": html.escape(tags_text),
        "{{CLIP_START}}": fmt_ts(start),
        "{{CLIP_END}}": fmt_ts(end),
        "{{CLIP_DURATION}}": f"{end - start:.1f}s",
        "{{CLIP_CAPTION_TEXT}}": html.escape(caption_text),
    }
    out = template
    for token, value in mapping.items():
        out = out.replace(token, value)
    return out


def main() -> None:
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    proposals = json.loads(Path(sys.argv[1]).read_text())
    clips_dir = Path(sys.argv[2])  # informational; card src is relative "clips/<id>.mp4"
    meta = json.loads(Path(sys.argv[3]).read_text())
    template_path = Path(sys.argv[4])
    out_path = Path(sys.argv[5])

    template = template_path.read_text()
    card_match = CARD_RE.search(template)
    if not card_match:
        raise SystemExit("render: template missing <!--CARD--> ... <!--/CARD--> block")
    card_tpl = card_match.group(1)

    clips = proposals.get("clips", [])
    cards_html = "\n".join(render_card(card_tpl, c, i) for i, c in enumerate(clips))

    shell = template[: card_match.start()] + "{{CLIP_CARDS}}" + template[card_match.end():]

    title = meta.get("title") or proposals.get("source_title") or "Untitled"
    channel = meta.get("channel") or ""
    url = meta.get("url") or proposals.get("source_url") or ""
    replacements = {
        "{{SOURCE_TITLE}}": html.escape(title),
        "{{SOURCE_URL}}": html.escape(url),
        "{{SOURCE_CHANNEL}}": html.escape(channel),
        "{{GENERATED_AT}}": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{{CLIP_COUNT}}": str(len(clips)),
        "{{CLIP_CARDS}}": cards_html,
    }
    rendered = shell
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)

    out_path.write_text(rendered, encoding="utf-8")
    print(f"[render] wrote {out_path} ({len(clips)} clips)")


if __name__ == "__main__":
    main()
