from __future__ import annotations

import json
import logging
from pathlib import Path

from yt_automator.optimizer.bandit_optimizer import BanditOptimizer

_log = logging.getLogger(__name__)


def compute_reward(analytics_response: dict, target_views: int = 1000) -> float:
    rows = analytics_response.get("rows", [])
    if not rows:
        return 0.0

    # columns: video, averageViewDuration, averageViewPercentage, views, likes, comments
    row = rows[0]
    try:
        avg_view_pct = float(row[2]) if len(row) > 2 else 0.0
        views = float(row[3]) if len(row) > 3 else 0.0
        likes = float(row[4]) if len(row) > 4 else 0.0
    except (TypeError, ValueError):
        return 0.0

    def clip(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    reward = (
        0.5 * (avg_view_pct / 100.0)
        + 0.3 * clip(views / max(target_views, 1), 0.0, 1.0)
        + 0.2 * clip(likes / max(views, 1.0), 0.0, 1.0)
    )
    return round(reward, 4)


class RewardCalculator:
    def __init__(self, repo_root: Path, optimizer: BanditOptimizer):
        self.repo_root = repo_root
        self.channels_dir = repo_root / "channels"
        self.optimizer = optimizer
        self._run_index: dict[str, dict] | None = None

    def process_all_collected(self) -> None:
        for analytics_path in sorted(self.channels_dir.glob("*/analytics/*.json")):
            channel = analytics_path.parent.parent.name
            try:
                self._process_file(channel, analytics_path)
            except Exception as exc:
                _log.warning("[%s] Failed to process %s: %s", channel, analytics_path.name, exc)

    def _process_file(self, channel: str, analytics_path: Path) -> None:
        data = json.loads(analytics_path.read_text(encoding="utf-8"))
        analytics_response = data.get("analytics", {})
        record = data.get("record", {})

        style_variant = record.get("style_variant")
        if not style_variant:
            _log.debug("No style_variant in %s — skipping reward", analytics_path.name)
            return

        reward = compute_reward(analytics_response)
        if reward == 0.0 and not analytics_response.get("rows"):
            _log.debug("[%s] No analytics data for %s yet", channel, analytics_path.stem)
            return

        self.optimizer.record_reward(channel, style_variant, reward)
        _log.info(
            "[%s] Reward %.4f recorded for strategy '%s' (video %s)",
            channel, reward, style_variant, analytics_path.stem,
        )
