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
