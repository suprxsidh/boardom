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
