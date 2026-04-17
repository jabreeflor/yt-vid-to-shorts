#!/usr/bin/env python3
"""Download a YouTube video's mp4, auto-captions, and metadata into a workdir.

Usage:
    python fetch.py <url> <workdir>

Outputs in <workdir>:
    video.mp4        merged single-file video, <=1080p
    captions.vtt     auto-generated English captions with word-level timestamps
    meta.json        {id, title, duration, channel, url}
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def fetch_video(url: str, workdir: Path) -> Path:
    template = str(workdir / "video.%(ext)s")
    run([
        "yt-dlp",
        "-f", "bv[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", template,
        url,
    ])
    mp4 = workdir / "video.mp4"
    if mp4.exists():
        return mp4
    # Fallback: some containers end up as mkv/webm; remux to mp4
    for ext in ("mkv", "webm", "mov"):
        src = workdir / f"video.{ext}"
        if src.exists():
            run(["ffmpeg", "-y", "-i", str(src), "-c", "copy", str(mp4)])
            src.unlink()
            return mp4
    raise SystemExit("fetch: no video file produced")


def fetch_captions(url: str, workdir: Path) -> Path:
    run([
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--sub-format", "vtt",
        "--sub-langs", "en.*,en",
        "-o", str(workdir / "captions.%(ext)s"),
        url,
    ])
    # yt-dlp names subs as captions.<lang>.vtt — pick the first English one
    candidates = sorted(workdir.glob("captions*.vtt"))
    if not candidates:
        raise SystemExit(
            "fetch: no auto-captions available for this video. "
            "This skill requires YouTube auto-captions."
        )
    target = workdir / "captions.vtt"
    chosen = candidates[0]
    if chosen != target:
        shutil.move(str(chosen), str(target))
    for extra in candidates[1:]:
        if extra != target:
            extra.unlink(missing_ok=True)
    return target


def fetch_meta(url: str, workdir: Path) -> Path:
    result = run(
        ["yt-dlp", "--skip-download", "--print-json", url],
        capture_output=True, text=True,
    )
    raw = json.loads(result.stdout.strip().splitlines()[0])
    meta = {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "duration": raw.get("duration"),
        "channel": raw.get("channel") or raw.get("uploader"),
        "url": raw.get("webpage_url", url),
        "thumbnail": raw.get("thumbnail"),
    }
    target = workdir / "meta.json"
    target.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return target


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    url = sys.argv[1]
    workdir = Path(sys.argv[2]).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"[fetch] workdir: {workdir}")
    meta = fetch_meta(url, workdir)
    print(f"[fetch] meta: {meta}")
    video = fetch_video(url, workdir)
    print(f"[fetch] video: {video}")
    caps = fetch_captions(url, workdir)
    print(f"[fetch] captions: {caps}")


if __name__ == "__main__":
    main()
