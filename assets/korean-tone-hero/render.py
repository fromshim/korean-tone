#!/usr/bin/env python3
"""index.html을 README용 애니메이션 GIF로 렌더링한다."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent


def find_command(candidates: list[str]) -> str:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise SystemExit(f"필요한 명령을 찾지 못했어: {', '.join(candidates)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=188)
    parser.add_argument("--output", type=Path, default=HERE / "korean-tone.gif")
    parser.add_argument(
        "--static-output",
        type=Path,
        default=HERE / "korean-tone-static.png",
        help="움직임 줄이기 환경에서 쓸 최종 상태 PNG",
    )
    args = parser.parse_args()

    if args.fps <= 0 or args.duration <= 0:
        parser.error("fps와 duration은 0보다 커야 해")

    browser = find_command([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
    ])
    magick = find_command(["magick"])
    html = (HERE / "index.html").resolve()
    args.output = args.output.resolve()
    args.static_output = args.static_output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.static_output.parent.mkdir(parents=True, exist_ok=True)

    frame_count = round(args.duration * args.fps)
    with tempfile.TemporaryDirectory(prefix="korean-tone-hero-") as temp:
        frame_dir = Path(temp)
        frames = []
        for index in range(frame_count):
            frame = frame_dir / f"frame-{index:04d}.png"
            time = index / args.fps
            url = f"{html.as_uri()}?t={time:.3f}"
            subprocess.run([
                browser,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={args.width},{args.height}",
                f"--screenshot={frame}",
                url,
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            frames.append(str(frame))

        final_state_index = min(round(frame_count * 0.7), frame_count - 1)
        shutil.copy2(frames[final_state_index], args.static_output)

        delay = max(round(100 / args.fps), 1)
        subprocess.run([
            magick,
            "-delay",
            str(delay),
            "-loop",
            "0",
            *frames,
            "-layers",
            "Optimize",
            str(args.output),
        ], check=True)

    print(args.output)
    print(args.static_output)


if __name__ == "__main__":
    main()
