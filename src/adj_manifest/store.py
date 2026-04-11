from __future__ import annotations
from datetime import datetime, timedelta
from .entries import (
    JournalEntry, ProposalEmitted, OutcomeObserved, ConditionRecord,
)
from .scoring import CalibrationScore, ScoringPair, BrierScorer
from .condition_quality import ConditionQualityMetrics, ConditionQualityScorer


class InMemoryJournalStore:
    """In-memory Level 3 journal store. Append-only, implements query contract."""

    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def append(self, entry: JournalEntry) -> None:
        self._entries.append(entry)

    def append_range(self, entries: list[JournalEntry]) -> None:
        self._entries.extend(entries)

    def get_calibration(self, agent_id: str, domain: str) -> CalibrationScore:
        pairs = self._get_scoring_pairs(agent_id, domain)
        if not pairs:
            return BrierScorer.get_default()
        return BrierScorer.compute(pairs, datetime.utcnow())

    def get_deliberation(self, deliberation_id: str) -> list[JournalEntry]:
        return sorted(
            [e for e in self._entries if e.deliberation_id == deliberation_id],
            key=lambda e: e.timestamp,
        )

    def get_condition_trace(self, agent_id: str, window: timedelta) -> ConditionQualityMetrics:
        cutoff = datetime.utcnow() - window
        conditions: list[ConditionRecord] = []
        for e in self._entries:
            if isinstance(e, ProposalEmitted) and e.proposal and e.proposal.agent_id == agent_id and e.timestamp >= cutoff:
                conditions.extend(e.proposal.dissent_conditions)
        return ConditionQualityScorer.compute(conditions)

    def get_outcome(self, deliberation_id: str) -> OutcomeObserved | None:
        outcomes = [
            e for e in self._entries
            if isinstance(e, OutcomeObserved) and e.deliberation_id == deliberation_id
        ]
        if not outcomes:
            return None
        return max(outcomes, key=lambda o: o.timestamp)

    def get_all_entries(self) -> list[JournalEntry]:
        return list(self._entries)

    def _get_scoring_pairs(self, agent_id: str, domain: str) -> list[ScoringPair]:
        proposals = [
            e for e in self._entries
            if isinstance(e, ProposalEmitted)
            and e.proposal
            and e.proposal.agent_id == agent_id
            and e.proposal.domain == domain
            and e.proposal.calibration_at_stake
        ]

        outcomes: dict[str, OutcomeObserved] = {}
        for e in self._entries:
            if isinstance(e, OutcomeObserved):
                existing = outcomes.get(e.deliberation_id)
                if existing is None or e.timestamp > existing.timestamp:
                    outcomes[e.deliberation_id] = e

        pairs: list[ScoringPair] = []
        for p in proposals:
            outcome = outcomes.get(p.deliberation_id)
            if outcome:
                pairs.append(ScoringPair(
                    confidence=p.proposal.confidence,
                    outcome=outcome.outcome_value,
                    timestamp=outcome.observed_at or outcome.timestamp,
                ))
        return pairs
