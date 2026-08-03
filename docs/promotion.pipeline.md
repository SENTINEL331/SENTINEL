# Promotion Pipeline Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-11` |
| Requirement prefix | `PRM` |
| Status | Normative subsystem specification |

## 1. Purpose

The Promotion Pipeline defines the escalating evidence gates through which a Hypothesis and candidate strategy must pass before becoming a validated trading opportunity and, optionally, live-eligible.

## 2. Governing Rule

Promotion is earned through increasingly independent and operationally realistic evidence. A passed gate grants permission to attempt the next stage; it does not guarantee profit or authorize live capital.

```text
Research Candidate
  -> Initial Backtest
  -> Independent Unseen Validation
  -> Generalization Challenge (when applicable)
  -> Paper Trading
  -> Validated Opportunity
  -> Optional Live Eligibility
  -> Continuous Monitoring
```

**PRM-001:** Mandatory gates MUST NOT be skipped by the AI Researcher, implementation code, or operator convenience.

**PRM-002:** Every gate MUST produce an immutable Promotion Decision.

## 3. Common Gate Contract

Every gate defines:

- eligible input artifact and version;
- required evidence and minimum quality;
- objective pass/fail/indeterminate criteria;
- AI interpretation and recommendation where applicable;
- risk and implementation checks;
- policy version;
- output stage and permitted next actions;
- failure, exception, and override handling.

**PRM-003:** Gate criteria MUST be explicit before evaluation.

**PRM-004:** A result MUST be `pass`, `fail`, `indeterminate`, or `invalid`; absence of failure is not a pass.

**PRM-005:** Overrides MUST NOT relabel failed evidence as passed; they create a separately visible exception decision.

## 4. Gate 0 — Research Candidate

Admission requires an active, falsifiable Hypothesis Version with evidence, scope, assumptions, falsification conditions, and a valid Experiment Request.

**PRM-006:** Narrative plausibility alone MUST NOT admit a candidate.

## 5. Gate 1 — Initial Backtest

Evaluates whether the idea merits independent testing. The original design commonly uses roughly two years of history, but the configured period must fit the strategy and data.

Gate considerations include net risk-adjusted outcome, drawdown, sample size, stability, benchmark comparison, leakage checks, and realistic implementation assumptions.

**PRM-007:** Passing the initial backtest MUST NOT be described as validation.

**PRM-008:** Parameter selection and research-family testing effort MUST accompany the result.

## 6. Gate 2 — Independent Unseen Validation

Evaluates the frozen candidate on data not used for formation or tuning. The established default is a distinct six-month period.

**PRM-009:** Validation data MUST remain unseen until the candidate and criteria are frozen.

**PRM-010:** Retuning after inspection MUST produce a new candidate that requires new independent validation.

**PRM-011:** Repeated reuse of the same validation period MUST reduce or remove its independent status.

## 7. Gate 3 — Generalization Challenge

Tests the claim across other suitable instruments, sectors, markets, regimes, or periods. This gate is mandatory when the claim asserts such generality. A genuinely Instrument-specific claim may record a justified non-applicability decision.

**PRM-012:** The scope of the promoted claim MUST NOT exceed the scope successfully tested.

## 8. Gate 4 — Paper Trading

Tests the frozen Trade Plan against unfolding conditions without real capital. It validates operations as well as signal performance.

The policy defines minimum elapsed time, opportunity count, trade count, market regimes, operational reliability, net performance, drawdown, and incident tolerance.

**PRM-013:** Paper Trading MUST precede live eligibility.

**PRM-014:** Paper fills and timing MUST use documented realistic assumptions.

**PRM-015:** A passing Paper result MUST include adequate sample justification, not merely positive profit.

## 9. Gate 5 — Validated Opportunity

Creates or approves a complete Trade Plan and permits admission to the Trade Queue. The plan must express instrument, direction, buy/sell or equivalent executable rules, entry, exit, invalidation, expiry, risk, uncertainty, cost, capacity, and lineage.

**PRM-016:** Ambiguous action semantics MUST block promotion.

**PRM-017:** Current evidence and knowledge freshness MUST be checked at promotion time.

## 10. Gate 6 — Optional Live Eligibility

This gate is disabled unless an approved live architecture exists. It checks capital mandate, pre-trade risk, broker readiness, credentials, reconciliation, incident response, kill switches, compliance, and authorization.

**PRM-018:** Research confidence MUST NOT grant live authority.

**PRM-019:** The AI Researcher MAY be authorized to make bounded live decisions only under an explicit policy.

## 11. Failure and Re-entry

Failure produces evidence. It may contradict a Hypothesis, narrow its scope, prompt a new version, make it inactive, or block it pending better data. It never deletes history.

**PRM-020:** A failed candidate MUST NOT retry unchanged until the reason for failure and basis for retest are recorded.

**PRM-021:** A refined candidate MUST identify which earlier Results remain applicable.

**PRM-022:** `indeterminate` MUST lead to more evidence or inactivity, not promotion.

## 12. Continuous Monitoring and Demotion

Validated, paper, and live strategies remain conditional knowledge. Drift, deteriorating win rate, drawdown, execution failure, regime change, data issues, or invalidated assumptions may suspend Queue Entries and return the strategy to research.

**PRM-023:** Monitoring thresholds and review cadence MUST be defined before deployment.

**PRM-024:** Demotion or suspension MUST preserve the original Promotion Decisions.

## 13. AI and Policy Responsibilities

The AI Researcher interprets evidence and recommends a transition. The policy engine calculates objective gate satisfaction. An authorized human handles specified exceptions and live authority.

**PRM-025:** AI recommendation and objective gate outcome MUST be stored separately.

**PRM-026:** Policy code MUST NOT invent a scientific narrative.

## 14. Reporting

Sentinel reports counts and conversion rates for every stage, reasons for failure/indeterminate outcomes, time spent in stage, Paper and live performance, and cohorts by strategy family, symbol, and policy version.

**PRM-027:** Funnel statistics MUST not combine backtest, validation, Paper, and live results into one unlabeled metric.

## 15. Acceptance Criteria

Tests must prove ordered gates, validation independence, version freezing, override visibility, scope enforcement, Paper prerequisites, live-authority separation, failed-candidate retention, re-entry rules, and monitoring demotion.

## 16. Future Extensions

Future versions may add portfolio gates, independent AI review panels, formal model-risk approval, jurisdictional policies, staged capital limits, and champion/challenger deployment.

## 17. Out of Scope

Exact thresholds, Experiment algorithms, portfolio sizing, broker implementation, and legal approvals are configured or specified elsewhere.