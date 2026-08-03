# System Lifecycle

| Field | Value |
|---|---|
| Document ID | `SENTINEL-15` |
| Requirement prefix | `LFC` |
| Status | Normative runtime specification |

## 1. Purpose

This document defines Sentinel's runtime behavior over market days, non-market days, restarts, failures, and longer research periods. It connects the slow Research Loop and fast Execution-Monitoring Loop without mixing their responsibilities.

## 2. Lifecycle Overview

```text
Market Close
  -> Refresh and qualify data
  -> Build Snapshots and Journals
  -> Run AI research
  -> Execute and review Experiments
  -> Apply promotion gates
  -> Update Trade Queue
  -> Publish Research Cycle report
  -> Wait / run bounded background work
  -> Pre-market review
  -> Publish pre-market report
  -> Monitor market session
  -> Notify / Paper Trade / authorized execute
  -> Record outcomes
  -> Market Close
```

## 3. System States

Top-level operational states are:

- `starting` — validating configuration, stores, adapters, and clocks;
- `ready` — able to schedule work;
- `researching` — slow-loop work active;
- `pre_market_review` — Queue validity review active;
- `monitoring` — fast loop active during an eligible session;
- `maintenance` — approved migration or upkeep;
- `degraded` — limited work is safe but one or more capabilities failed;
- `paused` — no new work; state remains inspectable;
- `stopping` — draining and checkpointing;
- `stopped` — no active processing;
- `incident` — safety or integrity failure requires incident policy.

**LFC-001:** Operational state MUST NOT be inferred solely from process existence.

**LFC-002:** State transitions MUST be durable and observable.

## 4. Startup

On startup Sentinel:

1. loads and validates configuration and secrets references;
2. verifies clock, time zone, and market-calendar availability;
3. opens stores and checks compatible schema versions;
4. verifies data, AI, notification, Paper, and optional live adapters according to mode;
5. reconstructs incomplete cycles, Experiment Runs, Queue Entries, and trades;
6. performs idempotency and reconciliation checks;
7. determines current market phase;
8. enters `ready`, `degraded`, or `incident`.

**LFC-003:** Startup MUST fail safely when authoritative state cannot be trusted.

**LFC-004:** Live mode MUST remain disabled until risk, broker, reconciliation, and emergency controls pass readiness checks.

## 5. Post-Market Research

After each watched market's official data is expected to be available:

1. open an identified Research Cycle;
2. incrementally acquire data;
3. record quality/freshness and block invalid scopes;
4. calculate configured Features;
5. create immutable Snapshots;
6. generate one Journal per eligible watched symbol;
7. request structured Observations;
8. maintain up to six active Hypotheses per symbol;
9. validate and queue Experiment Requests;
10. execute work within resource budgets;
11. regenerate Journals and obtain Interpretations;
12. evaluate promotion recommendations and gates;
13. update Paper work and Trade Queue;
14. publish the Research Cycle report;
15. close the cycle as complete, partial, failed, or cancelled.

**LFC-005:** One symbol's failure SHOULD NOT prevent unrelated symbols completing when isolation is safe.

**LFC-006:** A cycle MUST not report success while silently omitting failed stages.

## 6. Overnight Work

Long Experiments and bounded validation may continue after the main cycle. They retain cycle correlation and resource limits. Completed results may open a follow-up interpretation task, but promotion policy determines whether it can occur immediately or waits for the next cycle.

**LFC-007:** Background work MUST be resumable or end in an explicit failure state.

## 7. Pre-Market Review

At a configured interval before the relevant open:

1. load non-terminal Queue Entries;
2. refresh permitted current evidence;
3. verify calendar, freshness, validity, expiry, risk, and operational mode;
4. suspend invalid or unverifiable plans;
5. resolve conflicts through risk/portfolio policy;
6. publish a report containing exact plan conditions and intended mode.

**LFC-008:** Pre-market review MUST NOT promote new research candidates.

**LFC-009:** Missing current evidence MUST produce suspension or explicit reduced authority.

## 8. Market Session Monitoring

During an eligible session Sentinel evaluates only declared Trade Plan conditions. It records trigger evaluations, invalidations, notifications, Paper actions, and authorized execution handoffs.

**LFC-010:** Monitoring cadence MUST match strategy requirements and data capability.

**LFC-011:** The fast loop MUST NOT mutate strategy semantics.

**LFC-012:** Duplicate trigger or action events MUST be prevented or safely recognized.

**LFC-013:** Market halts, early closes, feed gaps, and clock anomalies MUST invoke explicit policy.

## 9. Market Close and Reconciliation

At or after close Sentinel stops new session actions according to plan rules, records end-of-session state, reconciles Paper and authorized live activity, updates performance inputs, and schedules the next slow-loop cycle.

**LFC-014:** Unreconciled live state MUST block further affected execution and raise an incident.

## 10. Non-Trading Days

On weekends and holidays, Sentinel may perform approved Experiments, data maintenance, reports, and revalidation. It must not fabricate a market session or evaluate normal session triggers.

## 11. Failure and Degraded Operation

Failures are isolated by capability:

- data failure blocks affected evidence-dependent work;
- AI failure blocks new AI-authored artifacts but not deterministic monitoring already safe under policy;
- Experiment failure records failure without falsifying the Hypothesis;
- notification failure follows escalation policy;
- Paper adapter failure suspends affected Paper activity;
- live adapter, reconciliation, risk, or authority failure disables affected live action.

**LFC-015:** Degraded operation MUST state which capabilities remain authorized.

**LFC-016:** Safety-critical failure MUST default toward preventing new capital exposure.

## 12. Pause, Resume, and Shutdown

Pause stops new scheduled work and action according to mode while preserving inspection and safe management of existing exposure. Graceful shutdown stops intake, checkpoints work, finishes or cancels tasks by policy, and records final state.

**LFC-017:** Shutdown MUST NOT abandon an open live position without an explicit management policy.

**LFC-018:** Resume MUST revalidate time-sensitive Queue and trade state before action.

## 13. Recovery

After interruption Sentinel reconstructs state from Stores and events, reconciles external effects, identifies missed schedules and monitoring gaps, and resumes only idempotent work.

**LFC-019:** Recovery MUST NOT infer that an unrecorded trade occurred.

**LFC-020:** Missed data or monitoring intervals MUST remain visible in research and performance assessment.

## 14. Reports and User Experience

The user must be able to see what occurred while away. Reports identify:

- symbols reviewed and blocked;
- Hypotheses tested, failed, supported, superseded, and advanced;
- gate funnel counts;
- active Experiments and Paper Trades;
- Queue state and market-session actions;
- stage-specific win rate, average profit/loss, expectancy, and drawdown where valid;
- failures, incidents, and required decisions;
- next scheduled actions.

**LFC-021:** Reports MUST distinguish research, validation, Paper, and live outcomes.

## 15. Continuous and Periodic Review

Daily monitoring is supplemented by configured weekly/monthly research health, model behavior, data quality, promotion calibration, Paper/live degradation, security, and cost reviews.

**LFC-022:** Validated knowledge and Trade Plans MUST have review or expiry rules.

## 16. Acceptance Criteria

Lifecycle tests cover normal days, holidays, early closes, daylight-saving changes, startup during market hours, partial symbol failure, restart during Experiments, duplicate triggers, notification failure, Paper/live adapter failure, pause with exposure, reconciliation failure, and missed cycles.

## 17. Future Extensions

Future versions may support multiple markets and time zones concurrently, event-driven scheduling, 24/7 assets, distributed workers, high-availability monitoring, and staged live-capital mandates.

## 18. Out of Scope

Exact schedules, exchange list, monitoring interval, incident organization, and live-order mechanics are deployment configuration or separate operational specifications.

