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
    scene_queries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MediaAsset:
    provider: str
    local_path: Path
    source_url: str
    license_name: str
    attribution_required: bool
    media_type: str = "image"  # "image" or "video"


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
