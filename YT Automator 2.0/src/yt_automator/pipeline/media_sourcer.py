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
