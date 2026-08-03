# Experiment Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-09` |
| Requirement prefix | `EXP` |
| Status | Normative subsystem specification |

## 1. Purpose

An Experiment is an objective, reproducible test designed to reduce uncertainty about one Hypothesis Version. The AI Researcher requests the test; Sentinel validates, executes, and records it.

## 2. Responsibilities

The Experiment subsystem owns protocol validation, data partitioning, execution, reproducibility, metrics, diagnostics, costs, robustness checks, artifacts, and immutable Results. It does not author Hypotheses, interpret market meaning, or promote strategies.

## 3. Experiment Types

Supported logical types include:

- exploratory analysis;
- initial backtest;
- independent unseen-period validation;
- walk-forward evaluation;
- cross-symbol, sector, market, or regime validation;
- sensitivity and perturbation analysis;
- placebo or null test;
- reproduction;
- paper-trading evaluation;
- revalidation or degradation check.

**EXP-001:** Every Experiment MUST declare its type and data-partition role.

## 4. Experiment Request

An accepted request must specify:

- Request and Hypothesis Version identifiers;
- research question and expected information gain;
- universe, sampling frequency, and period;
- as-of and point-in-time rules;
- feature and data versions;
- signal, entry, exit, invalidation, and holding semantics where applicable;
- benchmark or null;
- metrics, uncertainty method, and acceptance criteria;
- transaction fees, spread, slippage, borrow, funding, latency, liquidity, and capacity assumptions as relevant;
- sample partition and embargo rules;
- robustness checks;
- resource budget and reproducibility requirements.

**EXP-002:** A Request MUST be schema-valid and internally consistent before execution.

**EXP-003:** Confirmatory acceptance criteria SHOULD be frozen before results are visible.

**EXP-004:** A Request MUST NOT designate evidence used in hypothesis formation as unseen validation data.

## 5. Data Integrity

Experiments simulate what could have been known at the historical decision time.

**EXP-005:** Future data MUST NOT influence past features, universe membership, signals, decisions, or parameters.

**EXP-006:** Corporate actions, revisions, survivorship, delistings, publication delay, market calendars, and missing data MUST be handled explicitly.

**EXP-007:** Discovery, tuning, test, and validation samples MUST have machine-readable boundaries.

**EXP-008:** Repeated access to a held-out sample MUST be recorded and may invalidate its independent status.

## 6. Strategy Simulation

Where an Experiment simulates trading, it must define position state, order timing, fills, partial fills where modeled, exposure, overlapping signals, cash, leverage, fees, and exits.

**EXP-009:** Signal calculation and simulated execution MUST respect event ordering.

**EXP-010:** Same-bar execution MUST be prohibited unless the required information was available before the assumed fill and the convention is documented.

**EXP-011:** Results MUST include gross and net performance.

**EXP-012:** Cost-free results MUST NOT be used for promotion when material costs exist.

## 7. Metrics

Metrics are selected according to objective and strategy but should cover:

- sample and trade count;
- total and annualized return where meaningful;
- win rate;
- average and median profit and loss;
- expectancy and payoff ratio;
- volatility and risk-adjusted return;
- maximum drawdown and recovery;
- turnover, exposure, capacity, and concentration;
- tail behavior and worst outcomes;
- benchmark-relative performance;
- uncertainty intervals and statistical significance where appropriate;
- stability across periods, parameters, and regimes.

**EXP-013:** No single headline metric MAY determine scientific validity in isolation.

**EXP-014:** Every reported metric MUST identify sample, period, costs, and calculation version.

**EXP-015:** Small samples MUST be labeled and MUST NOT support overstated confidence.

## 8. Multiple Testing and Overfitting

Sentinel records Experiment families, parameter searches, failed variants, and repeated tests so the apparent evidence can be adjusted for research effort.

**EXP-016:** Parameter searches MUST record the searched space and selection rule.

**EXP-017:** Related Hypothesis and Experiment variants MUST be grouped for multiple-testing analysis.

**EXP-018:** The best observed variant MUST NOT be presented as though it were selected in advance.

## 9. Execution and Reproducibility

An Experiment Run records code revision, environment, dependencies, inputs, configuration, seed, hardware-sensitive details where relevant, start/end time, logs, and artifact hashes.

**EXP-019:** Identical reproducible Runs SHOULD yield results within defined deterministic tolerance.

**EXP-020:** A retry MUST create a new Run linked to the same Request.

**EXP-021:** Runtime failure, timeout, cancellation, and invalid result MUST be distinct states.

**EXP-022:** Execution MUST be idempotent with respect to accidental duplicate dispatch or detect and link the duplicate.

## 10. Result

The immutable Result contains metrics, diagnostics, warnings, protocol deviations, robustness outcomes, trade/sample detail references, and an objective gate-evaluation input package.

**EXP-023:** Results MUST include adverse and failed checks, not only passing outputs.

**EXP-024:** Results MUST distinguish “strategy failed” from “Experiment could not validly answer the question.”

**EXP-025:** The Experiment service MUST NOT write an AI-style research conclusion into the authoritative Result.

## 11. Independent Validation

The established default validation uses a distinct six-month period after a successful initial test. The exact window may be configured when justified.

**EXP-026:** Validation MUST use the frozen candidate version and protocol unless a deviation causes the result to lose independent status.

**EXP-027:** Retuning after viewing validation creates a new candidate requiring new independent evidence.

## 12. Generalization

Cross-market or regime validation is required when the claim extends beyond one Instrument or regime. A symbol-specific finding may remain symbol-specific if its limitation is explicit.

**EXP-028:** Failure to generalize MUST narrow the claim or block promotion under a broader claim.

## 13. Lifecycle

```text
proposed -> accepted | rejected
accepted -> queued -> running
running -> completed | failed | cancelled | timed_out
completed -> valid | invalidated_by_protocol
```

Results and failures remain immutable.

## 14. Security and Isolation

Experiment code and data access operate with least privilege, bounded resources, and isolated credentials. Generated code or AI-authored specifications are untrusted until validated.

**EXP-029:** Experiments MUST NOT obtain broker live-order credentials.

**EXP-030:** Resource limits and allowed data scopes MUST be enforced outside AI control.

## 15. Acceptance Criteria

Conformance requires tests for leakage prevention, partition independence, cost application, event ordering, deterministic replay, retry history, malformed Requests, partial failure, multiple-testing metadata, and Result immutability.

## 16. Future Extensions

Future work may add distributed workers, causal experiments, synthetic markets, richer market-impact models, formal experiment preregistration, and independent reproduction agents.

## 17. Out of Scope

The subsystem does not decide which Hypothesis deserves attention, interpret results, create Trade Plans, authorize promotion, or execute live orders.
