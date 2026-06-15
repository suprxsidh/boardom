from __future__ import annotations

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
    def _fmt_ts(value: float) -> str:
        value = max(0.0, value)
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = int(value % 60)
        centiseconds = int((value - int(value)) * 100)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
