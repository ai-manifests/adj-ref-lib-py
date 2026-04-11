"""ADJ spec Section 9 worked example — PR merge journal lifecycle."""
from datetime import datetime, timedelta
from adj_manifest import (
    DeliberationOpened, ProposalEmitted, RoundEvent, DeliberationClosed,
    OutcomeObserved, ActionDescriptor, DeliberationConfig, TallyRecord,
    ProposalData, ConditionRecord, CalibrationScore, ScoringPair,
    BrierScorer, ConditionQualityScorer, InMemoryJournalStore,
)
from adj_manifest.entries import EntryType, EventKind, TerminationState, OutcomeClass

DLB = "dlb_01HMXJ3E9R"
TEST_RUNNER = "did:adp:test-runner-v2"
SCANNER = "did:adp:security-scanner-v3"
LINTER = "did:adp:style-linter-v1"
T0 = datetime(2026, 4, 11, 14, 32, 0)
T_OUTCOME = datetime(2026, 4, 14, 9, 12, 0)
ACTION = ActionDescriptor("merge_pull_request", "github.com/acme/api#4471", {"strategy": "squash"})


def _build_journal() -> InMemoryJournalStore:
    store = InMemoryJournalStore()
    store.append(DeliberationOpened("adj_01", EntryType.DELIBERATION_OPENED, DLB, T0, None,
        "code.correctness", ACTION, (TEST_RUNNER, SCANNER, LINTER), DeliberationConfig()))
    store.append(ProposalEmitted("adj_02", EntryType.PROPOSAL_EMITTED, DLB, T0 + timedelta(seconds=9), None,
        ProposalData("prp_01", TEST_RUNNER, "approve", 0.86, "code.correctness", True,
            (ConditionRecord("dc_tr_01", "if any test marked critical regresses", "active", 0),
             ConditionRecord("dc_tr_02", "if coverage delta is negative", "active", 0)))))
    store.append(ProposalEmitted("adj_03", EntryType.PROPOSAL_EMITTED, DLB, T0 + timedelta(seconds=11), None,
        ProposalData("prp_02", SCANNER, "reject", 0.79, "security.policy", True,
            (ConditionRecord("dc_ss_01", "if any code path in auth module remains untested", "active", 0),
             ConditionRecord("dc_ss_02", "if no security-focused test covers token validation", "active", 0)))))
    store.append(ProposalEmitted("adj_04", EntryType.PROPOSAL_EMITTED, DLB, T0 + timedelta(seconds=12), None,
        ProposalData("prp_03", LINTER, "approve", 0.62, "code.style", True,
            (ConditionRecord("dc_sl_01", "if any public API name violates naming convention", "active", 0),))))
    for i, (eid, ek, aid, taid, tcid) in enumerate([
        ("adj_05", EventKind.FALSIFICATION_EVIDENCE, TEST_RUNNER, SCANNER, "dc_ss_01"),
        ("adj_06", EventKind.FALSIFICATION_EVIDENCE, TEST_RUNNER, SCANNER, "dc_ss_02"),
        ("adj_07", EventKind.ACKNOWLEDGE, SCANNER, None, "dc_ss_01"),
        ("adj_08", EventKind.ACKNOWLEDGE, SCANNER, None, "dc_ss_02"),
        ("adj_09", EventKind.REVISE, SCANNER, None, None),
    ]):
        store.append(RoundEvent(eid, EntryType.ROUND_EVENT, DLB,
            T0 + timedelta(seconds=135 + i), None, 1, ek, aid, taid, tcid))
    store.append(DeliberationClosed("adj_10", EntryType.DELIBERATION_CLOSED, DLB,
        T0 + timedelta(seconds=210), None, TerminationState.CONVERGED, 1, "partially_reversible",
        TallyRecord(0.89, 0.00, 0.64, 1.53, 1.00, 0.582, 0.60),
        {TEST_RUNNER: 0.71, SCANNER: 0.64, LINTER: 0.18}, ACTION))
    return store


def test_full_deliberation_has_10_entries():
    store = _build_journal()
    assert len(store.get_deliberation(DLB)) == 10


def test_no_outcome_before_recording():
    store = _build_journal()
    assert store.get_outcome(DLB) is None


def test_calibration_returns_bootstrap_before_outcome():
    store = _build_journal()
    cal = store.get_calibration(TEST_RUNNER, "code.correctness")
    assert cal.value == 0.5
    assert cal.sample_size == 0


def test_outcome_recorded_and_retrievable():
    store = _build_journal()
    store.append(OutcomeObserved("adj_11", EntryType.OUTCOME_OBSERVED, DLB,
        T_OUTCOME + timedelta(minutes=3), None, T_OUTCOME, OutcomeClass.BINARY,
        1.0, ("ci:github-actions/run/8835001",), "did:adp:ci-monitor-v1", 0.95, True))
    outcome = store.get_outcome(DLB)
    assert outcome is not None
    assert outcome.outcome_value == 1.0
    assert outcome.ground_truth is True


def test_calibration_updates_after_outcome():
    store = _build_journal()
    store.append(OutcomeObserved("adj_11", EntryType.OUTCOME_OBSERVED, DLB,
        T_OUTCOME + timedelta(minutes=3), None, T_OUTCOME, OutcomeClass.BINARY,
        1.0, (), "did:adp:ci-monitor-v1", 0.95, True))

    tr_cal = store.get_calibration(TEST_RUNNER, "code.correctness")
    assert tr_cal.sample_size == 1
    assert 0.97 <= tr_cal.value <= 0.99  # 1 - (0.86-1)^2 = 0.9804

    sc_cal = store.get_calibration(SCANNER, "security.policy")
    assert sc_cal.sample_size == 1
    assert 0.95 <= sc_cal.value <= 0.97  # 1 - (0.79-1)^2 = 0.9559

    lt_cal = store.get_calibration(LINTER, "code.style")
    assert lt_cal.sample_size == 1
    assert 0.84 <= lt_cal.value <= 0.87  # 1 - (0.62-1)^2 = 0.8556


def test_incremental_brier_matches_spec():
    prior = CalibrationScore(0.85, 312, timedelta(days=18))
    new_pair = ScoringPair(0.86, 1.0, T_OUTCOME)
    updated = BrierScorer.update(prior, new_pair, T_OUTCOME)
    assert updated.sample_size == 313
    assert 0.849 <= updated.value <= 0.852


def test_condition_quality_tracks_falsification():
    conditions = [
        ConditionRecord("dc_ss_01", "...", "falsified", 0, 1),
        ConditionRecord("dc_ss_02", "...", "falsified", 0, 1),
    ]
    metrics = ConditionQualityScorer.compute(conditions)
    assert metrics.falsification_ratio == 1.0
    assert metrics.conditions_tested == 2


def test_condition_quality_detects_untestable():
    conditions = [
        ConditionRecord(f"dc_{i:02}", f"cond {i}", "falsified" if i < 2 else "active", 0, 1 if i < 2 else None)
        for i in range(10)
    ]
    metrics = ConditionQualityScorer.compute(conditions)
    assert metrics.falsification_ratio == 0.2
    assert metrics.conditions_tested == 2


def test_bootstrap_agent_gets_default():
    store = InMemoryJournalStore()
    cal = store.get_calibration("did:adp:new-agent", "code.correctness")
    assert cal.value == 0.5
    assert cal.sample_size == 0
    assert cal.staleness == timedelta(0)


def test_outcome_supersedes_replaces_prior():
    store = _build_journal()
    store.append(OutcomeObserved("adj_11", EntryType.OUTCOME_OBSERVED, DLB,
        T_OUTCOME + timedelta(minutes=3), None, T_OUTCOME, OutcomeClass.BINARY,
        1.0, (), "did:adp:ci-monitor-v1", 0.95, True))
    store.append(OutcomeObserved("adj_12", EntryType.OUTCOME_OBSERVED, DLB,
        T_OUTCOME + timedelta(days=1), None, T_OUTCOME + timedelta(hours=6),
        OutcomeClass.BINARY, 0.0, ("incident:pagerduty/INC-8823",),
        "did:adp:incident-monitor-v1", 0.99, True, "adj_11"))

    outcome = store.get_outcome(DLB)
    assert outcome is not None
    assert outcome.outcome_value == 0.0

    tr_cal = store.get_calibration(TEST_RUNNER, "code.correctness")
    assert 0.25 <= tr_cal.value <= 0.27  # 1 - (0.86-0)^2 = 0.2604
