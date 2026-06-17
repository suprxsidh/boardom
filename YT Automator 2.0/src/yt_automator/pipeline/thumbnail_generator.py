from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_log = logging.getLogger(__name__)

_THUMB_W, _THUMB_H = 1280, 720
_FONT_SIZE = 120
_STROKE = 6
_MAX_TEXT_W = int(_THUMB_W * 0.90)


def _bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    homebrew = f"/opt/homebrew/bin/{name}"
    if Path(homebrew).exists():
        return homebrew
    return name


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/Library/Fonts/Impact.ttf",
        "/Windows/Fonts/impact.ttf",
        "Impact",
        "Impact.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    for face in ("Arial Black", "Arial Bold", "Arial", "Helvetica"):
        try:
            return ImageFont.truetype(face + ".ttf", size)
        except Exception:
            pass
    return ImageFont.load_default()


def _first_frame(video_path: Path, out_path: Path) -> bool:
    ffmpeg = _bin("ffmpeg")
    # Try scene-change frame first, fallback to 0.5s grab
    for cmd in [
        [ffmpeg, "-y", "-i", str(video_path), "-vf", "select=gt(scene\\,0.1)", "-vframes", "1", str(out_path)],
        [ffmpeg, "-y", "-ss", "0.5", "-i", str(video_path), "-vframes", "1", str(out_path)],
    ]:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_path.exists() and out_path.stat().st_size > 0:
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return False


def _wrap_text(text: str, font: ImageFont.ImageFont) -> list[str]:
    """Split text into lines that fit within _MAX_TEXT_W."""
    words = text.split()
    lines: list[str] = []
    current = ""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for word in words:
        candidate = (current + " " + word).strip()
        bbox = dummy.textbbox((0, 0), candidate, font=font, stroke_width=_STROKE)
        if bbox[2] - bbox[0] > _MAX_TEXT_W and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


class ThumbnailGenerator:
    def generate(self, video_path: Path, title: str, run_dir: Path) -> Path | None:
        try:
            return self._generate(video_path, title, run_dir)
        except Exception as exc:
            _log.warning("Thumbnail generation failed (non-fatal): %s", exc)
            return None

    def _generate(self, video_path: Path, title: str, run_dir: Path) -> Path:
        frame_path = run_dir / "_thumb_frame.jpg"
        thumb_path = run_dir / "thumbnail.jpg"

        if not _first_frame(video_path, frame_path):
            raise RuntimeError(f"Could not extract frame from {video_path}")

        img = Image.open(frame_path).convert("RGB")
        img = img.resize((_THUMB_W, _THUMB_H), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(radius=8))

        # Overlay title text (max 4 words)
        words = title.split()[:4]
        display = " ".join(words)

        font = _load_font(_FONT_SIZE)
        lines = _wrap_text(display, font)

        draw = ImageDraw.Draw(img)
        line_height = _FONT_SIZE + 10
        total_h = line_height * len(lines)
        y_start = _THUMB_H - total_h - 80  # bottom-third anchor

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=_STROKE)
            lw = bbox[2] - bbox[0]
            x = (_THUMB_W - lw) // 2 - bbox[0]
            draw.text(
                (x, y_start),
                line,
                font=font,
                fill=(255, 255, 255),
                stroke_width=_STROKE,
                stroke_fill=(10, 10, 10),
            )
            y_start += line_height

        img.save(str(thumb_path), "JPEG", quality=95)

        try:
            frame_path.unlink()
        except Exception:
            pass

        return thumb_path
