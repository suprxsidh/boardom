from __future__ import annotations

import asyncio
import random
import re
import subprocess
from functools import reduce
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
            communicate = edge_tts.Communicate(text, selected_voice, rate="+30%")
            await communicate.save(str(output_path))
            self._apply_prosody_variation(output_path, text)
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

    def _apply_prosody_variation(self, output_path: Path, text: str) -> None:
        try:
            try:
                from pydub import AudioSegment
                from pydub.silence import split_on_silence
            except ImportError:
                return

            audio = AudioSegment.from_mp3(str(output_path))

            chunks = split_on_silence(
                audio,
                min_silence_len=300,
                silence_thresh=-40,
                keep_silence=150,
            )

            if len(chunks) <= 1:
                return

            sentences = re.split(r"[.?!]", text)
            has_emphasis = [
                any(w.isupper() and len(w) >= 2 for w in sentence.split())
                for sentence in sentences
            ]

            processed: list[AudioSegment] = []
            for i, chunk in enumerate(chunks):
                if i < len(has_emphasis) and has_emphasis[i]:
                    speed = random.uniform(1.03, 1.06)
                else:
                    speed = random.uniform(0.97, 1.03)
                try:
                    chunk = chunk.speedup(playback_speed=speed, chunk_size=150, crossfade=25)
                except Exception:
                    pass
                processed.append(chunk)

            result = reduce(lambda a, b: a + b, processed)
            result.export(str(output_path), format="mp3", bitrate="192k")

        except Exception as exc:
            print(f"[WARN] prosody variation failed, keeping original audio: {exc}")

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
