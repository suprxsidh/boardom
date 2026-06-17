from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from yt_automator.models import PublishRecord


class RunLogger:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def log_publish_record(self, record: PublishRecord) -> Path:
        date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = self.data_dir / f"{date_key}.jsonl"
        payload = {
            "channel": record.channel,
            "topic": record.package.topic,
            "style_variant": record.package.style_variant,
            "title": record.package.title,
            "description": record.package.description,
            "script": record.package.script,
            "video_query": record.package.video_query,
            "scene_queries": record.package.scene_queries,
            "tags": record.package.tags,
            "source_links": record.package.source_links,
            "video_path": str(record.render_result.video_path),
            "audio_path": str(record.render_result.audio_path),
            "subtitle_path": str(record.render_result.subtitle_path),
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
