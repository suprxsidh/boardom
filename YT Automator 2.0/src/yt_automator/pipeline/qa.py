from __future__ import annotations

from yt_automator.models import ContentPackage
from yt_automator.utils.text import word_count


class QualityGate:
    def __init__(self, min_words: int = 75, max_words: int = 185):
        self.min_words = min_words
        self.max_words = max_words

    def validate_content(self, package: ContentPackage) -> tuple[bool, list[str]]:
        issues: list[str] = []
        count = word_count(package.script)
        if count < self.min_words:
            issues.append(f"Script too short ({count} words), likely <30s spoken")
        if count > self.max_words:
            issues.append(f"Script too long ({count} words), likely >60s spoken")
        if len(package.title) > 90:
            issues.append("Title too long (keep under 90 chars)")
        if not package.tags:
            issues.append("Missing tags")
        return (len(issues) == 0, issues)
