# YT Automator 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port youtube-automator v2 into `YT Automator 2.0/`, fix 4 bugs, upgrade to `google-genai` SDK, and wire up biology/physics/history channels with evening IST slots.

**Architecture:** Single Python package (`yt_automator`) with a `yta` CLI entry point. One pipeline per video: content generation (Gemini) → TTS (edge-tts) → subtitles (Whisper) → media fetch (Pixabay/Wikimedia/NASA) → render (ffmpeg) → upload (YouTube Data API v3). An epsilon-greedy bandit picks the content strategy for each video.

**Tech Stack:** Python 3.10+, `google-genai`, `edge-tts`, `openai-whisper`, `ffmpeg` (system), `Pillow`, `google-api-python-client`, `schedule`, `pytz`, `python-dotenv`

**Repo root:** `YT Automator 2.0/` — all paths in this plan are relative to it.

---

## File Map

| File | Responsibility |
|------|---------------|
| `.yta-root` | Sentinel for repo-root detection |
| `pyproject.toml` | Package metadata + dependencies |
| `.gitignore` | Exclude secrets, outputs, .env |
| `src/yt_automator/__init__.py` | Package version |
| `src/yt_automator/models.py` | Dataclasses: ContentPackage, MediaAsset, RenderResult, UploadResult, PublishRecord |
| `src/yt_automator/utils/paths.py` | `get_repo_root()` using sentinel file |
| `src/yt_automator/utils/text.py` | slugify, word_count, normalize_script, sentence_split |
| `src/yt_automator/utils/time_utils.py` | `generate_publish_schedule()` |
| `src/yt_automator/config.py` | `ConfigLoader` — loads/validates channel + app JSON |
| `src/yt_automator/secrets.py` | `SecretManager` — wraps dotenv + os.getenv |
| `src/yt_automator/optimizer/bandit_optimizer.py` | Epsilon-greedy bandit |
| `src/yt_automator/pipeline/qa.py` | Word-count + title-length gate |
| `src/yt_automator/pipeline/run_logger.py` | JSONL publish log |
| `src/yt_automator/providers/base.py` | `MediaProvider` ABC |
| `src/yt_automator/providers/pixabay_provider.py` | Pixabay image search + download |
| `src/yt_automator/providers/wikimedia_provider.py` | Wikimedia Commons image search + download |
| `src/yt_automator/providers/nasa_provider.py` | NASA image search + download |
| `src/yt_automator/pipeline/tts_engine.py` | edge-tts voice synthesis |
| `src/yt_automator/pipeline/subtitles.py` | Whisper transcription → .ass file (fixed alignment) |
| `src/yt_automator/pipeline/media_sourcer.py` | Fanout to providers + fallback image |
| `src/yt_automator/pipeline/content_generator.py` | Gemini content generation (google-genai SDK) |
| `src/yt_automator/pipeline/video_renderer.py` | ffmpeg: image + voice + music + subs → mp4 |
| `src/yt_automator/pipeline/youtube_client.py` | YouTube Data API v3 OAuth2 upload |
| `src/yt_automator/pipeline/orchestrator.py` | Full pipeline orchestration |
| `src/yt_automator/cli.py` | argparse CLI entry point |
| `config/app_settings.json` | Voices, subtitle model, Ollama settings |
| `config/media_sources.json` | Provider enable flags |
| `config/channels/biology.json` | Biology channel config |
| `config/channels/physics.json` | Physics channel config |
| `config/channels/history.json` | History channel config |
| `Makefile` | Convenience commands |
| `.env.example` | Documented key template |
| `SETUP.md` | Step-by-step user guide |
| `tests/test_smoke.py` | Channel list, bandit, QA gate, text utils |

---

## Task 1: Scaffold — package structure, pyproject.toml, .gitignore

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.yta-root`
- Create: `src/yt_automator/__init__.py`
- Create: `src/yt_automator/pipeline/__init__.py`
- Create: `src/yt_automator/providers/__init__.py`
- Create: `src/yt_automator/optimizer/__init__.py`
- Create: `src/yt_automator/utils/__init__.py`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p src/yt_automator/{pipeline,providers,optimizer,utils}
mkdir -p config/channels
mkdir -p assets/music
mkdir -p secrets/youtube
mkdir -p data/{history,runs,optimizer}
mkdir -p outputs
mkdir -p tests
touch src/yt_automator/__init__.py
touch src/yt_automator/pipeline/__init__.py
touch src/yt_automator/providers/__init__.py
touch src/yt_automator/optimizer/__init__.py
touch src/yt_automator/utils/__init__.py
touch tests/__init__.py
touch .yta-root
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "youtube-automator-v2"
version = "0.1.0"
description = "Automated YouTube Shorts pipeline"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31.0",
    "google-genai>=1.0.0",
    "edge-tts>=6.1.15",
    "openai-whisper>=20240930",
    "pillow>=10.0.0",
    "python-dotenv>=1.0.1",
    "google-auth-oauthlib>=1.2.0",
    "google-api-python-client>=2.160.0",
    "google-api-core>=2.24.1",
    "schedule>=1.2.2",
    "pytz>=2024.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.1",
]

[project.scripts]
yta = "yt_automator.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 3: Write .gitignore**

```gitignore
# secrets and credentials
secrets/
.env

# generated outputs
outputs/
assets/music/

# runtime data
data/runs/
data/optimizer/

# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
build/
.pytest_cache/

# macOS
.DS_Store
```

- [ ] **Step 4: Write src/yt_automator/__init__.py**

```python
"""YouTube automator v2 package."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 5: Install package in dev mode**

```bash
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

Expected: no errors, `yta` command available at `.venv/bin/yta`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .yta-root src/ tests/ config/ assets/ secrets/ data/ outputs/ Makefile
git commit -m "feat: scaffold package structure and dependencies"
```

---

## Task 2: Data model layer — models, utils

**Files:**
- Create: `src/yt_automator/models.py`
- Create: `src/yt_automator/utils/paths.py`
- Create: `src/yt_automator/utils/text.py`
- Create: `src/yt_automator/utils/time_utils.py`
- Test: `tests/test_smoke.py` (partial)

- [ ] **Step 1: Write models.py**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ContentPackage:
    topic: str
    script: str
    title: str
    description: str
    video_query: str
    tags: list[str]
    source_links: list[str] = field(default_factory=list)
    style_variant: str = "default"


@dataclass(slots=True)
class MediaAsset:
    provider: str
    local_path: Path
    source_url: str
    license_name: str
    attribution_required: bool


@dataclass(slots=True)
class RenderResult:
    video_path: Path
    audio_path: Path
    subtitle_path: Path
    duration_seconds: float


@dataclass(slots=True)
class UploadResult:
    success: bool
    video_url: str | None
    video_id: str | None
    error: str | None = None


@dataclass(slots=True)
class PublishRecord:
    channel: str
    package: ContentPackage
    render_result: RenderResult
    upload_result: UploadResult
    scheduled_publish_at: str | None
    created_at: datetime
```

- [ ] **Step 2: Write utils/paths.py (sentinel-based root detection)**

```python
from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / ".yta-root").exists():
            return candidate
    raise RuntimeError(
        "Could not find .yta-root sentinel. "
        "Run from inside the YT Automator 2.0 directory."
    )


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: Write utils/text.py**

```python
from __future__ import annotations

import re


def normalize_script(text: str) -> str:
    cleaned = text.replace("*", "").replace('"', "").strip()
    return re.sub(r"\s+", " ", cleaned)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def slugify(value: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return base.lower() or "item"
```

- [ ] **Step 4: Write utils/time_utils.py**

```python
from __future__ import annotations

from datetime import datetime, timedelta

import pytz


def generate_publish_schedule(
    daily_slots: list[str],
    timezone_name: str,
    count: int,
) -> list[str]:
    timezone = pytz.timezone(timezone_name)
    now_local = datetime.now(timezone)

    candidates: list[datetime] = []
    day_offset = 0
    while len(candidates) < count:
        base_day = now_local.date() + timedelta(days=day_offset)
        for slot in daily_slots:
            hour, minute = (int(p) for p in slot.split(":"))
            dt = timezone.localize(
                datetime(base_day.year, base_day.month, base_day.day, hour, minute)
            )
            if dt > now_local:
                candidates.append(dt)
                if len(candidates) == count:
                    break
        day_offset += 1

    return [
        dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for dt in candidates
    ]
```

- [ ] **Step 5: Write initial test for text utils**

```python
# tests/test_smoke.py
from yt_automator.utils.text import slugify, word_count, normalize_script


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
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: 5 tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/yt_automator/models.py src/yt_automator/utils/ tests/test_smoke.py
git commit -m "feat: add data models and utility functions"
```

---

## Task 3: Config loader and SecretManager

**Files:**
- Create: `src/yt_automator/config.py`
- Create: `src/yt_automator/secrets.py`

- [ ] **Step 1: Write config.py**

```python
from __future__ import annotations

import json
from pathlib import Path


class ConfigError(RuntimeError):
    pass


class ConfigLoader:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.channels_dir = repo_root / "config" / "channels"

    def list_channels(self) -> list[str]:
        if not self.channels_dir.exists():
            return []
        return sorted(path.stem for path in self.channels_dir.glob("*.json"))

    def load_channel(self, channel_name: str) -> dict:
        path = self.channels_dir / f"{channel_name}.json"
        if not path.exists():
            raise ConfigError(f"Missing channel config: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
        self._validate_channel_config(channel_name, data)
        return data

    def load_media_sources(self) -> dict:
        path = self.repo_root / "config" / "media_sources.json"
        if not path.exists():
            raise ConfigError(f"Missing media sources config: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_app_settings(self) -> dict:
        path = self.repo_root / "config" / "app_settings.json"
        if not path.exists():
            raise ConfigError(f"Missing app settings config: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _validate_channel_config(self, channel_name: str, config: dict) -> None:
        required = [
            "channel_name", "youtube", "content_strategies",
            "prompt_profile", "paths", "rl_profile",
        ]
        missing = [key for key in required if key not in config]
        if missing:
            raise ConfigError(
                f"Channel config {channel_name} missing keys: {', '.join(missing)}"
            )
```

- [ ] **Step 2: Write secrets.py**

```python
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class SecretError(RuntimeError):
    pass


class SecretManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        env_file = repo_root / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)

    def get(self, key: str, default: str | None = None) -> str | None:
        return os.getenv(key, default)

    def require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise SecretError(
                f"Missing required env var: {key}. Set it in .env or your shell."
            )
        return value
```

- [ ] **Step 3: Commit**

```bash
git add src/yt_automator/config.py src/yt_automator/secrets.py
git commit -m "feat: add config loader and secret manager"
```

---

## Task 4: Optimizer, QA gate, Run logger

**Files:**
- Create: `src/yt_automator/optimizer/bandit_optimizer.py`
- Create: `src/yt_automator/pipeline/qa.py`
- Create: `src/yt_automator/pipeline/run_logger.py`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write bandit_optimizer.py**

```python
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ArmStat:
    pulls: int
    reward_sum: float

    @property
    def average_reward(self) -> float:
        if self.pulls == 0:
            return 0.0
        return self.reward_sum / self.pulls


class BanditOptimizer:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def pick_arm(self, channel: str, candidate_arms: list[str], epsilon: float) -> str:
        if not candidate_arms:
            raise ValueError("No candidate arms available")
        bucket = self.state.setdefault(channel, {})
        for arm in candidate_arms:
            bucket.setdefault(arm, {"pulls": 0, "reward_sum": 0.0})
        if random.random() < epsilon:
            chosen = random.choice(candidate_arms)
            self._save()
            return chosen
        chosen = max(
            candidate_arms,
            key=lambda arm: self._arm_stat(bucket, arm).average_reward,
        )
        self._save()
        return chosen

    def record_reward(self, channel: str, arm: str, reward: float) -> None:
        bucket = self.state.setdefault(channel, {})
        arm_data = bucket.setdefault(arm, {"pulls": 0, "reward_sum": 0.0})
        arm_data["pulls"] += 1
        arm_data["reward_sum"] += float(reward)
        self._save()

    def _arm_stat(self, bucket: dict, arm: str) -> ArmStat:
        data = bucket.get(arm, {"pulls": 0, "reward_sum": 0.0})
        return ArmStat(pulls=int(data["pulls"]), reward_sum=float(data["reward_sum"]))

    def _load(self) -> dict:
        if not self.storage_path.exists():
            return {}
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        self.storage_path.write_text(
            json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8"
        )
```

- [ ] **Step 2: Write pipeline/qa.py**

```python
from __future__ import annotations

from yt_automator.models import ContentPackage
from yt_automator.utils.text import word_count


class QualityGate:
    def __init__(self, min_words: int = 75, max_words: int = 185):
        self.min_words = min_words
        self.max_words = max_words

    def validate_content(self, package: ContentPackage) -> tuple[bool, list[str]]:
        issues: list[str] = []
        count = word_count(package.script)
        if count < self.min_words:
            issues.append(f"Script too short ({count} words), likely <30s spoken")
        if count > self.max_words:
            issues.append(f"Script too long ({count} words), likely >60s spoken")
        if len(package.title) > 90:
            issues.append("Title too long (keep under 90 chars)")
        if not package.tags:
            issues.append("Missing tags")
        return (len(issues) == 0, issues)
```

- [ ] **Step 3: Write pipeline/run_logger.py**

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from yt_automator.models import PublishRecord


class RunLogger:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def log_publish_record(self, record: PublishRecord) -> Path:
        date_key = datetime.utcnow().strftime("%Y-%m-%d")
        output_path = self.data_dir / f"{date_key}.jsonl"
        payload = {
            "channel": record.channel,
            "topic": record.package.topic,
            "style_variant": record.package.style_variant,
            "title": record.package.title,
            "description": record.package.description,
            "tags": record.package.tags,
            "source_links": record.package.source_links,
            "video_path": str(record.render_result.video_path),
            "duration_seconds": record.render_result.duration_seconds,
            "upload_success": record.upload_result.success,
            "video_url": record.upload_result.video_url,
            "video_id": record.upload_result.video_id,
            "upload_error": record.upload_result.error,
            "scheduled_publish_at": record.scheduled_publish_at,
            "created_at": record.created_at.isoformat(),
        }
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return output_path
```

- [ ] **Step 4: Add bandit and QA tests to tests/test_smoke.py**

```python
# append to tests/test_smoke.py
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
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all existing + 4 new tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/yt_automator/optimizer/ src/yt_automator/pipeline/qa.py src/yt_automator/pipeline/run_logger.py tests/test_smoke.py
git commit -m "feat: add bandit optimizer, QA gate, and run logger"
```

---

## Task 5: Media providers and MediaSourcer

**Files:**
- Create: `src/yt_automator/providers/base.py`
- Create: `src/yt_automator/providers/pixabay_provider.py`
- Create: `src/yt_automator/providers/wikimedia_provider.py`
- Create: `src/yt_automator/providers/nasa_provider.py`
- Create: `src/yt_automator/pipeline/media_sourcer.py`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write providers/base.py**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from yt_automator.models import MediaAsset


class MediaProvider(ABC):
    name: str

    @abstractmethod
    def search_and_download(
        self,
        query: str,
        output_dir: Path,
        max_assets: int,
    ) -> list[MediaAsset]:
        raise NotImplementedError
```

- [ ] **Step 2: Write providers/pixabay_provider.py**

```python
from __future__ import annotations

from pathlib import Path

import requests

from yt_automator.models import MediaAsset
from yt_automator.providers.base import MediaProvider
from yt_automator.utils.paths import ensure_parent


class PixabayProvider(MediaProvider):
    name = "pixabay"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    def search_and_download(
        self,
        query: str,
        output_dir: Path,
        max_assets: int,
    ) -> list[MediaAsset]:
        if not self.api_key:
            return []
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": min(max_assets, 10),
            "orientation": "vertical",
            "image_type": "photo",
            "safesearch": "true",
        }
        resp = requests.get("https://pixabay.com/api/", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        assets: list[MediaAsset] = []
        for idx, hit in enumerate(data.get("hits", [])):
            url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not url:
                continue
            output_path = output_dir / f"pixabay_{idx}.jpg"
            ensure_parent(output_path)
            image_data = requests.get(url, timeout=30)
            image_data.raise_for_status()
            output_path.write_bytes(image_data.content)
            assets.append(
                MediaAsset(
                    provider=self.name,
                    local_path=output_path,
                    source_url=url,
                    license_name="Pixabay License",
                    attribution_required=False,
                )
            )
            if len(assets) >= max_assets:
                break
        return assets
```

- [ ] **Step 3: Write providers/wikimedia_provider.py**

```python
from __future__ import annotations

from pathlib import Path

import requests

from yt_automator.models import MediaAsset
from yt_automator.providers.base import MediaProvider
from yt_automator.utils.paths import ensure_parent


class WikimediaProvider(MediaProvider):
    name = "wikimedia"
    ENDPOINT = "https://commons.wikimedia.org/w/api.php"
    USER_AGENT = "yt-automator-v2/0.1 (contact: local-runner)"

    def search_and_download(
        self,
        query: str,
        output_dir: Path,
        max_assets: int,
    ) -> list[MediaAsset]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": min(max_assets * 3, 20),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1080,
            "format": "json",
        }
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.get(self.ENDPOINT, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()

        pages = payload.get("query", {}).get("pages", {})
        assets: list[MediaAsset] = []
        for idx, page in enumerate(pages.values()):
            image_info = (page.get("imageinfo") or [{}])[0]
            image_url = image_info.get("thumburl") or image_info.get("url")
            if not image_url:
                continue
            metadata = image_info.get("extmetadata") or {}
            license_short = (metadata.get("LicenseShortName") or {}).get("value", "Unknown")
            if not self._is_license_allowed(license_short):
                continue
            output_path = output_dir / f"wikimedia_{idx}.jpg"
            ensure_parent(output_path)
            raw = requests.get(image_url, headers=headers, timeout=20)
            raw.raise_for_status()
            output_path.write_bytes(raw.content)
            assets.append(
                MediaAsset(
                    provider=self.name,
                    local_path=output_path,
                    source_url=image_url,
                    license_name=license_short,
                    attribution_required=True,
                )
            )
            if len(assets) >= max_assets:
                break
        return assets

    @staticmethod
    def _is_license_allowed(license_name: str) -> bool:
        lowered = license_name.lower()
        blocked = ["noncommercial", "no derivatives", "all rights reserved", "unknown"]
        allowed = ["cc0", "public domain", "cc by", "cc-by", "cc by-sa", "cc-by-sa"]
        if any(t in lowered for t in blocked):
            return False
        return any(t in lowered for t in allowed)
```

- [ ] **Step 4: Write providers/nasa_provider.py**

```python
from __future__ import annotations

from pathlib import Path

import requests

from yt_automator.models import MediaAsset
from yt_automator.providers.base import MediaProvider
from yt_automator.utils.paths import ensure_parent


class NasaProvider(MediaProvider):
    name = "nasa"

    def __init__(self, api_key: str | None):
        self.api_key = api_key or "DEMO_KEY"

    def search_and_download(
        self,
        query: str,
        output_dir: Path,
        max_assets: int,
    ) -> list[MediaAsset]:
        params = {"q": query, "media_type": "image", "page": 1}
        resp = requests.get(
            "https://images-api.nasa.gov/search", params=params, timeout=20
        )
        resp.raise_for_status()
        items = resp.json().get("collection", {}).get("items", [])

        assets: list[MediaAsset] = []
        for idx, item in enumerate(items):
            links = item.get("links") or []
            if not links:
                continue
            image_url = links[0].get("href")
            if not image_url:
                continue
            out_path = output_dir / f"nasa_{idx}.jpg"
            ensure_parent(out_path)
            raw = requests.get(image_url, timeout=20)
            raw.raise_for_status()
            out_path.write_bytes(raw.content)
            assets.append(
                MediaAsset(
                    provider=self.name,
                    local_path=out_path,
                    source_url=image_url,
                    license_name="NASA Media Usage",
                    attribution_required=True,
                )
            )
            if len(assets) >= max_assets:
                break
        return assets
```

- [ ] **Step 5: Write pipeline/media_sourcer.py**

```python
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from yt_automator.models import MediaAsset
from yt_automator.providers.base import MediaProvider


class MediaSourcer:
    def __init__(self, providers: list[MediaProvider]):
        self.providers = providers

    def fetch_assets(
        self,
        query: str,
        output_dir: Path,
        max_assets: int,
    ) -> list[MediaAsset]:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets: list[MediaAsset] = []
        for provider in self.providers:
            if len(assets) >= max_assets:
                break
            try:
                needed = max_assets - len(assets)
                found = provider.search_and_download(query, output_dir, needed)
                assets.extend(found)
            except Exception as exc:
                print(f"[WARN] Provider {provider.name} failed: {exc}")

        if assets:
            return assets

        fallback_path = output_dir / "local_fallback.jpg"
        self._create_fallback_image(query, fallback_path)
        return [
            MediaAsset(
                provider="local-fallback",
                local_path=fallback_path,
                source_url="local://generated",
                license_name="generated",
                attribution_required=False,
            )
        ]

    @staticmethod
    def _create_fallback_image(query: str, path: Path) -> None:
        image = Image.new(
            "RGB",
            (1080, 1920),
            color=(
                random.randint(0, 70),
                random.randint(0, 70),
                random.randint(0, 70),
            ),
        )
        draw = ImageDraw.Draw(image)
        text = f"{query}\n\nVisual fallback"
        try:
            font = ImageFont.truetype("Arial.ttf", 68)
        except Exception:
            font = ImageFont.load_default()
        draw.multiline_text((70, 200), text, fill=(235, 235, 235), font=font, spacing=18)
        image.save(path)
```

- [ ] **Step 6: Add wikimedia license test to tests/test_smoke.py**

```python
# append to tests/test_smoke.py
from yt_automator.providers.wikimedia_provider import WikimediaProvider


def test_wikimedia_allows_cc0():
    assert WikimediaProvider._is_license_allowed("CC0") is True


def test_wikimedia_allows_cc_by():
    assert WikimediaProvider._is_license_allowed("CC BY 4.0") is True


def test_wikimedia_blocks_all_rights_reserved():
    assert WikimediaProvider._is_license_allowed("All Rights Reserved") is False


def test_wikimedia_blocks_unknown():
    assert WikimediaProvider._is_license_allowed("Unknown") is False
```

- [ ] **Step 7: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all tests pass including 4 new wikimedia license tests.

- [ ] **Step 8: Commit**

```bash
git add src/yt_automator/providers/ src/yt_automator/pipeline/media_sourcer.py tests/test_smoke.py
git commit -m "feat: add media providers and media sourcer"
```

---

## Task 6: TTS engine and subtitle writer

**Files:**
- Create: `src/yt_automator/pipeline/tts_engine.py`
- Create: `src/yt_automator/pipeline/subtitles.py`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write pipeline/tts_engine.py**

```python
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import edge_tts


class TTSEngine:
    def __init__(self, voices: list[str]):
        self.voices = voices

    async def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        selected_voice = voice or self.voices[0]
        try:
            communicate = edge_tts.Communicate(text, selected_voice, rate="+15%")
            await communicate.save(str(output_path))
            return output_path
        except Exception as exc:
            print(f"[WARN] edge-tts failed, using silent fallback: {exc}")
            self._create_silent_fallback(output_path)
            return output_path

    @staticmethod
    def _create_silent_fallback(output_path: Path) -> None:
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


def run_async(coro):
    return asyncio.run(coro)
```

- [ ] **Step 2: Write pipeline/subtitles.py (fixed bottom-center alignment)**

```python
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
            print(f"[WARN] Whisper failed, using synthetic subtitles: {exc}")
            return [
                {
                    "words": [
                        {"word": "Quick", "start": 0.0, "end": 0.9},
                        {"word": "story", "start": 0.9, "end": 1.8},
                        {"word": "today", "start": 1.8, "end": 2.8},
                    ]
                }
            ]

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
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = int(value % 60)
        centiseconds = int((value - int(value)) * 100)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
```

- [ ] **Step 3: Add subtitle format test to tests/test_smoke.py**

The Style line format when split by "," has Alignment at index 18 (0=Name, 1=Fontname, ..., 17=Shadow, 18=Alignment).

```python
# append to tests/test_smoke.py
import tempfile
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
    # Style line fields (0-indexed): 0=Name, 1=Fontname, ..., 17=Shadow, 18=Alignment
    style_line = [l for l in content.splitlines() if l.startswith("Style:")][0]
    fields = style_line.split(",")
    assert fields[18] == "2", f"Expected Alignment=2 (bottom-center), got {fields[18]}"
    assert "HELLO" in content
    assert "WORLD" in content
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/yt_automator/pipeline/tts_engine.py src/yt_automator/pipeline/subtitles.py tests/test_smoke.py
git commit -m "feat: add TTS engine and subtitle writer (fix bottom-center alignment)"
```

---

## Task 7: Content generator (google-genai SDK)

**Files:**
- Create: `src/yt_automator/pipeline/content_generator.py`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write pipeline/content_generator.py**

```python
from __future__ import annotations

import json
import random
import requests
from typing import Any

from yt_automator.models import ContentPackage
from yt_automator.utils.text import normalize_script, sentence_split


class ContentGenerator:
    def __init__(
        self,
        gemini_api_key: str | None,
        ollama_model: str | None = None,
        ollama_base_url: str = "http://localhost:11434",
        gemini_model: str = "gemini-2.0-flash-lite",
    ):
        self.gemini_api_key = gemini_api_key
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.gemini_model = gemini_model
        self._client = None
        if gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=gemini_api_key)
            except Exception:
                self._client = None

    def generate(
        self,
        channel_config: dict[str, Any],
        strategy_key: str,
        strategy_data: dict[str, Any],
        history: list[str],
        reddit_context: dict[str, str] | None = None,
    ) -> ContentPackage:
        prompt_profile = channel_config["prompt_profile"]
        theme = strategy_data["theme"]

        history_text = ""
        if history:
            latest = ", ".join(f'"{t}"' for t in history[-40:])
            history_text = f"Do not repeat these already covered topics: [{latest}]"

        reddit_text = ""
        if reddit_context:
            reddit_text = (
                "Incorporate this community story context while transforming it into an "
                "original narrative. Avoid direct copying. "
                f"Story title: {reddit_context.get('title', '')}. "
                f"Story summary: {reddit_context.get('summary', '')}."
            )

        prompt = f"""{prompt_profile['system_role']}

Channel: {channel_config['channel_name']}
Theme: {theme}
Strategy key: {strategy_key}
{history_text}
{reddit_text}

Script rules:
{prompt_profile['script_rules']}

Return strict JSON object with keys:
topic, script, title, description, video_query, tags, source_links""".strip()

        if self.ollama_model:
            try:
                payload = self._generate_with_ollama(prompt)
                return self._to_package(payload)
            except Exception:
                pass

        if self._client is not None:
            try:
                response = self._client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
                payload = self._parse_json(response.text)
                return self._to_package(payload)
            except Exception:
                pass

        return self._fallback_package(channel_config, strategy_data, reddit_context)

    def _generate_with_ollama(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("response", "{}").strip()
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)

    @staticmethod
    def _to_package(payload: dict[str, Any]) -> ContentPackage:
        script = normalize_script(payload.get("script", ""))
        script = " ".join(sentence_split(script))
        return ContentPackage(
            topic=str(payload.get("topic", "Untitled topic")).strip(),
            script=script,
            title=str(payload.get("title", "Untitled short")).strip(),
            description=str(payload.get("description", "")).strip(),
            video_query=str(payload.get("video_query", "interesting visuals")).strip(),
            tags=[str(item) for item in payload.get("tags", [])][:12],
            source_links=[str(item) for item in payload.get("source_links", [])][:8],
            style_variant=str(payload.get("style_variant", "default")),
        )

    @staticmethod
    def _fallback_package(
        channel_config: dict[str, Any],
        strategy_data: dict[str, Any],
        reddit_context: dict[str, str] | None,
    ) -> ContentPackage:
        topic = strategy_data["theme"]
        snippets = [
            "Most people miss this detail, but it changes the whole story.",
            "This fact sounds fake, yet it is documented.",
            "Here is where experts completely disagree.",
        ]
        script = (
            f"Quick deep dive on {topic}. "
            "This starts with a claim almost everyone gets wrong. "
            f"{random.choice(snippets)} "
            "The middle of this story is where the explanation gets counterintuitive, "
            "because the obvious answer fails when you look at real evidence. "
            "By the end, one small detail flips the conclusion and makes the whole topic "
            "easier to remember. "
            "Follow for the next short if you want more high-signal facts without fluff."
        )
        return ContentPackage(
            topic=topic,
            script=normalize_script(script),
            title=f"{channel_config['channel_name'].title()} short: {topic[:48]}",
            description=(
                f"{topic}. Built for quick learning and retention. "
                f"#{channel_config['channel_name']} #shorts #learn"
            ),
            video_query=strategy_data.get("default_query", "cinematic vertical background"),
            tags=[channel_config["channel_name"], "shorts", "education", "viral"],
            source_links=[],
            style_variant="fallback",
        )
```

- [ ] **Step 2: Add fallback test to tests/test_smoke.py**

```python
# append to tests/test_smoke.py
from yt_automator.pipeline.content_generator import ContentGenerator


def test_content_generator_fallback_returns_package():
    gen = ContentGenerator(gemini_api_key=None, ollama_model=None)
    channel_config = {
        "channel_name": "biology",
        "prompt_profile": {
            "system_role": "You are a biology writer.",
            "script_rules": "Write 30-60 seconds.",
        },
    }
    strategy_data = {"theme": "deep ocean creatures", "default_query": "ocean"}
    pkg = gen.generate(
        channel_config=channel_config,
        strategy_key="deep_ocean",
        strategy_data=strategy_data,
        history=[],
    )
    assert pkg.topic == "deep ocean creatures"
    assert len(pkg.script) > 50
    assert pkg.tags == ["biology", "shorts", "education", "viral"]
```

- [ ] **Step 3: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/yt_automator/pipeline/content_generator.py tests/test_smoke.py
git commit -m "feat: add content generator with google-genai SDK"
```

---

## Task 8: Video renderer

**Files:**
- Create: `src/yt_automator/pipeline/video_renderer.py`

No unit tests — requires live ffmpeg + real media files. Validated in Task 13 (make doctor + dry-run).

- [ ] **Step 1: Write pipeline/video_renderer.py**

```python
from __future__ import annotations

import subprocess
from pathlib import Path

from yt_automator.models import MediaAsset, RenderResult


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

        filter_chain = (
            "scale=8000:-1,"
            f"zoompan=z='min(zoom+0.00055,1.12)':d={frame_count}:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=24,"
            f"ass=filename='{subtitle_path.as_posix()}'"
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
            if "No such filter" in stderr or "ass" in stderr:
                print("[WARN] ffmpeg ass filter unavailable, retrying without subtitles")
                self._render_without_subtitles(primary, voice_audio_path, music_path, duration, output_path)
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
            raise RuntimeError(f"ffmpeg fallback render failed: {inner_stderr}") from inner_exc

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
        except Exception:
            return 6.0
```

- [ ] **Step 2: Commit**

```bash
git add src/yt_automator/pipeline/video_renderer.py
git commit -m "feat: add video renderer (ffmpeg Ken Burns + subtitle burn-in)"
```

---

## Task 9: YouTube client

**Files:**
- Create: `src/yt_automator/pipeline/youtube_client.py`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write pipeline/youtube_client.py**

```python
from __future__ import annotations

import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from yt_automator.models import UploadResult


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeClient:
    def __init__(self, credentials_path: Path, token_path: Path):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> bool:
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds:
                if not self.credentials_path.exists():
                    print(f"[FAIL] Missing credentials file: {self.credentials_path}")
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
        self.service = build("youtube", "v3", credentials=creds)
        return True

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str,
        privacy_status: str,
        publish_at: str | None,
        dry_run: bool,
    ) -> UploadResult:
        if dry_run:
            return UploadResult(
                success=True,
                video_url="https://www.youtube.com/watch?v=DRYRUN",
                video_id="DRYRUN",
            )

        if self.service is None and not self.authenticate():
            return UploadResult(
                success=False, video_url=None, video_id=None,
                error="Authentication failed",
            )

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": "private" if publish_at else privacy_status,
                "madeForKids": False,
                "selfDeclaredMadeForKids": False,
                "embeddable": True,
                "publicStatsViewable": True,
            },
        }
        if publish_at:
            body["status"]["publishAt"] = publish_at

        media = MediaFileUpload(
            str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4"
        )
        request = self.service.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )

        for attempt in range(3):
            try:
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        print(f"[INFO] Upload progress: {int(status.progress() * 100)}%")
                video_id = response["id"]
                return UploadResult(
                    success=True,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    video_id=video_id,
                )
            except HttpError as exc:
                if exc.resp.status in {500, 502, 503, 504} and attempt < 2:
                    time.sleep(5)
                    continue
                return UploadResult(
                    success=False, video_url=None, video_id=None, error=str(exc)
                )
            except Exception as exc:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return UploadResult(
                    success=False, video_url=None, video_id=None, error=str(exc)
                )

        return UploadResult(
            success=False, video_url=None, video_id=None, error="unknown"
        )
```

- [ ] **Step 2: Add dry-run test to tests/test_smoke.py**

```python
# append to tests/test_smoke.py
import tempfile
from yt_automator.pipeline.youtube_client import YouTubeClient


def test_youtube_dry_run_returns_success():
    with tempfile.TemporaryDirectory() as tmp:
        client = YouTubeClient(
            credentials_path=Path(tmp) / "creds.json",
            token_path=Path(tmp) / "token.json",
        )
        result = client.upload_short(
            video_path=Path(tmp) / "video.mp4",
            title="Test",
            description="desc",
            tags=["tag"],
            category_id="27",
            privacy_status="public",
            publish_at=None,
            dry_run=True,
        )
    assert result.success is True
    assert result.video_id == "DRYRUN"
```

- [ ] **Step 3: Run tests**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/yt_automator/pipeline/youtube_client.py tests/test_smoke.py
git commit -m "feat: add YouTube client with OAuth2 upload and dry-run mode"
```

---

## Task 10: Orchestrator

**Files:**
- Create: `src/yt_automator/pipeline/orchestrator.py`

- [ ] **Step 1: Write pipeline/orchestrator.py**

```python
from __future__ import annotations

import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from yt_automator.config import ConfigLoader
from yt_automator.models import PublishRecord
from yt_automator.optimizer.bandit_optimizer import BanditOptimizer
from yt_automator.pipeline.content_generator import ContentGenerator
from yt_automator.pipeline.media_sourcer import MediaSourcer
from yt_automator.pipeline.qa import QualityGate
from yt_automator.pipeline.run_logger import RunLogger
from yt_automator.pipeline.subtitles import SubtitleEngine
from yt_automator.pipeline.tts_engine import TTSEngine, run_async
from yt_automator.pipeline.video_renderer import VideoRenderer
from yt_automator.pipeline.youtube_client import YouTubeClient
from yt_automator.providers.nasa_provider import NasaProvider
from yt_automator.providers.pixabay_provider import PixabayProvider
from yt_automator.providers.wikimedia_provider import WikimediaProvider
from yt_automator.secrets import SecretManager
from yt_automator.utils.text import slugify
from yt_automator.utils.time_utils import generate_publish_schedule


class PipelineOrchestrator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_loader = ConfigLoader(repo_root)
        self.secret_manager = SecretManager(repo_root)
        self.app_settings = self.config_loader.load_app_settings()
        self.media_source_settings = self.config_loader.load_media_sources()

        optimizer_path = repo_root / "data" / "optimizer" / "bandit_state.json"
        self.optimizer = BanditOptimizer(optimizer_path)
        self.logger = RunLogger(repo_root / "data" / "runs")

    def list_channels(self) -> list[str]:
        return self.config_loader.list_channels()

    def get_channel_config(self, channel_name: str) -> dict:
        return self.config_loader.load_channel(channel_name)

    def run_batch(
        self,
        channels: list[str] | None,
        count: int,
        schedule: bool,
        dry_run: bool,
    ) -> None:
        targets = channels or self.list_channels()
        for channel in targets:
            self.run_once(
                channel_name=channel, count=count, schedule=schedule, dry_run=dry_run
            )

    def run_doctor(self, strict: bool = False) -> int:
        errors = 0
        warnings = 0
        print("[INFO] Running environment checks")

        for cmd in ("ffmpeg", "ffprobe"):
            if shutil.which(cmd):
                print(f"[OK] Found dependency: {cmd}")
            else:
                print(f"[FAIL] Missing dependency: {cmd}")
                errors += 1

        channels = self.list_channels()
        if not channels:
            print("[FAIL] No channel configs found in config/channels")
            errors += 1
        else:
            print(f"[OK] Found {len(channels)} channel configs")

        has_backend = bool(
            self.secret_manager.get("GEMINI_API_KEY")
            or self.secret_manager.get("OLLAMA_MODEL")
        )
        if has_backend:
            print("[OK] At least one generation backend configured")
        else:
            print("[WARN] No GEMINI_API_KEY or OLLAMA_MODEL set (fallback scripts used)")
            warnings += 1

        if self.secret_manager.get("PIXABAY_API_KEY"):
            print("[OK] PIXABAY_API_KEY is set")
        else:
            print("[WARN] PIXABAY_API_KEY not set (Wikimedia fallback will be used)")
            warnings += 1

        for channel in channels:
            cfg = self.get_channel_config(channel)
            creds_path, token_path = self._resolve_youtube_paths(cfg)
            if creds_path.exists():
                print(f"[OK] {channel}: credentials file found")
            else:
                print(f"[FAIL] {channel}: missing credentials at {creds_path}")
                errors += 1
            if not token_path.exists():
                print(f"[INFO] {channel}: token missing (created on first auth)")

            music_list = cfg["paths"]["music_files"]
            found = [
                n for n in music_list
                if (self.repo_root / "assets" / "music" / n).exists()
            ]
            if found:
                print(f"[OK] {channel}: found {len(found)} music file(s)")
            else:
                print(f"[WARN] {channel}: no music files found; silent fallback used")
                warnings += 1

        print(f"[INFO] Doctor summary: errors={errors} warnings={warnings}")

        if strict and (errors > 0 or warnings > 0):
            return 1
        return 1 if errors > 0 else 0

    def run_once(
        self,
        channel_name: str,
        count: int,
        schedule: bool,
        dry_run: bool,
    ) -> None:
        cfg = self.config_loader.load_channel(channel_name)
        history = self._load_topic_history(cfg)
        schedule_times: list[str] = []
        if schedule:
            schedule_times = generate_publish_schedule(
                cfg["youtube"]["daily_slots"],
                cfg["youtube"]["timezone"],
                count,
            )

        voices = self.app_settings["voices"]
        tts = TTSEngine(voices)
        subtitle_engine = SubtitleEngine(self.app_settings["subtitle_model"])
        qa_gate = QualityGate()

        gemini_key = self.secret_manager.get("GEMINI_API_KEY")
        ollama_model = self.secret_manager.get("OLLAMA_MODEL") or self.app_settings.get(
            "ollama_model"
        )
        ollama_base_url = self.app_settings.get("ollama_base_url", "http://localhost:11434")
        gemini_model = self.app_settings.get("gemini_model", "gemini-2.0-flash-lite")
        generator = ContentGenerator(
            gemini_key,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
            gemini_model=gemini_model,
        )

        media_sourcer = self._build_media_sourcer(channel_name)
        renderer = VideoRenderer()
        creds_path, token_path = self._resolve_youtube_paths(cfg)
        youtube_client = YouTubeClient(creds_path, token_path)

        for index in range(count):
            print(f"\n[BUILD] [{channel_name}] generating video {index + 1}/{count}")

            strategy_key, strategy_data = self._pick_strategy(cfg)
            package = generator.generate(
                channel_config=cfg,
                strategy_key=strategy_key,
                strategy_data=strategy_data,
                history=history,
            )
            package.style_variant = strategy_key

            valid, issues = qa_gate.validate_content(package)
            if not valid:
                print(f"[WARN] QA issues: {issues}")

            run_dir = self._new_run_dir(channel_name, package.topic)
            audio_path = run_dir / "voice.mp3"
            subtitle_path = run_dir / "subs.ass"
            video_path = run_dir / "final.mp4"

            voice = random.choice(voices)
            run_async(tts.synthesize(package.script, audio_path, voice=voice))
            segments = subtitle_engine.transcribe_segments(audio_path)
            subtitle_engine.write_ass(segments, subtitle_path)

            assets = media_sourcer.fetch_assets(
                package.video_query,
                run_dir / "assets",
                max_assets=cfg["pipeline"]["assets_per_video"],
            )

            music_path = self._resolve_music_file(cfg)
            render_result = renderer.render(
                assets=assets,
                voice_audio_path=audio_path,
                subtitle_path=subtitle_path,
                music_path=music_path,
                output_path=video_path,
            )

            publish_at = schedule_times[index] if schedule else None
            upload_result = youtube_client.upload_short(
                video_path=render_result.video_path,
                title=package.title,
                description=package.description,
                tags=package.tags,
                category_id=cfg["youtube"]["category_id"],
                privacy_status=cfg["youtube"]["privacy_status"],
                publish_at=publish_at,
                dry_run=dry_run,
            )

            record = PublishRecord(
                channel=channel_name,
                package=package,
                render_result=render_result,
                upload_result=upload_result,
                scheduled_publish_at=publish_at,
                created_at=datetime.utcnow(),
            )
            self.logger.log_publish_record(record)

            if upload_result.success:
                print(f"[OK] Uploaded: {upload_result.video_url}")
                self._append_topic_history(cfg, package.topic)
                history.append(package.topic)
            else:
                print(f"[FAIL] Upload failed: {upload_result.error}")

    def record_manual_reward(self, channel: str, arm: str, reward: float) -> None:
        self.optimizer.record_reward(channel, arm, reward)

    def _pick_strategy(self, cfg: dict) -> tuple[str, dict]:
        strategies = cfg["content_strategies"]
        arms = list(strategies.keys())
        epsilon = float(cfg["rl_profile"].get("epsilon", 0.2))
        chosen = self.optimizer.pick_arm(cfg["channel_name"], arms, epsilon)
        return chosen, strategies[chosen]

    def _build_media_sourcer(self, channel_name: str) -> MediaSourcer:
        providers = []
        pixabay_key = self.secret_manager.get("PIXABAY_API_KEY")
        for provider_cfg in self.media_source_settings.get("providers", []):
            if not provider_cfg.get("enabled", False):
                continue
            channels = provider_cfg.get("channels")
            if channels and channel_name not in channels:
                continue
            name = provider_cfg.get("name")
            if name == "pixabay":
                providers.append(PixabayProvider(pixabay_key))
            elif name == "wikimedia":
                providers.append(WikimediaProvider())
            elif name == "nasa":
                providers.append(NasaProvider(self.secret_manager.get("NASA_API_KEY")))
        if not providers:
            providers.append(WikimediaProvider())
        return MediaSourcer(providers)

    def _resolve_music_file(self, cfg: dict) -> Path:
        music_files = cfg["paths"]["music_files"]
        candidates = [
            self.repo_root / "assets" / "music" / name
            for name in music_files
            if (self.repo_root / "assets" / "music" / name).exists()
        ]
        if not candidates:
            fallback = self.repo_root / "assets" / "music" / "fallback_silent.mp3"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            if not fallback.exists():
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=mono",
                        "-t", "8", "-q:a", "9", "-acodec", "libmp3lame",
                        str(fallback),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            candidates.append(fallback)
        return random.choice(candidates)

    def _resolve_youtube_paths(self, cfg: dict) -> tuple[Path, Path]:
        creds_file = cfg["youtube"]["credentials_file"]
        token_file = cfg["youtube"]["token_file"]
        creds_path = self.repo_root / "secrets" / "youtube" / creds_file
        token_path = self.repo_root / "secrets" / "youtube" / token_file
        return creds_path, token_path

    def _load_topic_history(self, cfg: dict) -> list[str]:
        history_path = self.repo_root / cfg["paths"]["topic_history"]
        if not history_path.exists():
            return []
        try:
            return [
                line.strip()
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception:
            return []

    def _append_topic_history(self, cfg: dict, topic: str) -> None:
        history_path = self.repo_root / cfg["paths"]["topic_history"]
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(topic + "\n")

    def _new_run_dir(self, channel: str, topic: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = slugify(topic)[:45]
        path = self.repo_root / "outputs" / channel / f"{timestamp}_{slug}"
        path.mkdir(parents=True, exist_ok=True)
        return path
```

- [ ] **Step 2: Commit**

```bash
git add src/yt_automator/pipeline/orchestrator.py
git commit -m "feat: add pipeline orchestrator"
```

---

## Task 11: CLI entry point

**Files:**
- Create: `src/yt_automator/cli.py`

- [ ] **Step 1: Write cli.py**

```python
from __future__ import annotations

import argparse
import time

import schedule

from yt_automator.pipeline.orchestrator import PipelineOrchestrator
from yt_automator.utils.paths import get_repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube Automator v2")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-channels", help="List available channels")

    run_cmd = sub.add_parser("run", help="Generate and upload videos now")
    run_cmd.add_argument("channel", help="Channel slug from config/channels")
    run_cmd.add_argument("--count", type=int, default=1)
    run_cmd.add_argument("--schedule-publish", action="store_true")
    run_cmd.add_argument("--dry-run", action="store_true")

    run_all_cmd = sub.add_parser("run-all", help="Run all channels")
    run_all_cmd.add_argument("--count", type=int, default=1)
    run_all_cmd.add_argument("--schedule-publish", action="store_true")
    run_all_cmd.add_argument("--dry-run", action="store_true")

    daemon_cmd = sub.add_parser("daemon", help="Run scheduler for one channel")
    daemon_cmd.add_argument("channel")
    daemon_cmd.add_argument("--dry-run", action="store_true")

    daemon_all_cmd = sub.add_parser("daemon-all", help="Run scheduler for all channels")
    daemon_all_cmd.add_argument("--dry-run", action="store_true")
    daemon_all_cmd.add_argument("--run-now", action="store_true")

    reward_cmd = sub.add_parser("record-reward", help="Record manual reward for a strategy arm")
    reward_cmd.add_argument("channel")
    reward_cmd.add_argument("arm")
    reward_cmd.add_argument("reward", type=float)

    doctor_cmd = sub.add_parser("doctor", help="Validate setup and credentials")
    doctor_cmd.add_argument("--strict", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = PipelineOrchestrator(get_repo_root())

    if args.command == "list-channels":
        for ch in orchestrator.list_channels():
            print(ch)

    elif args.command == "run":
        orchestrator.run_once(
            channel_name=args.channel,
            count=max(args.count, 1),
            schedule=args.schedule_publish,
            dry_run=args.dry_run,
        )

    elif args.command == "run-all":
        orchestrator.run_batch(
            channels=None,
            count=max(args.count, 1),
            schedule=args.schedule_publish,
            dry_run=args.dry_run,
        )

    elif args.command == "daemon":
        _run_daemon(orchestrator, args.channel, args.dry_run)

    elif args.command == "daemon-all":
        _run_daemon_all(orchestrator, args.dry_run, args.run_now)

    elif args.command == "record-reward":
        orchestrator.record_manual_reward(args.channel, args.arm, args.reward)
        print("[OK] Reward recorded")

    elif args.command == "doctor":
        raise SystemExit(orchestrator.run_doctor(strict=args.strict))


def _run_daemon(orchestrator: PipelineOrchestrator, channel: str, dry_run: bool) -> None:
    cfg = orchestrator.get_channel_config(channel)
    slots = cfg["youtube"]["daily_slots"]
    print(f"[INFO] Starting daemon for {channel}. Daily slots: {', '.join(slots)} IST")
    for slot in slots:
        schedule.every().day.at(slot).do(
            orchestrator.run_once,
            channel_name=channel, count=1, schedule=False, dry_run=dry_run,
        )
    orchestrator.run_once(channel_name=channel, count=1, schedule=False, dry_run=dry_run)
    while True:
        schedule.run_pending()
        time.sleep(1)


def _run_daemon_all(
    orchestrator: PipelineOrchestrator, dry_run: bool, run_now: bool
) -> None:
    channels = orchestrator.list_channels()
    if not channels:
        print("[FAIL] No channels found")
        return
    print(f"[INFO] Starting daemon for all channels ({len(channels)} total)")
    for channel in channels:
        cfg = orchestrator.get_channel_config(channel)
        slots = cfg["youtube"]["daily_slots"]
        print(f"[INFO] {channel}: {', '.join(slots)}")
        for slot in slots:
            schedule.every().day.at(slot).do(
                orchestrator.run_once,
                channel_name=channel, count=1, schedule=False, dry_run=dry_run,
            )
    if run_now:
        orchestrator.run_batch(channels=channels, count=1, schedule=False, dry_run=dry_run)
    while True:
        schedule.run_pending()
        time.sleep(1)
```

- [ ] **Step 2: Commit**

```bash
git add src/yt_automator/cli.py
git commit -m "feat: add CLI entry point"
```

---

## Task 12: Channel configs and app settings

**Files:**
- Create: `config/app_settings.json`
- Create: `config/media_sources.json`
- Create: `config/channels/biology.json`
- Create: `config/channels/physics.json`
- Create: `config/channels/history.json`
- Create: `data/history/biology_topics.txt`
- Create: `data/history/physics_topics.txt`
- Create: `data/history/history_topics.txt`
- Test: `tests/test_smoke.py` (extend)

- [ ] **Step 1: Write config/app_settings.json**

```json
{
  "subtitle_model": "tiny.en",
  "gemini_model": "gemini-2.0-flash-lite",
  "ollama_model": null,
  "ollama_base_url": "http://localhost:11434",
  "voices": [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
    "en-AU-WilliamNeural",
    "en-CA-LiamNeural"
  ]
}
```

- [ ] **Step 2: Write config/media_sources.json**

```json
{
  "providers": [
    {
      "name": "pixabay",
      "enabled": true,
      "type": "image"
    },
    {
      "name": "wikimedia",
      "enabled": true,
      "type": "image"
    },
    {
      "name": "nasa",
      "enabled": true,
      "type": "image",
      "channels": ["physics"]
    }
  ],
  "license_allowlist": [
    "cc0",
    "public domain",
    "cc by",
    "cc-by",
    "cc by-sa",
    "cc-by-sa",
    "pixabay license",
    "nasa media usage"
  ]
}
```

- [ ] **Step 3: Write config/channels/biology.json**

```json
{
  "channel_name": "biology",
  "youtube": {
    "credentials_file": "biology_credentials.json",
    "token_file": "biology_token.json",
    "category_id": "27",
    "privacy_status": "public",
    "timezone": "Asia/Kolkata",
    "daily_slots": ["17:30", "19:00", "20:30", "22:00", "23:30"]
  },
  "paths": {
    "topic_history": "data/history/biology_topics.txt",
    "music_files": ["bg1.mp3", "bg2.mp3", "bg3.mp3", "bg4.mp3"]
  },
  "pipeline": {
    "assets_per_video": 1
  },
  "rl_profile": {
    "epsilon": 0.2
  },
  "content_strategies": {
    "deep_ocean": {
      "theme": "a bizarre adaptation in deep ocean life",
      "default_query": "deep sea creature"
    },
    "microbiome": {
      "theme": "a surprising fact about microbes affecting health or ecosystems",
      "default_query": "microscope microbes"
    },
    "human_body": {
      "theme": "a little-known process inside the human body",
      "default_query": "human biology anatomy"
    },
    "plant_signals": {
      "theme": "how plants communicate or defend themselves",
      "default_query": "plants forest macro"
    },
    "evolution": {
      "theme": "an evolutionary trait that seems impossible but is real",
      "default_query": "animal adaptation nature"
    }
  },
  "prompt_profile": {
    "system_role": "You are a high-retention biology Shorts writer focused on clarity and wonder.",
    "script_rules": "Write 30 to 60 seconds spoken. Start with a sharp hook, include one counterintuitive point, and end with a clean curiosity CTA."
  }
}
```

- [ ] **Step 4: Write config/channels/physics.json**

```json
{
  "channel_name": "physics",
  "youtube": {
    "credentials_file": "physics_credentials.json",
    "token_file": "physics_token.json",
    "category_id": "27",
    "privacy_status": "public",
    "timezone": "Asia/Kolkata",
    "daily_slots": ["17:30", "19:00", "20:30", "22:00", "23:30"]
  },
  "paths": {
    "topic_history": "data/history/physics_topics.txt",
    "music_files": ["bg1.mp3", "bg2.mp3", "bg3.mp3", "bg4.mp3"]
  },
  "pipeline": {
    "assets_per_video": 1
  },
  "rl_profile": {
    "epsilon": 0.2
  },
  "content_strategies": {
    "quantum": {
      "theme": "a counterintuitive quantum mechanics phenomenon with a real-world implication",
      "default_query": "quantum physics abstract"
    },
    "relativity": {
      "theme": "a consequence of special or general relativity that surprises most people",
      "default_query": "space time universe"
    },
    "thermodynamics": {
      "theme": "an everyday thermodynamics or entropy phenomenon explained from first principles",
      "default_query": "energy heat abstract"
    },
    "astrophysics": {
      "theme": "a mind-bending fact about stars, black holes, or the scale of the universe",
      "default_query": "galaxy nebula space"
    },
    "classical_mechanics": {
      "theme": "a surprising result from classical mechanics or fluid dynamics",
      "default_query": "motion physics experiment"
    }
  },
  "prompt_profile": {
    "system_role": "You are a physics educator writing YouTube Shorts scripts optimised for wonder and clarity.",
    "script_rules": "Write 30 to 60 seconds spoken. Open with a counterintuitive hook, explain the physics simply, end with a consequence that lands emotionally. No jargon without immediate plain-language follow-up."
  }
}
```

- [ ] **Step 5: Write config/channels/history.json**

```json
{
  "channel_name": "history",
  "youtube": {
    "credentials_file": "history_credentials.json",
    "token_file": "history_token.json",
    "category_id": "27",
    "privacy_status": "public",
    "timezone": "Asia/Kolkata",
    "daily_slots": ["17:30", "19:00", "20:30", "22:00", "23:30"]
  },
  "paths": {
    "topic_history": "data/history/history_topics.txt",
    "music_files": ["bg1.mp3", "bg2.mp3", "bg3.mp3", "bg4.mp3"]
  },
  "pipeline": {
    "assets_per_video": 1
  },
  "rl_profile": {
    "epsilon": 0.2
  },
  "content_strategies": {
    "forgotten_figures": {
      "theme": "a historically important person almost no one learns about in school",
      "default_query": "vintage portrait historical archive"
    },
    "turning_points": {
      "theme": "a small overlooked decision or accident that changed the course of history",
      "default_query": "historical battle map archive"
    },
    "daily_life": {
      "theme": "what ordinary daily life was actually like for common people in a specific era",
      "default_query": "ancient civilization ruins"
    },
    "misconceptions": {
      "theme": "a popular historical belief that modern research has overturned",
      "default_query": "museum artifact ancient"
    },
    "firsts": {
      "theme": "the documented first time humanity did or invented something we now take for granted",
      "default_query": "invention discovery vintage"
    }
  },
  "prompt_profile": {
    "system_role": "You are a history educator writing punchy YouTube Shorts scripts that make the past feel immediate and surprising.",
    "script_rules": "Write 30 to 60 seconds spoken. Start with the most surprising fact in the story. Include one detail that recontextualises the event. End with a forward-looking statement about why it still matters."
  }
}
```

- [ ] **Step 6: Create empty topic history files**

```bash
touch data/history/biology_topics.txt
touch data/history/physics_topics.txt
touch data/history/history_topics.txt
```

- [ ] **Step 7: Add channel count smoke test to tests/test_smoke.py**

```python
# append to tests/test_smoke.py
from yt_automator.pipeline.orchestrator import PipelineOrchestrator
from yt_automator.utils.paths import get_repo_root


def test_channel_count_and_names():
    orchestrator = PipelineOrchestrator(get_repo_root())
    channels = orchestrator.list_channels()
    assert len(channels) == 3
    assert "biology" in channels
    assert "physics" in channels
    assert "history" in channels
```

- [ ] **Step 8: Run full test suite**

```bash
.venv/bin/pytest tests/test_smoke.py -v
```

Expected: all tests pass including channel count test.

- [ ] **Step 9: Commit**

```bash
git add config/ data/history/ tests/test_smoke.py
git commit -m "feat: add channel configs for biology, physics, history"
```

---

## Task 13: Tooling — Makefile, .env.example, SETUP.md

**Files:**
- Create: `Makefile`
- Create: `.env.example`
- Create: `SETUP.md`

- [ ] **Step 1: Write Makefile**

```makefile
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
YTA  := $(VENV)/bin/yta

.PHONY: setup doctor run dry-run daemon-all test clean

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	@echo "\n[OK] Setup complete. Copy .env.example to .env and fill in your keys."

doctor:
	$(YTA) doctor

run:
	$(YTA) run $(CHANNEL) --count 1

dry-run:
	$(YTA) run $(CHANNEL) --count 1 --dry-run

run-all-dry:
	$(YTA) run-all --count 1 --dry-run

daemon-all:
	$(YTA) daemon-all --run-now

test:
	$(VENV)/bin/pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
```

- [ ] **Step 2: Write .env.example**

```env
# ─────────────────────────────────────────────
# AI Script Generation  (at least one required)
# ─────────────────────────────────────────────

# Gemini API key — get free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=

# Ollama local model (optional, no API key needed)
# Install Ollama: https://ollama.com  then: ollama pull qwen2.5:7b
# OLLAMA_MODEL=qwen2.5:7b

# ─────────────────────────────────────────────
# Media Providers  (optional, improves image variety)
# ─────────────────────────────────────────────

# Pixabay API key — free at: https://pixabay.com/api/docs/
PIXABAY_API_KEY=

# NASA API key — free at: https://api.nasa.gov  (email → instant key)
# Used only for the physics channel. Falls back to DEMO_KEY if absent.
NASA_API_KEY=
```

- [ ] **Step 3: Write SETUP.md**

```markdown
# Setup Guide

## Prerequisites

```bash
# Install ffmpeg (required for video rendering)
brew install ffmpeg

# Verify
ffmpeg -version
```

## 1. Install Python dependencies

```bash
make setup
```

This creates `.venv/` and installs the `yta` CLI.

## 2. Set environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Key | Where to get it | Required? |
|-----|-----------------|-----------|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API key | Yes (or use Ollama) |
| `PIXABAY_API_KEY` | [pixabay.com/api](https://pixabay.com/api/docs/) | Recommended |
| `NASA_API_KEY` | [api.nasa.gov](https://api.nasa.gov) | Optional (physics only) |

## 3. Add YouTube OAuth credentials

For **each channel** (biology, physics, history):

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (one project can serve all channels)
3. **APIs & Services → Enable APIs** → enable **YouTube Data API v3**
4. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**
   - Configure consent screen if prompted: External → fill app name → Save
   - Application type: **Desktop app** → name it after the channel → Create
5. Download the JSON → rename it → place in `secrets/youtube/`:

| Channel | Filename |
|---------|----------|
| biology | `secrets/youtube/biology_credentials.json` |
| physics | `secrets/youtube/physics_credentials.json` |
| history | `secrets/youtube/history_credentials.json` |

Token files are created automatically the first time you run each channel.

## 4. Add background music

Place 3–4 royalty-free MP3 files in `assets/music/`:

| Filename | Source |
|----------|--------|
| `bg1.mp3` | [pixabay.com/music](https://pixabay.com/music) (free, no attribution) |
| `bg2.mp3` | same |
| `bg3.mp3` | same |
| `bg4.mp3` | same |

If no music files are found, the pipeline auto-generates a silent fallback.

## 5. Validate setup

```bash
make doctor
```

All `[OK]` lines = ready. `[WARN]` lines = optional. `[FAIL]` lines = must fix.

## 6. First run (dry-run — no real upload)

```bash
make dry-run CHANNEL=biology
```

This runs the full pipeline but skips the actual YouTube upload.
Check `outputs/biology/` for the generated video.

## 7. First real upload

```bash
make run CHANNEL=biology
```

A browser window will open for Google OAuth consent. Approve it once per channel.
The token is saved to `secrets/youtube/biology_token.json` for future runs.

## 8. Start the scheduler (all channels, 5 videos/day each)

```bash
make daemon-all
```

Videos are scheduled at 17:30, 19:00, 20:30, 22:00, 23:30 IST.
Keep this process running (use `screen`, `tmux`, or a system service).

## Adding more channels later

Drop a new JSON file in `config/channels/` following the same structure as `biology.json`.
Add its credentials file to `secrets/youtube/`. Run `make doctor` to verify.
```

- [ ] **Step 4: Commit**

```bash
git add Makefile .env.example SETUP.md
git commit -m "feat: add Makefile, .env.example, and SETUP.md"
```

---

## Task 14: Final verification

- [ ] **Step 1: Run full test suite**

```bash
.venv/bin/pytest tests/ -v
```

Expected: all tests pass, zero failures.

- [ ] **Step 2: Run yta list-channels**

```bash
.venv/bin/yta list-channels
```

Expected output:
```
biology
history
physics
```

- [ ] **Step 3: Run yta doctor**

```bash
.venv/bin/yta doctor
```

Expected: `[OK]` for ffmpeg, ffprobe, channel configs. `[FAIL]` for missing credentials (expected — user hasn't added them yet). `[WARN]` for GEMINI_API_KEY and music files (expected — user fills .env separately).

- [ ] **Step 4: Run dry-run end-to-end (once .env is filled)**

```bash
.venv/bin/yta run biology --count 1 --dry-run
```

Expected: video rendered in `outputs/biology/`, log written to `data/runs/YYYY-MM-DD.jsonl`, upload shows `[OK] Uploaded: https://www.youtube.com/watch?v=DRYRUN`.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete YT Automator 2.0 implementation"
```
