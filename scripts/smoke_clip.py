#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/smoke/clip.mp4")
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    insight = data["insights"][0]
    start_seconds = insight["start_ms"] / 1000
    duration_seconds = (insight["end_ms"] - insight["start_ms"]) / 1000
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-ss", str(start_seconds), "-i", str(args.source.resolve()),
        "-t", str(duration_seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", str(args.output.resolve()),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(args.output.resolve())],
        check=True, capture_output=True, text=True, timeout=30,
    )
    print(probe.stdout.strip())


if __name__ == "__main__":
    main()
