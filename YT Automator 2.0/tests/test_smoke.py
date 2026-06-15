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
