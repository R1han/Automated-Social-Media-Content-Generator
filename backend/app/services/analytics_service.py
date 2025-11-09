"""Lightweight analytics heuristics for demo reporting."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsPayload:
    expected_ctr: float
    retention_score: float
    narrative_complexity: float

    def as_dict(self) -> dict[str, float]:
        return {
            "expected_ctr": self.expected_ctr,
            "retention_score": self.retention_score,
            "narrative_complexity": self.narrative_complexity,
        }


class AnalyticsService:
    """Computes proxy engagement metrics based on narrative properties."""

    def evaluate(self, script: str, caption: str) -> AnalyticsPayload:
        script_words = len(script.split())
        caption_words = len(caption.split())
        total_words = script_words + caption_words
        reading_time = total_words / 150 if total_words else 0.5

        expected_ctr = min(0.25, 0.08 + 0.0005 * max(caption_words - 60, 0))
        retention_score = max(0.6, min(0.95, 0.7 + 0.02 * math.log(max(script_words, 30), 10)))
        narrative_complexity = min(1.0, (script_words / max(reading_time, 0.5)) / 250)

        logger.debug(
            "Analytics computed",
            extra={
                "expected_ctr": expected_ctr,
                "retention_score": retention_score,
                "narrative_complexity": narrative_complexity,
            },
        )

        return AnalyticsPayload(
            expected_ctr=round(expected_ctr, 3),
            retention_score=round(retention_score, 3),
            narrative_complexity=round(narrative_complexity, 3),
        )
