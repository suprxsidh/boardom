import pytest

from yt_automator.utils.text import slugify, word_count, normalize_script
from yt_automator.utils.time_utils import generate_publish_schedule


def test_slugify_basic():
    assert slugify("Deep Ocean Life!") == "deep-ocean-life"


def test_slugify_empty():
    assert slugify("") == "item"


def test_word_count():
    assert word_count("Hello world this is five") == 5


def test_normalize_script_removes_asterisks():
    assert normalize_script("**bold** text") == "bold text"


def test_normalize_script_collapses_whitespace():
    assert normalize_script("too   many   spaces") == "too many spaces"


def test_generate_publish_schedule_raises_on_empty_slots():
    with pytest.raises(ValueError, match="daily_slots cannot be empty"):
        generate_publish_schedule([], "Asia/Kolkata", 1)


import tempfile
from pathlib import Path
from yt_automator.optimizer.bandit_optimizer import BanditOptimizer
from yt_automator.pipeline.qa import QualityGate
from yt_automator.models import ContentPackage


def test_bandit_picks_arm_from_list():
    with tempfile.TemporaryDirectory() as tmp:
        opt = BanditOptimizer(Path(tmp) / "state.json")
        arms = ["a", "b", "c"]
        result = opt.pick_arm("biology", arms, epsilon=1.0)
        assert result in arms


def test_bandit_record_reward_updates_state():
    with tempfile.TemporaryDirectory() as tmp:
        opt = BanditOptimizer(Path(tmp) / "state.json")
        opt.record_reward("biology", "deep_ocean", 0.8)
        assert opt.state["biology"]["deep_ocean"]["pulls"] == 1
        assert opt.state["biology"]["deep_ocean"]["reward_sum"] == 0.8


def test_qa_gate_passes_valid_package():
    gate = QualityGate()
    pkg = ContentPackage(
        topic="Test",
        script=" ".join(["word"] * 100),
        title="A Valid Title",
        description="desc",
        video_query="query",
        tags=["tag1"],
    )
    valid, issues = gate.validate_content(pkg)
    assert valid
    assert issues == []


def test_qa_gate_fails_short_script():
    gate = QualityGate()
    pkg = ContentPackage(
        topic="Test",
        script="Too short",
        title="Title",
        description="desc",
        video_query="query",
        tags=["tag"],
    )
    valid, issues = gate.validate_content(pkg)
    assert not valid
    assert any("short" in i for i in issues)


import json as _json
from datetime import datetime, timezone
from yt_automator.pipeline.run_logger import RunLogger
from yt_automator.models import (
    ContentPackage, MediaAsset, RenderResult, UploadResult, PublishRecord
)


def test_run_logger_writes_jsonl_with_all_fields():
    with tempfile.TemporaryDirectory() as tmp:
        logger = RunLogger(Path(tmp) / "runs")
        pkg = ContentPackage(
            topic="Test topic",
            script="A test script here",
            title="Test title",
            description="desc",
            video_query="nature",
            tags=["tag1"],
        )
        render = RenderResult(
            video_path=Path(tmp) / "final.mp4",
            audio_path=Path(tmp) / "voice.mp3",
            subtitle_path=Path(tmp) / "subs.ass",
            duration_seconds=30.0,
        )
        upload = UploadResult(success=True, video_url="https://yt.be/abc", video_id="abc")
        record = PublishRecord(
            channel="biology",
            package=pkg,
            render_result=render,
            upload_result=upload,
            scheduled_publish_at=None,
            created_at=datetime.now(timezone.utc),
        )
        out = logger.log_publish_record(record)
        lines = out.read_text().strip().splitlines()
        assert len(lines) == 1
        data = _json.loads(lines[0])
        assert data["channel"] == "biology"
        assert data["script"] == "A test script here"
        assert data["video_query"] == "nature"
        assert "audio_path" in data
        assert "subtitle_path" in data
        assert data["upload_success"] is True


from yt_automator.providers.wikimedia_provider import WikimediaProvider


def test_wikimedia_allows_cc0():
    assert WikimediaProvider._is_license_allowed("CC0") is True


def test_wikimedia_allows_cc_by():
    assert WikimediaProvider._is_license_allowed("CC BY 4.0") is True


def test_wikimedia_blocks_all_rights_reserved():
    assert WikimediaProvider._is_license_allowed("All Rights Reserved") is False


def test_wikimedia_blocks_unknown():
    assert WikimediaProvider._is_license_allowed("Unknown") is False


def test_wikimedia_blocks_cc_by_nd():
    assert WikimediaProvider._is_license_allowed("CC BY-ND 4.0") is False


def test_wikimedia_blocks_cc_by_nc():
    assert WikimediaProvider._is_license_allowed("CC BY-NC 4.0") is False


# --- Task 6: subtitle format ---
from yt_automator.pipeline.subtitles import SubtitleEngine


def test_write_ass_produces_valid_file():
    engine = SubtitleEngine()
    segments = [
        {"words": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "World", "start": 0.5, "end": 1.0},
        ]}
    ]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "subs.ass"
        engine.write_ass(segments, out)
        content = out.read_text()
    assert "[Script Info]" in content
    # Style line fields (0-indexed): 18=Alignment
    style_line = [l for l in content.splitlines() if l.startswith("Style:")][0]
    fields = style_line.split(",")
    assert fields[18] == "2", f"Expected Alignment=2 (bottom-center), got {fields[18]}"
    assert "HELLO" in content
    assert "WORLD" in content


# --- Task 6: TTS engine ---
from yt_automator.pipeline.tts_engine import TTSEngine


def test_tts_engine_rejects_empty_voices():
    import pytest
    with pytest.raises(ValueError, match="at least one voice"):
        TTSEngine(voices=[])


def test_write_ass_empty_segments_writes_header_only():
    engine = SubtitleEngine()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "empty.ass"
        engine.write_ass([], out)
        content = out.read_text()
    assert "[Script Info]" in content
    assert "Dialogue:" not in content
