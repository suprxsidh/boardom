from __future__ import annotations

import logging
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from yt_automator.models import MediaAsset, RenderResult

_log = logging.getLogger(__name__)

_FONT_SIZE = 110
_STROKE = 5
_W, _H = 1080, 1920
_POP_IN_DURATION = 0.2   # seconds — matches reference pop_in_effect


def _bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    homebrew = f"/opt/homebrew/bin/{name}"
    if Path(homebrew).exists():
        return homebrew
    return name


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Impact first — matches reference exactly
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
    # Fallback chain for non-macOS
    for face in ("Arial Black", "Arial Bold", "Arial", "Helvetica"):
        try:
            return ImageFont.truetype(face + ".ttf", size)
        except Exception:
            pass
    return ImageFont.load_default()


def _render_word_image(text: str, font: ImageFont.ImageFont) -> Image.Image:
    """Pre-render a word onto a transparent RGBA canvas (reused for pop-in scaling)."""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font, stroke_width=_STROKE)
    tw = bbox[2] - bbox[0] + _STROKE * 2 + 4
    th = bbox[3] - bbox[1] + _STROKE * 2 + 4
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (_STROKE + 2 - bbox[0], _STROKE + 2 - bbox[1]),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=_STROKE,
        stroke_fill=(10, 10, 10, 255),
    )
    return canvas


_MAX_WORD_W = int(_W * 0.88)   # never wider than 88% of frame


def _composite_word(frame: Image.Image, word_img: Image.Image, scale: float) -> None:
    """Composite a (possibly scaled) word image centered on the frame."""
    if scale != 1.0:
        nw = max(1, int(word_img.width * scale))
        nh = max(1, int(word_img.height * scale))
        word_img = word_img.resize((nw, nh), Image.LANCZOS)
    # Auto-shrink long words so they never overflow the frame
    if word_img.width > _MAX_WORD_W:
        ratio = _MAX_WORD_W / word_img.width
        word_img = word_img.resize(
            (max(1, int(word_img.width * ratio)), max(1, int(word_img.height * ratio))),
            Image.LANCZOS,
        )
    x = (_W - word_img.width) // 2
    y = int(_H * 0.68) - word_img.height // 2   # bottom third — avoids covering subject
    frame.paste(word_img, (x, y), word_img)


class VideoRenderer:
    def __init__(self, shorts_size: tuple[int, int] = (_W, _H), fps: int = 24):
        self.shorts_size = shorts_size
        self.fps = fps
        self._font: ImageFont.ImageFont | None = None
        self._word_cache: dict[str, Image.Image] = {}
        # Randomised per-video to break identical-footage pattern
        self._saturation: float = round(random.uniform(1.1, 1.4), 2)

    @property
    def font(self) -> ImageFont.ImageFont:
        if self._font is None:
            self._font = _load_font(_FONT_SIZE)
        return self._font

    def _word_img(self, text: str) -> Image.Image:
        if text not in self._word_cache:
            self._word_cache[text] = _render_word_image(text, self.font)
        return self._word_cache[text]

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def render(
        self,
        assets: list[MediaAsset],
        voice_audio_path: Path,
        subtitle_path: Path,
        music_path: Path,
        output_path: Path,
        drawtext_filter: str = "null",
    ) -> RenderResult:
        if not assets:
            raise RuntimeError("No media assets provided to renderer")

        duration = self._probe_duration(voice_audio_path)
        subtitle_index = self._load_subtitle_index(subtitle_path)

        video_assets = [a for a in assets if a.media_type == "video"]
        image_assets = [a for a in assets if a.media_type == "image"]

        if video_assets:
            self._render_video_clips(
                [a.local_path for a in video_assets],
                voice_audio_path, music_path,
                output_path, duration, subtitle_index,
            )
        else:
            self._render_image_bg(
                image_assets[0].local_path,
                voice_audio_path, music_path,
                output_path, duration, subtitle_index,
            )

        return RenderResult(
            video_path=output_path,
            audio_path=voice_audio_path,
            subtitle_path=subtitle_path,
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------ #
    #  Video-clip path  (Pexels — 3 clips stitched equally)
    # ------------------------------------------------------------------ #

    def _render_video_clips(
        self,
        clip_paths: list[Path],
        voice_audio_path: Path,
        music_path: Path,
        output_path: Path,
        duration: float,
        subtitle_index: list[tuple[float, float, str]],
    ) -> None:
        w, h = self.shorts_size
        fps = self.fps
        total_frames = max(int(duration * fps), 24)
        num_clips = len(clip_paths)
        clip_duration = duration / num_clips          # equal split — matches reference

        # Decode frames from each clip in sequence
        def frames_from_clip(path: Path, n_frames: int):
            cmd = [
                _bin("ffmpeg"),
                "-stream_loop", "-1", "-i", str(path),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},eq=saturation={self._saturation:.2f}",
                "-r", str(fps),
                "-vframes", str(n_frames),
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "pipe:1",
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            frame_size = w * h * 3
            yielded = 0
            while yielded < n_frames:
                raw = proc.stdout.read(frame_size)
                if len(raw) < frame_size:
                    break
                yield raw
                yielded += 1
            proc.stdout.close()
            proc.wait()

        encode_cmd = [
            _bin("ffmpeg"), "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps),
            "-i", "pipe:0",
            "-i", str(voice_audio_path),
            "-i", str(music_path),
            "-filter_complex",
            "[2:a]volume=0.15[bgm_raw];[bgm_raw][1:a]sidechaincompress=threshold=0.02:ratio=4:attack=100:release=600:knee=6[bgm_ducked];[1:a][bgm_ducked]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "libx264", "-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-t", f"{duration:.2f}",
            str(output_path),
        ]
        encode_proc = subprocess.Popen(
            encode_cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )

        try:
            global_frame = 0
            for clip_idx, clip_path in enumerate(clip_paths):
                clip_start_t = clip_idx * clip_duration
                frames_for_clip = int(clip_duration * fps)
                if clip_idx == num_clips - 1:
                    frames_for_clip = total_frames - global_frame  # absorb rounding

                for raw in frames_from_clip(clip_path, frames_for_clip):
                    t = clip_start_t + (global_frame - clip_idx * int(clip_duration * fps)) / fps
                    frame = Image.frombytes("RGB", (w, h), raw)
                    self._overlay_subtitle(frame, subtitle_index, t)
                    encode_proc.stdin.write(frame.tobytes())
                    global_frame += 1
        finally:
            encode_proc.stdin.close()
            encode_proc.wait()

        if encode_proc.returncode != 0:
            err = encode_proc.stderr.read().decode("utf-8", errors="replace") if encode_proc.stderr else ""
            raise RuntimeError(f"ffmpeg encode failed:\n{err}")

    # ------------------------------------------------------------------ #
    #  Image-bg path  (Ken Burns fallback when no video clips)
    # ------------------------------------------------------------------ #

    def _render_image_bg(
        self,
        image_path: Path,
        voice_audio_path: Path,
        music_path: Path,
        output_path: Path,
        duration: float,
        subtitle_index: list[tuple[float, float, str]],
    ) -> None:
        w, h = self.shorts_size
        fps = self.fps
        total_frames = max(int(duration * fps), 24)

        img = Image.open(image_path).convert("RGB")
        scale = max(w * 1.15 / img.width, h * 1.15 / img.height)
        if scale > 1:
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

        encode_cmd = [
            _bin("ffmpeg"), "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps),
            "-i", "pipe:0",
            "-i", str(voice_audio_path),
            "-i", str(music_path),
            "-filter_complex",
            "[2:a]volume=0.15[bgm_raw];[bgm_raw][1:a]sidechaincompress=threshold=0.02:ratio=4:attack=100:release=600:knee=6[bgm_ducked];[1:a][bgm_ducked]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "libx264", "-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-t", f"{duration:.2f}",
            str(output_path),
        ]
        proc = subprocess.Popen(
            encode_cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            for i in range(total_frames):
                t = i / fps
                zoom = min(1.0 + 0.00055 * i, 1.12)
                sw, sh = int(img.width / zoom), int(img.height / zoom)
                cx, cy = (img.width - sw) // 2, (img.height - sh) // 2
                frame = img.crop((cx, cy, cx + sw, cy + sh)).resize((w, h), Image.LANCZOS)
                self._overlay_subtitle(frame, subtitle_index, t)
                proc.stdin.write(frame.tobytes())
        finally:
            proc.stdin.close()
            proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            raise RuntimeError(f"ffmpeg image-bg encode failed:\n{err}")

    # ------------------------------------------------------------------ #
    #  Subtitle overlay — Impact, center, pop-in scale 0.8→1.0 in 0.2s
    # ------------------------------------------------------------------ #

    def _overlay_subtitle(
        self,
        frame: Image.Image,
        index: list[tuple[float, float, str]],
        t: float,
    ) -> None:
        for start, end, text in index:
            if start <= t < end:
                word_img = self._word_img(text)
                elapsed = t - start
                if elapsed < _POP_IN_DURATION:
                    scale = 0.8 + 0.2 * (elapsed / _POP_IN_DURATION)
                else:
                    scale = 1.0
                _composite_word(frame, word_img, scale)
                break

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_subtitle_index(subtitle_path: Path) -> list[tuple[float, float, str]]:
        import re
        index: list[tuple[float, float, str]] = []
        if not subtitle_path.exists():
            return index
        ts_re = re.compile(r"(\d+):(\d{2}):(\d{2})\.(\d{2})")

        def parse_ts(s: str) -> float:
            m = ts_re.match(s.strip())
            if not m:
                return 0.0
            h, mi, sec, cs = (int(x) for x in m.groups())
            return h * 3600 + mi * 60 + sec + cs / 100

        text_re = re.compile(r"\{[^}]*\}")
        for line in subtitle_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("Dialogue:"):
                continue
            parts = line.split(",", 9)
            if len(parts) < 10:
                continue
            raw = text_re.sub("", parts[9]).strip()
            if raw:
                index.append((parse_ts(parts[1]), parse_ts(parts[2]), raw))
        return index

    @staticmethod
    def _probe_duration(audio_path: Path) -> float:
        cmd = [
            _bin("ffprobe"), "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            return max(float(subprocess.check_output(cmd).decode().strip()), 3.0)
        except (subprocess.CalledProcessError, ValueError) as exc:
            _log.warning("ffprobe failed (%s), defaulting to 6.0s", exc)
            return 6.0
        except FileNotFoundError as exc:
            raise RuntimeError("ffprobe not found — install ffmpeg") from exc
