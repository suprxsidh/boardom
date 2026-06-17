from __future__ import annotations

import difflib
import re
from pathlib import Path


class SubtitleEngine:
    def __init__(self, model_name: str = "tiny.en"):
        self.model_name = model_name
        self._model = None

    def transcribe_segments(self, audio_path: Path) -> list[dict]:
        try:
            if self._model is None:
                import whisper
                self._model = whisper.load_model(self.model_name)
            result = self._model.transcribe(str(audio_path), word_timestamps=True)
            return result.get("segments", [])
        except Exception as exc:
            print(f"[WARN] Whisper failed, returning empty segments: {exc}")
            return []

    def write_ass(self, segments: list[dict], output_path: Path) -> Path:
        # Alignment=2: bottom-center. MarginV=120: 120px from bottom edge of 1920px frame.
        content = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,96,&H00FFFFFF,&H00000000,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,7,0,2,20,20,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for segment in segments:
            for word in segment.get("words", []):
                start = self._fmt_ts(float(word["start"]))
                end = self._fmt_ts(float(word["end"]))
                text = str(word["word"]).upper().strip()
                animated = "{\\fscx82\\fscy82\\t(0,180,\\fscx100\\fscy100)}" + text
                content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{animated}\n"

        output_path.write_text(content, encoding="utf-8")
        return output_path

    @staticmethod
    def correct_against_script(segments: list[dict], original_script: str) -> list[dict]:
        """Align Whisper word texts against the original script to fix mis-hearings.

        Keeps Whisper timing intact; replaces wrong/cased words with the original
        script's tokens wherever SequenceMatcher finds a match or same-length swap.
        """
        flat: list[dict] = [w for seg in segments for w in seg.get("words", [])]
        if not flat:
            return segments

        def alpha(s: str) -> str:
            return re.sub(r"[^a-z'-]", "", s.lower())

        orig_tokens: list[str] = re.findall(r"[A-Za-z'-]+", original_script)
        w_keys = [alpha(w.get("word", "")) for w in flat]
        o_keys = [alpha(t) for t in orig_tokens]

        matcher = difflib.SequenceMatcher(None, w_keys, o_keys, autojunk=False)
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    flat[i]["word"] = orig_tokens[j]   # fix casing / punctuation
            elif op == "replace" and (i2 - i1) == (j2 - j1):
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    flat[i]["word"] = orig_tokens[j]   # fix mis-heard word
        return segments

    @classmethod
    def build_drawtext_filter(cls, segments: list[dict]) -> str:
        """Build an ffmpeg drawtext filter chain for word-by-word subtitles.

        Uses only libfreetype (always available in Homebrew ffmpeg) — no libass needed.
        """
        parts: list[str] = []
        for segment in segments:
            for word in segment.get("words", []):
                start = float(word["start"])
                end = float(word["end"])
                raw = str(word["word"]).upper().strip()
                if not raw:
                    continue
                text = cls._escape_drawtext(raw)
                dt = (
                    f"drawtext="
                    f"text='{text}'"
                    f":fontsize=96"
                    f":x=(w-tw)/2"
                    f":y=h-th-120"
                    f":fontcolor=white"
                    f":borderw=6"
                    f":bordercolor=0x101010@FF"
                    f":bold=1"
                    f":enable='between(t,{start:.3f},{end:.3f})'"
                )
                parts.append(dt)
        return ",".join(parts) if parts else "null"

    @staticmethod
    def _escape_drawtext(text: str) -> str:
        """Escape special chars for ffmpeg drawtext option values."""
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "’")   # replace apostrophe with curly quote
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text

    @staticmethod
    def _fmt_ts(value: float) -> str:
        value = max(0.0, value)
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = int(value % 60)
        centiseconds = int((value - int(value)) * 100)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
