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
            "q": query[:100],
            "per_page": max(3, min(max_assets, 200)),
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
