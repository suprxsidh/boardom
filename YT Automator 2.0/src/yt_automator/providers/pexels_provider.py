from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from yt_automator.models import MediaAsset
from yt_automator.providers.base import MediaProvider
from yt_automator.utils.paths import ensure_parent


class PexelsProvider(MediaProvider):
    name = "pexels"
    _API_BASE = "https://api.pexels.com/videos/search"

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
        headers = {"Authorization": self.api_key}
        params = {
            "query": query[:100],
            "orientation": "portrait",
            "size": "medium",
            "per_page": min(max_assets + 3, 15),
        }
        resp = requests.get(self._API_BASE, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        candidates: list[tuple[int, str]] = []
        for idx, video in enumerate(data.get("videos", [])):
            file_url = self._pick_file(video.get("video_files", []))
            if file_url:
                candidates.append((idx, file_url))
            if len(candidates) >= max_assets:
                break

        output_dir.mkdir(parents=True, exist_ok=True)

        def _download(idx: int, url: str) -> MediaAsset | None:
            output_path = output_dir / f"pexels_{idx}.mp4"
            ensure_parent(output_path)
            try:
                raw = requests.get(url, timeout=60, stream=True)
                raw.raise_for_status()
                with output_path.open("wb") as fh:
                    for chunk in raw.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
                return MediaAsset(
                    provider=self.name,
                    local_path=output_path,
                    source_url=url,
                    license_name="Pexels License",
                    attribution_required=False,
                    media_type="video",
                )
            except Exception:
                return None

        assets: list[MediaAsset] = []
        with ThreadPoolExecutor(max_workers=min(len(candidates), 5)) as pool:
            futures = {pool.submit(_download, idx, url): idx for idx, url in candidates}
            results: dict[int, MediaAsset] = {}
            for future in as_completed(futures):
                idx = futures[future]
                asset = future.result()
                if asset:
                    results[idx] = asset

        # Return in original search-result order
        for idx, _ in candidates:
            if idx in results:
                assets.append(results[idx])

        return assets

    @staticmethod
    def _pick_file(files: list[dict]) -> str | None:
        """Pick best portrait file: prefer hd quality, then highest available."""
        portrait = [f for f in files if f.get("width", 9999) < f.get("height", 0)]
        if not portrait:
            portrait = files
        # prefer quality="hd" or "sd", avoid "uhd" (too large)
        preferred = [f for f in portrait if f.get("quality") in ("hd", "sd")]
        chosen = preferred or portrait
        chosen_sorted = sorted(chosen, key=lambda f: f.get("height", 0), reverse=True)
        return chosen_sorted[0].get("link") if chosen_sorted else None
