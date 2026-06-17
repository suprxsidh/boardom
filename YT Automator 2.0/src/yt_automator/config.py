from __future__ import annotations

import json
from pathlib import Path


class ConfigError(RuntimeError):
    pass


class ConfigLoader:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.channels_dir = repo_root / "channels"

    def channel_dir(self, channel_name: str) -> Path:
        return self.channels_dir / channel_name

    def list_channels(self) -> list[str]:
        if not self.channels_dir.exists():
            return []
        return sorted(
            p.name for p in self.channels_dir.iterdir()
            if p.is_dir() and (p / "config.json").exists()
        )

    def load_channel(self, channel_name: str) -> dict:
        path = self.channel_dir(channel_name) / "config.json"
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
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    def load_app_settings(self) -> dict:
        path = self.repo_root / "config" / "app_settings.json"
        if not path.exists():
            raise ConfigError(f"Missing app settings config: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    def _validate_channel_config(self, channel_name: str, config: dict) -> None:
        required = [
            "channel_name", "youtube", "content_strategies",
            "prompt_profile", "rl_profile",
        ]
        missing = [key for key in required if key not in config]
        if missing:
            raise ConfigError(
                f"Channel config {channel_name} missing keys: {', '.join(missing)}"
            )
