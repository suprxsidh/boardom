from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Coroutine, TypeVar

import edge_tts

_T = TypeVar("_T")


class TTSEngine:
    def __init__(self, voices: list[str]):
        if not voices:
            raise ValueError("TTSEngine requires at least one voice.")
        self.voices = voices

    async def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        selected_voice = voice or self.voices[0]
        try:
            communicate = edge_tts.Communicate(text, selected_voice, rate="+15%")
            await communicate.save(str(output_path))
            return output_path
        except Exception as exc:
            print(f"[WARN] edge-tts failed, using silent fallback: {exc}")
            try:
                self._create_silent_fallback(output_path)
            except Exception as fb_exc:
                raise RuntimeError(
                    f"Both edge-tts and ffmpeg silent fallback failed: {fb_exc}"
                ) from fb_exc
            return output_path

    @staticmethod
    def _create_silent_fallback(output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=mono",
                "-t", "6", "-q:a", "9", "-acodec", "libmp3lame",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine synchronously. Must not be called from inside a running event loop."""
    return asyncio.run(coro)
