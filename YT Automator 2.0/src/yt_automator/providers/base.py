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
