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
