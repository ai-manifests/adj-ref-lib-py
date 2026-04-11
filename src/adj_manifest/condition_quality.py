from __future__ import annotations
from dataclasses import dataclass
from .entries import ConditionRecord


@dataclass(frozen=True)
class ConditionQualityMetrics:
    falsification_ratio: float
    amendment_frequency: float
    conditions_published: int
    conditions_tested: int
    total_amendments: int


class ConditionQualityScorer:
    @staticmethod
    def compute(conditions: list[ConditionRecord]) -> ConditionQualityMetrics:
        if not conditions:
            return ConditionQualityMetrics(0, 0, 0, 0, 0)

        tested = sum(1 for c in conditions if c.tested_in_round is not None)
        amendments = sum(c.amendment_count for c in conditions)

        return ConditionQualityMetrics(
            falsification_ratio=tested / len(conditions),
            amendment_frequency=amendments / len(conditions),
            conditions_published=len(conditions),
            conditions_tested=tested,
            total_amendments=amendments,
        )
