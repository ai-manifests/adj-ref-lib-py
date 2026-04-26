# adj-manifest

[![PyPI](https://img.shields.io/pypi/v/adj-manifest.svg?label=PyPI)](https://pypi.org/project/adj-manifest/)
[![Downloads](https://img.shields.io/pypi/dm/adj-manifest.svg)](https://pypi.org/project/adj-manifest/)
[![Python](https://img.shields.io/pypi/pyversions/adj-manifest.svg)](https://pypi.org/project/adj-manifest/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Spec](https://img.shields.io/badge/spec-adj--manifest.dev-informational)](https://adj-manifest.dev)

A Python reference implementation of the **Agent Deliberation Journal (ADJ)** specification — the append-only journal format that records every step of a multi-agent deliberation: when it opened, what proposals were emitted, what falsifications happened, when it closed, and what outcome was eventually observed.

This library is one of several reference implementations ([C#](https://github.com/ai-manifests/adj-ref-lib-csharp), [TypeScript](https://github.com/ai-manifests/adj-ref-lib-ts)) of the same spec. The spec itself is at [adp-manifest.dev](https://adp-manifest.dev) and is the source of truth; this library implements what the spec says.

Zero runtime dependencies. Requires Python 3.10+.

## Install

```bash
pip install adj-manifest
```

Or from source:

```bash
git clone https://github.com/ai-manifests/adj-ref-lib-py.git
cd adj-ref-lib-py
pip install -e .
```

## Quick example

```python
from datetime import datetime, timezone
from adj_manifest import (
    InMemoryJournalStore,
    DeliberationOpened,
    ActionDescriptor,
    DeliberationConfig,
    BrierScorer,
)

store = InMemoryJournalStore()

store.append(DeliberationOpened(
    entry_id="adj_01HMX",
    deliberation_id="dlb_42",
    timestamp=datetime.now(timezone.utc),
    prior_entry_hash=None,
    action=ActionDescriptor(kind="code.merge", tier="auto", blast_radius="team-scope"),
    config=DeliberationConfig(min_agents=3, timeout_seconds=300),
))

# ... append proposals, round events, deliberation close, outcome ...

score = BrierScorer.compute_calibration(scoring_pairs)
# score.value is the Brier-scored calibration score in [0, 1]
```

## API

All public symbols are exported from the `adj_manifest` package root.

### Entry types

`JournalEntry`, `DeliberationOpened`, `ProposalEmitted`, `RoundEvent`, `DeliberationClosed`, `OutcomeObserved`

### Value types

`ActionDescriptor`, `DeliberationConfig`, `TallyRecord`, `ProposalData`, `ConditionRecord`, `CalibrationScore`, `ScoringPair`, `ConditionQualityMetrics`

### Scorers

- `BrierScorer` — `compute_calibration(pairs)` returns a calibration score from `(confidence, outcome)` pairs. `update(score, pair)` folds a new observation into an existing score.
- `ConditionQualityScorer` — `compute(entries)` returns per-condition quality metrics (how often each dissent condition was falsified, how often it was load-bearing, etc.)

### Store

- `InMemoryJournalStore` — thread-safe in-memory journal store suitable for tests and prototypes. Implements the store contract from the spec.

## Testing

```bash
pip install -e .[dev]
pytest
```

## Spec

This library implements the Agent Deliberation Journal specification. Read the spec at [adp-manifest.dev](https://adp-manifest.dev). If the spec and this library disagree, the spec is correct and this is a bug.

## License

Apache-2.0 — see [`LICENSE`](LICENSE) for the full license text and [`NOTICE`](NOTICE) for attribution.
