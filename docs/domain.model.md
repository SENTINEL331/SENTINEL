# Sentinel Domain Model

| Field | Value |
|---|---|
| Document ID | `SENTINEL-04` |
| Status | Normative domain specification |
| Version | 1.0 |
| Depends on | `00-Vision.md` through `03-Research-Process.md` |

## 1. Purpose

This document defines Sentinel's first-class domain objects, their ownership, identities, relationships, immutability rules, and high-level lifecycles. Detailed object specifications may add fields and constraints but must not contradict this model.

## 2. Modeling Rules

**DOM-001:** Every first-class object MUST have a stable unique identifier.

**DOM-002:** Every persisted object MUST record creation time, effective time where relevant, schema version, and actor.

**DOM-003:** References between objects MUST use stable identifiers rather than copied mutable state.

**DOM-004:** Completed evidence and history objects MUST be immutable.

**DOM-005:** Lifecycle changes MUST be explicit events or versioned transitions.

**DOM-006:** Enumerated states MUST be owned by the domain specification, not invented by individual adapters.

**DOM-007:** Monetary values MUST identify currency; quantities and measurements MUST identify units where ambiguity is possible.

**DOM-008:** Dates and times MUST identify time zone or use UTC plus the relevant market calendar.

## 3. Aggregate Overview

```text
ResearchProgram
  └─ ResearchCycle
      └─ SymbolResearch
          ├─ Snapshot ──> Observation
          ├─ JournalView
          └─ Hypothesis ──> HypothesisVersion
                              └─ ExperimentRequest
                                  └─ ExperimentRun
                                      └─ ExperimentResult
                                          └─ PromotionDecision
                                              └─ TradePlan
                                                  ├─ PaperTrade
                                                  ├─ TradeQueueEntry
                                                  └─ LiveTrade

All material actions ──> LifecycleEvent / AuditEvent
```

## 4. Ownership Summary

| Object | Authoritative owner | Mutability |
|---|---|---|
| Research Objective | Governance | Versioned |
| Watchlist | Sentinel | Versioned |
| Market Data Record | Sentinel evidence store | Append/correct by supersession |
| Feature Value | Sentinel feature store | Immutable |
| Snapshot | Sentinel | Immutable |
| Observation | AI Researcher, validated by Sentinel | Immutable |
| Research Journal | Sentinel-generated view | Not authoritative persistence |
| Hypothesis | AI Researcher, governed by Sentinel | Identity stable; versions immutable |
| Experiment Request | AI Researcher, accepted by Sentinel | Immutable after acceptance |
| Experiment Result | Sentinel experiment service | Immutable |
| Promotion Decision | Policy plus authorized actor | Immutable |
| Trade Plan | Researcher-authored, policy-validated | Versioned |
| Trade Queue Entry | Sentinel opportunity service | Event-driven state |
| Paper Trade | Sentinel paper service | Append-only lifecycle |
| Live Trade | Sentinel execution service | Append-only lifecycle |

## 5. Research Objective

Defines the mission and constraints of a research program.

Required concepts:

- identifier and version;
- name and purpose;
- eligible universe and asset classes;
- target holding horizon;
- return and risk measures;
- default risk posture;
- cost and implementation assumptions;
- promotion-policy reference;
- effective period and status.

Lifecycle: `draft -> approved -> active -> superseded`.

**DOM-009:** Every Hypothesis and Experiment MUST resolve to the Research Objective under which it was created.

## 6. Watchlist

The governed set of instruments eligible for scheduled research.

Required concepts:

- version;
- instrument identifiers;
- active dates;
- inclusion rationale or source;
- market and calendar;
- data requirements;
- actor and approval.

The AI Researcher may recommend a future change but does not silently alter the Watchlist.

## 7. Instrument

A stable representation of a tradable or researchable instrument independent of provider ticker spelling.

Required concepts:

- canonical identifier;
- symbol and venue;
- asset class;
- currency;
- trading calendar and time zone;
- tick and lot constraints;
- provider mappings;
- active dates and corporate lineage.

**DOM-010:** Provider symbols MUST map to a canonical Instrument.

## 8. Market Data Record

An observed market or contextual value with point-in-time provenance.

Required concepts:

- instrument;
- event/effective time;
- availability time;
- retrieval time;
- value and unit;
- source/provider;
- revision/correction status;
- quality status;
- entitlement classification.

**DOM-011:** Event time and availability time MUST remain distinguishable.

## 9. Feature Definition and Feature Value

### 9.1 Feature Definition

Defines a deterministic measurement, its parameters, algorithm version, input requirements, and output semantics.

### 9.2 Feature Value

An immutable calculated value for an Instrument and effective time, linked to its Feature Definition and input lineage.

**DOM-012:** A Feature Value MUST NOT contain an unstructured AI judgment.

## 10. Research Cycle

Represents one scheduled or manually initiated unit of research work.

Required concepts:

- cycle identifier;
- objective and configuration versions;
- effective market date;
- start/end time;
- selected Watchlist version;
- feature set, AI contract, code, and policy versions;
- resource budget and usage;
- status and summary;
- failure or blocking reasons.

Lifecycle: `scheduled -> running -> completed | partially_completed | failed | cancelled`.

## 11. Snapshot

An immutable, point-in-time research evidence package for one Instrument.

Required concepts:

- identifier;
- Instrument and as-of time;
- Research Cycle;
- referenced market records and Feature Values;
- freshness and quality summary;
- source/version lineage;
- creation time.

Lifecycle: created once; never edited. A corrected or expanded view is a new Snapshot.

**DOM-013:** A Snapshot MUST contain or reference sufficient evidence to reconstruct its presentation to the Researcher.

## 12. Observation

An objective AI-authored statement supported by evidence. It answers: “What fact can reasonably be concluded from the presented evidence?”

Required concepts:

- identifier;
- Instrument;
- statement;
- evidence citations, normally including a Snapshot;
- importance or relevance;
- authoring AI-call reference;
- creation time;
- deduplication/family linkage;
- schema and contract version.

An Observation does not contain a strategy, predicted return, Experiment Result, or order instruction.

Lifecycle: `proposed -> accepted | rejected_as_invalid | duplicate`. Accepted content is immutable.

**DOM-014:** Acceptance validates structure and evidence linkage; it does not certify the Observation as timeless truth.

## 13. Research Journal

A generated, ordered context view for the AI Researcher. It answers: “What does the Researcher need to understand now?”

Required concepts in a rendered Journal:

- Instrument, date, Research Objective, and mission;
- current Snapshot reference;
- recent and important Observations;
- active Hypotheses and current versions;
- active and relevant completed Experiments;
- Paper and live monitoring state where applicable;
- contradictions, open questions, and pending actions;
- source record identifiers;
- builder and rendering version.

The Journal may be cached as a render artifact, but the cache is not authoritative and must be reproducible.

**DOM-015:** A Journal MUST NOT be directly edited to change research state.

## 14. Hypothesis

A stable research identity representing a falsifiable proposed relationship worthy of investigation.

Required concepts:

- identifier and Instrument or universe scope;
- Research Objective;
- current lifecycle state;
- current version reference;
- family/competing-hypothesis relationships;
- active-capacity status;
- creation author and time;
- complete version and evidence history.

The Hypothesis identity persists while its wording and test design evolve through Hypothesis Versions.

### 14.1 Hypothesis Version

Required concepts:

- hypothesis identifier and version number;
- precise claim and proposed mechanism;
- expected direction/effect;
- universe, regime, and holding horizon;
- supporting and opposing Observation references;
- assumptions;
- falsification and invalidation conditions;
- confidence and rationale;
- proposed evaluation method;
- predecessor and change reason.

Lifecycle states for the identity include `active`, `inactive`, `blocked`, `contradicted`, `supported`, and `superseded`. Promotion stage is tracked separately so scientific status is not confused with operational stage.

**DOM-016:** No more than six Hypotheses per Instrument MAY consume active capacity under the default policy.

**DOM-017:** A failed Hypothesis MUST NOT be deleted.

**DOM-018:** Hypothesis text MUST NOT be edited in place after it has an accepted Experiment Request; refinement creates a new version.

## 15. Experiment Request

A structured request by the AI Researcher for Sentinel to reduce uncertainty about one Hypothesis Version.

Required concepts:

- identifier;
- Hypothesis Version;
- Experiment type and research question;
- universe, period, data partition role, and as-of constraint;
- strategy or test specification;
- features and parameters;
- benchmark/null;
- metrics and acceptance criteria;
- cost, liquidity, slippage, latency, and capacity assumptions;
- robustness checks;
- requested resource budget;
- authoring AI-call reference.

Lifecycle: `proposed -> accepted | rejected -> queued -> running -> completed | failed | cancelled`.

**DOM-019:** Acceptance freezes the Experiment Request.

## 16. Experiment Run and Result

### 16.1 Experiment Run

One execution attempt of an accepted request, recording environment, code, data, parameters, seed, start/end times, logs, and status.

### 16.2 Experiment Result

The immutable output of a Run, including metrics, uncertainty, diagnostics, trades or samples as applicable, warnings, protocol deviations, costs, robustness results, and machine-verifiable artifacts.

**DOM-020:** Retrying a failed Run creates another Run; it does not overwrite the failure.

**DOM-021:** Result interpretation belongs outside the Result object.

## 17. Interpretation

An AI-authored assessment of one or more immutable Results and their implications for a Hypothesis.

Required concepts:

- referenced Results and Hypothesis Version;
- summary;
- supporting and conflicting findings;
- confidence change and rationale;
- limitations;
- recommended next action;
- authoring AI-call reference.

Interpretations are immutable research artifacts and may disagree.

## 18. Promotion Decision

Records whether an artifact may enter the next promotion stage.

Required concepts:

- source Hypothesis/Trade Plan version;
- from-stage and proposed to-stage;
- objective gate results;
- AI recommendation;
- policy version;
- final decision and reason;
- decision actor and time;
- exception/override reference if any.

Stages: `research_candidate`, `initial_backtest`, `independent_validation`, `generalization_challenge`, `paper_trading`, `validated_opportunity`, `live_eligible`.

**DOM-022:** Promotion Decisions MUST be immutable and chain to prior stage decisions.

## 19. Trade Plan

A versioned, actionable expression of validated research.

Required concepts:

- identifier/version and Instrument(s);
- supporting Hypothesis, Results, and Promotion Decisions;
- direction or relative-value structure;
- activation and entry condition;
- explicit entry price when appropriate;
- exit, target, stop, and invalidation conditions;
- intended horizon and expiry;
- sizing inputs and maximum risk;
- expected-return distribution and uncertainty;
- liquidity, cost, capacity, and timing assumptions;
- eligible market sessions;
- operational mode: research, paper, notification, or authorized live.

**DOM-023:** A Trade Plan MUST be executable without inventing missing buy/sell semantics.

**DOM-024:** A material plan change MUST create a new version and may require revalidation.

## 20. Paper Trade

The append-only operational history of applying a Trade Plan without real capital.

Required concepts:

- Trade Plan version;
- simulated account and capital assumptions;
- decision, submission, fill, and exit times;
- requested and simulated prices/quantities;
- fees, spread, slippage, and latency;
- skipped or missed actions;
- profit/loss and risk outcomes;
- deviations and incidents;
- lifecycle events.

Lifecycle: `eligible -> monitoring -> triggered -> opened -> partially_closed -> closed`, with terminal alternatives such as `expired`, `invalidated`, `cancelled`, or `failed`.

## 21. Trade Queue Entry

A current-state projection for one validated Trade Plan awaiting or undergoing market monitoring.

Required concepts:

- Trade Plan version;
- admission decision;
- priority;
- activation window and expiry;
- current validity;
- last review time and evidence;
- intended action mode;
- suspension/withdrawal reason.

Lifecycle: `queued -> eligible -> triggered -> actioned`, or `suspended | expired | invalidated | withdrawn`.

The historical transitions are authoritative; the queue projection may be updated from those events.

## 22. Live Trade

The append-only record of authorized real-capital execution. It extends the operational concepts of Paper Trade with broker, account, order, acknowledgement, fill, reconciliation, and incident references.

**DOM-025:** A Live Trade MUST reference the authority and risk decision that permitted it.

**DOM-026:** Paper and Live Trades MUST never share an ambiguous mode.

## 23. Report

A reproducible presentation of research or operational state, including Cycle Reports, Pre-Market Reports, Performance Reports, and Incident Reports.

Required concepts:

- report type and effective period;
- source identifiers and query/configuration version;
- generated time;
- audience and sensitivity;
- stage-specific counts and metrics;
- limitations and missing-data warnings.

Reports are derived artifacts, not authoritative history.

## 24. Lifecycle and Audit Events

A Lifecycle Event records a domain transition. An Audit Event records who or what issued, approved, rejected, or attempted an action.

Required concepts:

- event identifier and type;
- aggregate identifier and prior version/state;
- command/cause and correlation identifier;
- actor;
- policy/configuration version;
- event and recording times;
- outcome and reason.

**DOM-027:** Material state MUST be reconstructable from authoritative records and events.

## 25. Identity, Equality, and Deduplication

- Entities such as Hypotheses and Trade Plans are equal by stable identity.
- Value objects such as price, time range, or metric definitions are equal by value and unit.
- Observations may be semantically similar without being identical; deduplication records the relationship and does not destroy provenance.
- Experiment Requests with equivalent protocols remain distinct if created under different Hypothesis Versions or policies.

**DOM-028:** Deduplication MUST NOT convert repeated claims into independent evidence.

## 26. Deletion and Retention

Research and trade history is retained according to policy, legal obligations, data rights, and operational cost. Logical deactivation or supersession is preferred over deletion. If legal or entitlement requirements compel removal, Sentinel preserves a non-sensitive tombstone and impact record where permitted.

**DOM-029:** Ordinary application behavior MUST NOT hard-delete accepted research or completed trading records.

## 27. Future Extensions

Future objects may include Research Question, Feature Request, Causal Model, Portfolio Hypothesis, Research Agent, Critique, Independent Reproduction, Incident, and Capital Allocation Decision. New objects must declare their principal question, owner, mutability, and lifecycle.

## 28. Out of Scope

This document does not define database tables, serialization formats, API endpoints, Python classes, or exact metric formulas. Implementations must map to this model without treating a storage schema as the domain itself.