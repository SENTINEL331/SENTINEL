# Hypothesis Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-08` |
| Requirement prefix | `HYP` |
| Status | Normative subsystem specification |

## 1. Purpose

A Hypothesis is a durable, falsifiable research proposition authored and maintained by the AI Researcher. It states a proposed market relationship worthy of investigation. It is neither an Observation nor a Trade Plan.

## 2. Responsibilities

The Hypothesis subsystem preserves identity and version history, enforces the active-capacity limit, links evidence and competing explanations, records confidence changes, and coordinates Experiment Requests and promotion state.

## 3. Ownership

- The AI Researcher owns the claim, reasoning, refinement, confidence assessment, and recommendation.
- Sentinel validates structure, evidence links, capacity, state transitions, and storage.
- Experiment services own test results.
- Promotion policy owns gate enforcement.

**HYP-001:** Sentinel MUST NOT rewrite a Hypothesis on the AI Researcher's behalf.

**HYP-002:** The AI Researcher MUST NOT alter authoritative Experiment Results to support a Hypothesis.

## 4. Hypothesis Identity and Versions

A stable Hypothesis identity represents the continuing research question. Each accepted refinement creates an immutable Hypothesis Version.

Required identity fields include:

- `hypothesis_id`;
- Research Objective and Instrument/universe scope;
- creation actor and time;
- current version;
- scientific status and promotion stage;
- active-capacity status;
- family, predecessor, successor, and competing-hypothesis links.

Required version fields include:

- version number and predecessor;
- precise claim;
- proposed mechanism or predictive relationship;
- expected direction and effect;
- universe, regime, frequency, and holding horizon;
- supporting and opposing evidence;
- assumptions and limitations;
- falsification and invalidation conditions;
- confidence with rationale;
- proposed Experiment design;
- change reason and AI-call reference.

**HYP-003:** Accepted versions MUST be immutable.

**HYP-004:** A material change to claim, scope, signal, horizon, or falsification condition MUST create a new version.

**HYP-005:** Results from an earlier version MUST NOT be attributed to a later version without an explicit applicability decision.

## 5. Quality Standard

A valid Hypothesis must be specific enough to test and broad enough to have research meaning. It must answer:

1. What relationship is claimed?
2. For which instruments, regimes, and times?
3. Why might it exist?
4. What direction or effect is expected?
5. What evidence currently supports or opposes it?
6. What result would weaken or falsify it?
7. What experiment would reduce uncertainty?

**HYP-006:** A Hypothesis MUST be falsifiable.

**HYP-007:** A Hypothesis MUST NOT be a disguised order instruction.

**HYP-008:** A Hypothesis MUST NOT claim guaranteed profit.

**HYP-009:** Proposed mechanisms MUST be labeled as explanatory reasoning, not stored fact.

## 6. Capacity and Portfolio Management

The default policy allows no more than six active Hypotheses per watched symbol. Six is a ceiling, not a daily generation goal. A symbol may have zero to six active Hypotheses and unlimited inactive historical Hypotheses subject to retention policy.

**HYP-010:** The Researcher MUST review the existing portfolio before proposing a new Hypothesis.

**HYP-011:** Sentinel MUST reject activation above the configured capacity unless an authorized policy exception exists.

**HYP-012:** A new Hypothesis MUST add a materially distinct testable idea.

**HYP-013:** Capacity status MUST NOT delete or conceal inactive research.

## 7. Competition and Families

Hypotheses may be mutually supportive, competing, nested, or variants within one research family. For example, trend continuation and mean reversion may compete to explain the same conditions.

**HYP-014:** Related variants MUST share a family identifier for multiple-testing and comparison purposes.

**HYP-015:** Evidence favoring one competitor MUST be evaluated for its implications for the others.

**HYP-016:** Competition MUST NOT be resolved by confidence labels alone; relevant evidence and Experiments decide.

## 8. Confidence

Confidence represents the current strength of the research case under defined semantics. It is distinct from promotion stage and predicted win probability.

**HYP-017:** Confidence MUST change only when cited evidence, Results, assumptions, or scope change.

**HYP-018:** Confidence MUST include concise rationale and contrary evidence.

**HYP-019:** Repetition or AI agreement MUST NOT count as independent confirmation.

**HYP-020:** Confidence MUST NOT substitute for mandatory promotion gates.

## 9. Scientific Lifecycle

```text
proposed
  -> active
  -> supported | contradicted | blocked
  -> active (refined version)
  -> inactive | superseded
```

Scientific status and promotion stage are orthogonal. An active Hypothesis may be awaiting its first Experiment or may support a Paper Trade. A contradicted Hypothesis remains historically inspectable.

**HYP-021:** Ordinary lifecycle behavior MUST NOT include hard deletion.

**HYP-022:** Making a Hypothesis inactive or superseded MUST record the reason and actor.

**HYP-023:** New evidence MAY reactivate an inactive Hypothesis through an explicit event and current version review.

## 10. Experiment Interaction

Each Experiment Request tests one identified Hypothesis Version. The Researcher may request multiple complementary Experiments, but repeated variants must remain visible as one research family.

**HYP-024:** A Hypothesis MUST NOT be promoted without stored, reproducible Experiment Results.

**HYP-025:** Failed, inconclusive, and operationally invalid Experiments MUST remain linked.

**HYP-026:** Retesting after refinement MUST identify whether prior evidence remains applicable.

## 11. Promotion Interaction

Promotion follows initial backtest, independent unseen-period validation, applicable generalization challenge, Paper Trading, and validated-opportunity review. A Hypothesis does not become a Trade Plan; it supports creation of one.

**HYP-027:** Promotion stage MUST be derived from immutable Promotion Decisions.

**HYP-028:** Passing a stage MUST NOT automatically raise scientific confidence without Researcher interpretation.

**HYP-029:** Gate failure MUST update research context but MUST NOT erase the Hypothesis.

## 12. Storage and Queries

The store must query by identifier, symbol/universe, status, capacity, family, version, evidence, Experiment, promotion stage, and effective date. Historical reconstruction must show what the Researcher knew at any cycle.

**HYP-030:** The complete version and lifecycle history MUST survive process restart.

## 13. Acceptance Criteria

Conformance requires tests for capacity enforcement, immutable versions, evidence linkage, duplicate-family handling, confidence audit, concurrent update conflict, lifecycle reconstruction, inactive re-entry, and retention of failed research.

## 14. Future Extensions

Future versions may support portfolio-level Hypotheses, causal graphs, formal priors/posteriors, independent AI critics, automated clustering, and cross-symbol capacity allocation.

## 15. Out of Scope

This subsystem does not calculate features, execute Experiments, decide objective gate outcomes, create orders, or own trade performance.
