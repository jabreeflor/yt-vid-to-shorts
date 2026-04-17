#!/usr/bin/env python3
"""Cut video clips from proposals.json using ffmpeg.

Usage:
    python cut_clips.py <proposals.json> <video.mp4> <outdir> [--no-vertical]

Defaults to 9:16 vertical center-crop. Pass --no-vertical to keep source aspect.
"""
import json
import subprocess
import sys
from pathlib import Path


def probe_aspect(video: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(video),
        ],
        capture_output=True, text=True, check=True,
    )
    w, h = result.stdout.strip().split("x")
    return int(w), int(h)


def format_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def cut_clip(video: Path, start: float, end: float, out: Path, vertical: bool, src_w: int, src_h: int) -> None:
    args = [
        "ffmpeg", "-y",
        "-ss", format_ts(start),
        "-to", format_ts(end),
        "-i", str(video),
    ]
    # Only crop if source is wider than 9:16; otherwise keep as-is
    if vertical and src_w / src_h > 9 / 16:
        args += ["-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0"]
    args += [
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(args, check=True)


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    proposals_path = Path(sys.argv[1])
    video_path = Path(sys.argv[2])
    outdir = Path(sys.argv[3])
    vertical = "--no-vertical" not in sys.argv[4:]

    outdir.mkdir(parents=True, exist_ok=True)
    proposals = json.loads(proposals_path.read_text())
    clips = proposals.get("clips", [])
    if not clips:
        raise SystemExit("cut_clips: no clips in proposals.json")

    src_w, src_h = probe_aspect(video_path)
    print(f"[cut_clips] source {src_w}x{src_h}, vertical={vertical}")

    for clip in clips:
        cid = clip["id"]
        start = float(clip["start"])
        end = float(clip["end"])
        out = outdir / f"{cid}.mp4"
        print(f"[cut_clips] {cid}: {start:.2f}s -> {end:.2f}s ({end-start:.1f}s) -> {out.name}")
        cut_clip(video_path, start, end, out, vertical, src_w, src_h)

    print(f"[cut_clips] wrote {len(clips)} clips to {outdir}")


if __name__ == "__main__":
    main()
