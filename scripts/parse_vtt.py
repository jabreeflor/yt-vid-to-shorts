#!/usr/bin/env python3
"""Parse a YouTube auto-caption VTT file into a structured transcript.json.

Usage:
    python parse_vtt.py <captions.vtt> <transcript.json>

Output JSON structure:
    {
      "duration": <float seconds, last word end>,
      "text": "<full plaintext transcript>",
      "segments": [{"start": float, "end": float, "text": str}],
      "words": [{"t": float, "w": str}]
    }

Notes on YouTube auto-captions:
- Cues overlap as a rolling window — each new cue repeats the previous line plus
  a new word. We dedupe by tracking word-level onsets.
- Inline word timestamps appear as <HH:MM:SS.mmm><c>word</c> inside cue bodies.
"""
import html
import json
import re
import sys
from pathlib import Path

TIMESTAMP_RE = re.compile(r"<(\d{2}):(\d{2}):(\d{2})\.(\d{3})>")
TAG_RE = re.compile(r"</?c[^>]*>")
CUE_TIMING_RE = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})"
)


def hms_to_seconds(hms: str) -> float:
    h, m, rest = hms.split(":")
    s, ms = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_cue_body(body: str, cue_start: float) -> list[tuple[float, str]]:
    """Return list of (timestamp, word) from a cue body with inline word timings."""
    body = html.unescape(TAG_RE.sub("", body))
    pieces: list[tuple[float, str]] = []
    pos = 0
    current_time = cue_start
    for match in TIMESTAMP_RE.finditer(body):
        pre = body[pos:match.start()].strip()
        if pre:
            for word in pre.split():
                pieces.append((current_time, word))
        h, m, s, ms = match.groups()
        current_time = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
        pos = match.end()
    tail = body[pos:].strip()
    if tail:
        for word in tail.split():
            pieces.append((current_time, word))
    return pieces


def parse_vtt(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    words: list[tuple[float, str]] = []
    cues: list[dict] = []

    seen_keys: set[tuple[float, str]] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        timing_match = CUE_TIMING_RE.match(line)
        if not timing_match:
            i += 1
            continue
        cue_start = hms_to_seconds(timing_match.group(1))
        cue_end = hms_to_seconds(timing_match.group(2))
        i += 1
        body_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not CUE_TIMING_RE.match(lines[i]):
            body_lines.append(lines[i])
            i += 1
        # YouTube auto-captions stack the previous (plain) echo line(s) first,
        # followed by one line containing the fresh `<t><c>word</c>` stream.
        # Only the line(s) containing inline timestamps carry new content.
        new_lines = [ln for ln in body_lines if TIMESTAMP_RE.search(ln)]
        if not new_lines:
            continue  # pure echo cue — skip
        body = " ".join(new_lines)
        pieces = parse_cue_body(body, cue_start)
        cue_text = []
        for t, w in pieces:
            # Dedupe by (onset, word) — multiple plain words can share cue_start.
            key = (round(t, 3), w)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            words.append((t, w))
            cue_text.append(w)
        if cue_text:
            cues.append({
                "start": cue_start,
                "end": cue_end,
                "text": " ".join(cue_text),
            })

    full_text = " ".join(w for _, w in words)
    duration = words[-1][0] if words else 0.0
    return {
        "duration": duration,
        "text": full_text,
        "segments": cues,
        "words": [{"t": round(t, 3), "w": w} for t, w in words],
    }


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = parse_vtt(src)
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        f"[parse_vtt] {len(data['words'])} words, "
        f"{len(data['segments'])} segments, duration {data['duration']:.1f}s -> {dst}"
    )


if __name__ == "__main__":
    main()
