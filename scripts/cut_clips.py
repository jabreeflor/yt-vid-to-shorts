#!/usr/bin/env python3
"""Cut video clips from proposals.json using ffmpeg.

Usage:
    python cut_clips.py <proposals.json> <video.mp4> <outdir> [--fit MODE]

Fit modes (how to fit a source frame into a 9:16 canvas):
    blur-pad   (default) scale to fit width, fill top/bottom with a blurred
               version of the frame — the standard Reels/TikTok look.
               Works for any source layout (reaction streams, widescreen, etc.).
    crop       center-crop to 9:16. Only sensible for talking-head videos
               where the subject is centered.
    letterbox  scale to fit width, solid black bars top/bottom.
    source     keep the original aspect ratio (no 9:16 conversion).

Audio is loudness-normalized to -16 LUFS (peak -1.5 dB) in every mode.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


CANVAS_W, CANVAS_H = 1080, 1920
FIT_MODES = {"blur-pad", "crop", "letterbox", "source"}


def probe_dims(video: Path) -> tuple[int, int]:
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(video)],
        capture_output=True, text=True, check=True,
    )
    w, h = r.stdout.strip().split("x")
    return int(w), int(h)


def format_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def build_video_filter(fit: str, src_w: int, src_h: int) -> Optional[str]:
    """Return the -vf filter string for the requested fit mode, or None to skip."""
    src_ratio = src_w / src_h
    target_ratio = CANVAS_W / CANVAS_H  # 9/16 = 0.5625

    if fit == "source":
        return None

    if fit == "crop":
        # Only crop if source is wider than 9:16; otherwise leave as-is.
        if src_ratio <= target_ratio:
            return None
        return "crop=ih*9/16:ih:(iw-ih*9/16)/2:0"

    if fit == "letterbox":
        # Scale to fit inside 1080x1920 maintaining aspect, pad with black.
        return (
            f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=decrease,"
            f"pad={CANVAS_W}:{CANVAS_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1"
        )

    if fit == "blur-pad":
        # Classic Reels look: blurred, zoomed-to-fill background layer + the
        # unmodified source scaled-to-fit on top.
        # Uses split + two parallel branches + overlay.
        return (
            "split=2[bg][fg];"
            # Background: scale to cover the canvas, crop to canvas, heavy blur
            f"[bg]scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
            f"crop={CANVAS_W}:{CANVAS_H},gblur=sigma=40,eq=brightness=-0.08:saturation=1.1[bgout];"
            # Foreground: scale to fit inside canvas maintaining aspect
            f"[fg]scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=decrease[fgout];"
            # Overlay centered
            "[bgout][fgout]overlay=(W-w)/2:(H-h)/2,setsar=1"
        )

    raise ValueError(f"unknown fit mode: {fit}")


def cut_clip(
    video: Path, start: float, end: float, out: Path,
    fit: str, src_w: int, src_h: int,
) -> None:
    vf = build_video_filter(fit, src_w, src_h)

    args = [
        "ffmpeg", "-y",
        "-ss", format_ts(start),
        "-to", format_ts(end),
        "-i", str(video),
    ]
    if vf:
        args += ["-vf", vf]
    # Loudness normalization — one-pass loudnorm keeps streams stable for
    # clips without requiring a first-pass measurement.
    args += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    args += [
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposals")
    parser.add_argument("video")
    parser.add_argument("outdir")
    parser.add_argument(
        "--fit", default="blur-pad", choices=sorted(FIT_MODES),
        help="How to fit the source frame into 9:16 (default: blur-pad)",
    )
    # Back-compat: `--no-vertical` == `--fit source`
    parser.add_argument("--no-vertical", action="store_true",
                        help="Deprecated alias for --fit source")
    args = parser.parse_args()

    fit = "source" if args.no_vertical else args.fit

    proposals = json.loads(Path(args.proposals).read_text())
    clips = proposals.get("clips", [])
    if not clips:
        raise SystemExit("cut_clips: no clips in proposals.json")

    video = Path(args.video)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    src_w, src_h = probe_dims(video)
    print(f"[cut_clips] source {src_w}x{src_h}, fit={fit}")

    for clip in clips:
        cid = clip["id"]
        start = float(clip["start"])
        end = float(clip["end"])
        out = outdir / f"{cid}.mp4"
        print(f"[cut_clips] {cid}: {start:.2f}s -> {end:.2f}s ({end-start:.1f}s)")
        cut_clip(video, start, end, out, fit, src_w, src_h)

    print(f"[cut_clips] wrote {len(clips)} clips to {outdir}")


if __name__ == "__main__":
    main()
