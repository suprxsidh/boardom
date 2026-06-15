from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ArmStat:
    pulls: int
    reward_sum: float

    @property
    def average_reward(self) -> float:
        if self.pulls == 0:
            return 0.0
        return self.reward_sum / self.pulls


class BanditOptimizer:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def pick_arm(self, channel: str, candidate_arms: list[str], epsilon: float) -> str:
        if not candidate_arms:
            raise ValueError("No candidate arms available")
        bucket = self.state.setdefault(channel, {})
        for arm in candidate_arms:
            bucket.setdefault(arm, {"pulls": 0, "reward_sum": 0.0})
        if random.random() < epsilon:
            chosen = random.choice(candidate_arms)
            self._save()
            return chosen
        chosen = max(
            candidate_arms,
            key=lambda arm: self._arm_stat(bucket, arm).average_reward,
        )
        self._save()
        return chosen

    def record_reward(self, channel: str, arm: str, reward: float) -> None:
        bucket = self.state.setdefault(channel, {})
        arm_data = bucket.setdefault(arm, {"pulls": 0, "reward_sum": 0.0})
        arm_data["pulls"] += 1
        arm_data["reward_sum"] += float(reward)
        self._save()

    def _arm_stat(self, bucket: dict, arm: str) -> ArmStat:
        data = bucket.get(arm, {"pulls": 0, "reward_sum": 0.0})
        return ArmStat(pulls=int(data["pulls"]), reward_sum=float(data["reward_sum"]))

    def _load(self) -> dict:
        if not self.storage_path.exists():
            return {}
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        self.storage_path.write_text(
            json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8"
        )
