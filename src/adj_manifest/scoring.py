from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class CalibrationScore:
    value: float
    sample_size: int
    staleness: timedelta


@dataclass(frozen=True)
class ScoringPair:
    confidence: float
    outcome: float
    timestamp: datetime


class BrierScorer:
    @staticmethod
    def compute(pairs: list[ScoringPair], now: datetime) -> CalibrationScore:
        if not pairs:
            return BrierScorer.get_default()

        brier_sum = 0.0
        most_recent = datetime.min
        for p in pairs:
            diff = p.confidence - p.outcome
            brier_sum += diff * diff
            if p.timestamp > most_recent:
                most_recent = p.timestamp

        brier = brier_sum / len(pairs)
        staleness = now - most_recent if now > most_recent else timedelta(0)

        return CalibrationScore(
            value=max(0.0, min(1.0, 1.0 - brier)),
            sample_size=len(pairs),
            staleness=staleness,
        )

    @staticmethod
    def update(prior: CalibrationScore, new_pair: ScoringPair, now: datetime) -> CalibrationScore:
        prior_brier = 1.0 - prior.value
        diff = new_pair.confidence - new_pair.outcome
        new_contribution = diff * diff
        new_n = prior.sample_size + 1
        new_brier = (prior.sample_size * prior_brier + new_contribution) / new_n
        staleness = now - new_pair.timestamp if now > new_pair.timestamp else timedelta(0)

        return CalibrationScore(
            value=max(0.0, min(1.0, 1.0 - new_brier)),
            sample_size=new_n,
            staleness=staleness,
        )

    @staticmethod
    def get_default() -> CalibrationScore:
        return CalibrationScore(value=0.5, sample_size=0, staleness=timedelta(0))
