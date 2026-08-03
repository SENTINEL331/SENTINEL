# Trade Queue Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-10` |
| Requirement prefix | `TRQ` |
| Status | Normative subsystem specification |

## 1. Purpose

The Trade Queue is the governed collection of validated, versioned Trade Plans awaiting their specified market conditions, final validity review, notification, paper action, or authorized live execution. It separates completed research from time-sensitive monitoring.

## 2. Responsibilities

The subsystem owns admission, priority, validity projection, market-session eligibility, trigger monitoring, suspension, expiry, withdrawal, action handoff, and audit history.

It does not accept raw AI tips, run open-ended research, waive promotion gates, size portfolios without policy, or grant live authority.

## 3. Admission

A Queue Entry requires:

- immutable Trade Plan version;
- supporting Hypothesis and Experiment lineage;
- completed required Promotion Decisions through Paper Trading;
- current risk and implementability assessment;
- entry, exit, invalidation, and expiry rules;
- allowed sessions and market calendar;
- intended mode: notify, paper, or authorized live;
- current data-quality and monitoring readiness.

**TRQ-001:** Only a validated Trade Plan MAY enter the Trade Queue.

**TRQ-002:** Queue admission MUST NOT itself authorize real-capital execution.

**TRQ-003:** An incomplete or ambiguous buy/sell plan MUST be rejected.

## 4. Queue Entry Fields

Required concepts include:

- `queue_entry_id` and Trade Plan version;
- admission decision and time;
- priority and rationale;
- activation window, eligible sessions, and expiry;
- trigger and invalidation expressions;
- current status and validity;
- last review evidence/time;
- intended action mode;
- risk-policy and authority references;
- suspension, withdrawal, or terminal reason;
- complete lifecycle events.

## 5. Lifecycle

```text
queued -> under_review -> eligible -> triggered -> actioned
   |            |            |
   +-> suspended <- invalidated
   +-> expired
   +-> withdrawn
```

An actioned entry may produce a notification, Paper Trade, or authorized live-order workflow. Terminal state does not delete the entry.

**TRQ-004:** Every transition MUST record actor, time, evidence, policy, and reason.

**TRQ-005:** A material Trade Plan change MUST create a new version and new or superseding Queue Entry.

## 6. Pre-Market Review

Before the relevant market opens, Sentinel must:

1. refresh current permitted evidence;
2. verify market calendar and session;
3. check data freshness and operational health;
4. reevaluate invalidation and expiry;
5. confirm risk and authority mode;
6. publish a pre-market report.

**TRQ-006:** A Queue Entry MUST NOT become eligible on stale or failed required data.

**TRQ-007:** The report MUST state exact activation, exit, invalidation, expiry, mode, and material risk.

## 7. Intraday Monitoring

The fast loop evaluates predeclared conditions against current evidence. It does not rewrite the strategy or generate new Hypotheses.

**TRQ-008:** Trigger evaluation MUST be deterministic, versioned, and event-time aware.

**TRQ-009:** A trigger MUST be distinguished from a confirmed action.

**TRQ-010:** If required validity cannot be established, the safe state is suspension rather than assumed eligibility.

**TRQ-011:** Fast-loop information MAY create an Observation or research task for the next slow loop but MUST NOT cause unvalidated strategy mutation.

## 8. Priority and Conflicts

Priority may consider expiry, evidence strength, expected risk-adjusted value, capital use, operational readiness, and portfolio policy. Priority is not authority.

**TRQ-012:** Priority criteria MUST be explicit and versioned.

**TRQ-013:** Conflicting plans for the same capital or Instrument MUST be resolved by portfolio/risk policy before action.

**TRQ-014:** An AI confidence score alone MUST NOT determine priority.

## 9. Notification

A notification must state whether it is informational, requires approval, records a Paper Trade, or reports an authorized live action. It includes plan identity, conditions met, intended action, risk, expiry, and a concise evidence trail.

**TRQ-015:** Notifications MUST NOT describe an unexecuted action as executed.

**TRQ-016:** Delivery failure MUST be recorded and follow escalation policy.

## 10. Execution Handoff

For live mode, the Queue hands an immutable plan and trigger event to a separately authorized execution and pre-trade risk service. The Queue never holds broker credentials.

**TRQ-017:** Live handoff MUST include idempotency and authority identifiers.

**TRQ-018:** Risk rejection MUST be terminal for that attempted action unless a new authorized decision is created.

## 11. Restart and Recovery

Current Queue state must be reconstructable from durable Entries and events. On restart Sentinel reviews every non-terminal entry before resuming monitoring.

**TRQ-019:** Restart MUST NOT re-trigger an already actioned event.

**TRQ-020:** Missed monitoring intervals MUST be disclosed; Sentinel MUST NOT infer fills or decisions that were not recorded.

## 12. Reporting

Reports cover queued, eligible, triggered, actioned, suspended, invalidated, expired, and withdrawn counts; current capital/risk conflicts; missed triggers; delivery failures; and stage-specific outcomes.

## 13. Acceptance Criteria

Tests must cover admission gates, plan ambiguity, calendars, expiry, stale data, deterministic triggers, duplicate events, restart, conflicting plans, notification failure, paper/live distinction, and unauthorized execution attempts.

## 14. Future Extensions

Future versions may add portfolio optimization, multi-leg atomic plans, auction/session-specific handling, approval workflows, and multiple execution venues.

## 15. Out of Scope

Research discovery, Experiment execution, promotion design, brokerage implementation, portfolio construction, and accounting are outside this subsystem.
