from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EntryType(Enum):
    DELIBERATION_OPENED = "deliberation_opened"
    PROPOSAL_EMITTED = "proposal_emitted"
    ROUND_EVENT = "round_event"
    DELIBERATION_CLOSED = "deliberation_closed"
    OUTCOME_OBSERVED = "outcome_observed"


class EventKind(Enum):
    FALSIFICATION_EVIDENCE = "falsification_evidence"
    ACKNOWLEDGE = "acknowledge"
    REJECT = "reject"
    AMEND = "amend"
    REVISE = "revise"
    CHALLENGE_TIER = "challenge_tier"
    TIER_RESPONSE = "tier_response"
    TIMEOUT = "timeout"


class TerminationState(Enum):
    CONVERGED = "converged"
    PARTIAL_COMMIT = "partial_commit"
    DEADLOCKED = "deadlocked"


class OutcomeClass(Enum):
    BINARY = "binary"
    GRADED = "graded"


@dataclass(frozen=True)
class ActionDescriptor:
    kind: str
    target: str
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DeliberationConfig:
    max_rounds: int = 3
    participation_floor: float = 0.50


@dataclass(frozen=True)
class TallyRecord:
    approve_weight: float
    reject_weight: float
    abstain_weight: float
    total_weight: float
    approval_fraction: float
    participation_fraction: float
    threshold: float


@dataclass(frozen=True)
class ConditionRecord:
    id: str
    condition: str
    status: str
    amendment_count: int
    tested_in_round: int | None = None


@dataclass(frozen=True)
class ProposalData:
    proposal_id: str
    agent_id: str
    vote: str
    confidence: float
    domain: str
    calibration_at_stake: bool
    dissent_conditions: tuple[ConditionRecord, ...] = ()


@dataclass(frozen=True)
class JournalEntry:
    entry_id: str
    entry_type: EntryType
    deliberation_id: str
    timestamp: datetime
    prior_entry_hash: str | None = None


@dataclass(frozen=True)
class DeliberationOpened(JournalEntry):
    decision_class: str = ""
    action: ActionDescriptor | None = None
    participants: tuple[str, ...] = ()
    config: DeliberationConfig | None = None

    def __post_init__(self):
        object.__setattr__(self, 'entry_type', EntryType.DELIBERATION_OPENED)


@dataclass(frozen=True)
class ProposalEmitted(JournalEntry):
    proposal: ProposalData | None = None

    def __post_init__(self):
        object.__setattr__(self, 'entry_type', EntryType.PROPOSAL_EMITTED)


@dataclass(frozen=True)
class RoundEvent(JournalEntry):
    round: int = 0
    event_kind: EventKind = EventKind.TIMEOUT
    agent_id: str = ""
    target_agent_id: str | None = None
    target_condition_id: str | None = None
    payload: dict | None = None

    def __post_init__(self):
        object.__setattr__(self, 'entry_type', EntryType.ROUND_EVENT)


@dataclass(frozen=True)
class DeliberationClosed(JournalEntry):
    termination: TerminationState = TerminationState.DEADLOCKED
    round_count: int = 0
    tier: str = ""
    final_tally: TallyRecord | None = None
    weights: dict[str, float] = field(default_factory=dict)
    committed_action: ActionDescriptor | None = None

    def __post_init__(self):
        object.__setattr__(self, 'entry_type', EntryType.DELIBERATION_CLOSED)


@dataclass(frozen=True)
class OutcomeObserved(JournalEntry):
    observed_at: datetime | None = None
    outcome_class: OutcomeClass = OutcomeClass.BINARY
    success: float = 0.0
    evidence_refs: tuple[str, ...] = ()
    reporter_id: str = ""
    reporter_confidence: float = 0.0
    ground_truth: bool = False
    supersedes: str | None = None

    @property
    def outcome_value(self) -> float:
        return self.success

    def __post_init__(self):
        object.__setattr__(self, 'entry_type', EntryType.OUTCOME_OBSERVED)
