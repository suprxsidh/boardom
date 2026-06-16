from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from yt_automator.models import MediaAsset, RenderResult

_log = logging.getLogger(__name__)


class VideoRenderer:
    def __init__(self, shorts_size: tuple[int, int] = (1080, 1920), fps: int = 24):
        self.shorts_size = shorts_size
        self.fps = fps

    def render(
        self,
        assets: list[MediaAsset],
        voice_audio_path: Path,
        subtitle_path: Path,
        music_path: Path,
        output_path: Path,
    ) -> RenderResult:
        if not assets:
            raise RuntimeError("No media assets provided to renderer")

        primary = assets[0].local_path
        duration = self._probe_duration(voice_audio_path)
        frame_count = max(int(duration * self.fps), 24)

        w, h = self.shorts_size
        filter_chain = (
            "scale=8000:-1,"
            f"zoompan=z='min(zoom+0.00055,1.12)':d={frame_count}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={self.fps},"
            + self._escape_filter_path(subtitle_path)
        )

        command = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(primary),
            "-i", str(voice_audio_path),
            "-i", str(music_path),
            "-filter_complex",
            f"[0:v]{filter_chain}[v];[2:a]volume=0.08[bgm];[1:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-t", f"{duration:.2f}",
            str(output_path),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")
            if "No such filter" in stderr or "filter 'ass'" in stderr or "ass filter" in stderr:
                _log.warning("ffmpeg ass filter unavailable, retrying without subtitles")
                self._render_without_subtitles(
                    primary, voice_audio_path, music_path, duration, output_path
                )
            else:
                raise RuntimeError(f"ffmpeg render failed: {stderr}") from exc

        return RenderResult(
            video_path=output_path,
            audio_path=voice_audio_path,
            subtitle_path=subtitle_path,
            duration_seconds=duration,
        )

    def _render_without_subtitles(
        self,
        primary: Path,
        voice_audio_path: Path,
        music_path: Path,
        duration: float,
        output_path: Path,
    ) -> None:
        command = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(primary),
            "-i", str(voice_audio_path),
            "-i", str(music_path),
            "-filter_complex",
            "[0:v]scale=1080:1920,format=yuv420p[v];[2:a]volume=0.08[bgm];[1:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-t", f"{duration:.2f}",
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as inner_exc:
            inner_stderr = inner_exc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ffmpeg fallback render failed: {inner_stderr}"
            ) from inner_exc

    @staticmethod
    def _escape_filter_path(path: Path) -> str:
        s = path.as_posix()
        for ch in ("\\", "'", ":", " "):
            s = s.replace(ch, "\\" + ch)
        return f"ass=filename={s}"

    @staticmethod
    def _probe_duration(audio_path: Path) -> float:
        command = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            output = subprocess.check_output(command).decode("utf-8").strip()
            return max(float(output), 3.0)
        except (subprocess.CalledProcessError, ValueError) as exc:
            _log.warning("ffprobe failed (%s), defaulting to 6.0s — output may be truncated", exc)
            return 6.0
        except FileNotFoundError as exc:
            raise RuntimeError("ffprobe not found — install ffmpeg to use the video renderer") from exc
