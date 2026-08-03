# Sentinel Architecture

| Field | Value |
|---|---|
| Document ID | `SENTINEL-02` |
| Status | Normative architecture specification |
| Version | 1.0 |
| Depends on | `00-Vision.md`, `01-Philosophy.md` |

## 1. Purpose

This document defines Sentinel's logical architecture, subsystem responsibilities, ownership boundaries, permitted dependencies, and principal information flows. It describes what the system must contain without prescribing a particular deployment topology or vendor.

## 2. Architectural Context

Sentinel is a documentation-driven autonomous quantitative research platform. Its primary output is a validated trading opportunity. It may later execute live trades when a separate approved execution and risk architecture grants that authority.

The canonical research chain is:

```text
Market
  -> Snapshot
  -> Observation
  -> Observation Store
  -> Research Journal
  -> Hypothesis
  -> Hypothesis Store
  -> Experiment Request
  -> Experiment Service
  -> Experiment Store
  -> Promotion Pipeline
  -> Paper Trade
  -> Trade Queue
  -> AI Review
  -> Notification or Authorized Execution
  -> Monitoring and Learning
```

The Journal repeatedly reconnects stored results to the AI Researcher. The architecture is a loop, not a one-way batch pipeline.

## 3. Architectural Drivers

- traceability from opportunity to source evidence;
- point-in-time reproducibility;
- persistent research across restarts;
- strict separation between AI reasoning and deterministic computation;
- append-only history;
- staged validation and low-to-moderate risk;
- clear market-close research and intraday monitoring loops;
- replaceable data, AI, storage, and execution adapters;
- implementation clarity for humans and coding agents;
- optional evolution from research output to governed live execution.

## 4. System Boundary

### 4.1 Inside Sentinel

Sentinel owns:

- watchlists and research policy;
- market calendars and scheduling;
- data acquisition, caching, provenance, and quality status;
- deterministic features and research snapshots;
- AI Researcher orchestration and structured AI contracts;
- permanent Observation, Hypothesis, Experiment, and Trade stores;
- generated Research Journals;
- deterministic experiment execution;
- promotion gates and Trade Queue state;
- paper trading and performance measurement;
- opportunity monitoring, reports, and notifications;
- audit, security, configuration, and observability controls;
- optional live-execution coordination when separately authorized.

### 4.2 External systems

External systems may provide market data, AI inference, news or contextual evidence, identity, notification delivery, brokerage, exchange access, and durable infrastructure. They are adapters or destinations, never architectural authorities.

**ARC-001:** External providers MUST be accessed through owned contracts.

**ARC-002:** Provider-specific representations MUST NOT leak into core domain objects without normalization.

## 5. Logical Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE & CONTROL                     │
│ policies · identity · configuration · audit · scheduling   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                     MARKET FOUNDATION                       │
│ adapters -> history -> quality -> features -> snapshots    │
└─────────────────────────────┬───────────────────────────────┘
                              │ evidence
┌─────────────────────────────▼───────────────────────────────┐
│                       RESEARCH SYSTEM                       │
│ Journal -> AI Researcher -> Observations/Hypotheses        │
│                 -> Experiment Requests                      │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│    PERMANENT STORES      │    │     EXPERIMENT SYSTEM       │
│ evidence · observations  │<---│ backtest · validation       │
│ hypotheses · experiments │    │ reproducibility · costs     │
│ trades · lifecycle       │    └──────────────┬──────────────┘
└───────────────┬──────────┘                   │
                └──────────────┬───────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 PROMOTION & OPPORTUNITY SYSTEM              │
│ gates -> paper trading -> trade plans -> Trade Queue        │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               MONITORING, REPORTING & EXECUTION             │
│ pre-market review · triggers · notify · optional execute    │
└─────────────────────────────────────────────────────────────┘
```

## 6. Subsystems

### 6.1 Configuration and policy

Provides the versioned control plane for watchlists, research capacity, data windows, promotion thresholds, schedules, costs, risk limits, AI selection, resource budgets, and feature sets.

**ARC-003:** Configuration MUST be centralized, typed, validated, and versioned.

**ARC-004:** No business-significant threshold MAY exist only as a magic number in code.

**ARC-005:** Configuration changes affecting research results MUST be recorded with those results.

### 6.2 Scheduler and market calendar

Coordinates market-close research, pre-market review, in-session monitoring, and scheduled maintenance using exchange-aware calendars and time zones.

**ARC-006:** Scheduling MUST use market calendars rather than assuming every weekday is a trading day.

**ARC-007:** A cycle MUST record its effective market date, clock time, and time zone.

### 6.3 Watchlist service

Owns the configured set of symbols eligible for research. The AI Researcher may recommend changes in a future version, but it does not silently change the authoritative watchlist.

**ARC-008:** Sentinel MUST own and persist the active watchlist.

### 6.4 Market data adapters

Acquire historical and current data through replaceable providers. They record source, retrieval time, effective time, revision status, and entitlement.

**ARC-009:** Raw source data MUST remain separable from normalized and derived data.

**ARC-010:** Incremental updates SHOULD avoid re-downloading unchanged history while preserving correction handling.

**ARC-011:** Missing, stale, duplicated, or structurally invalid data MUST be visible to downstream consumers.

### 6.5 History service

Maintains point-in-time market history and exposes availability and freshness. The initial research design may use approximately two years of daily history, but windows are configured per experiment.

**ARC-012:** Historical queries MUST support an as-of boundary.

### 6.6 Feature engine and registry

Calculates deterministic measurements. The v1 skeleton begins with a small core set—such as SMA, EMA, RSI, ATR, and Bollinger Bands—while allowing later additions through registered, versioned feature definitions.

**ARC-013:** Feature calculations MUST be deterministic for identical inputs and versions.

**ARC-014:** Feature metadata MUST include name, version, parameters, input window, and effective time.

**ARC-015:** Features MUST report measurements, not unsupported market opinions.

### 6.7 Snapshot service

Builds immutable Research Snapshots containing the relevant evidence for one symbol at one point in time.

**ARC-016:** A Snapshot MUST reference its underlying data and feature versions.

**ARC-017:** A Snapshot MUST NOT embed AI interpretation as authoritative evidence.

### 6.8 Permanent research stores

Persist distinct domain objects and lifecycle events. Logical stores exist for Observations, Hypotheses, Experiments, validations, Trade Plans, Paper Trades, Live Trades, and audit records. A single physical database may implement several stores if contracts remain separate.

**ARC-018:** Stores MUST expose append-oriented, domain-specific contracts.

**ARC-019:** Completed historical records MUST NOT be updated in place.

**ARC-020:** Stores MUST support lineage queries in both directions.

### 6.9 Research Journal builder

Generates the AI Researcher's current context for a symbol from permanent stores. It does not persist an alternative truth.

**ARC-021:** A Journal MUST be reproducible from its source record versions.

**ARC-022:** Journal construction MUST apply explicit relevance, ordering, and context-size rules.

### 6.10 AI gateway

Provides a replaceable interface to one or more AI models. It combines the AI Constitution, task contract, Journal, Snapshot, and output schema, then records request and response metadata.

**ARC-023:** AI calls MUST record provider, model, prompt/template version, parameters, time, and structured response status.

**ARC-024:** Invalid AI output MUST fail schema validation and MUST NOT enter domain stores as valid artifacts.

**ARC-025:** Secrets and hidden reasoning MUST NOT be stored in user-facing research artifacts.

### 6.11 AI Researcher

Acts as Sentinel's lead research scientist. It reviews Journals and new evidence, authors Observations, maintains up to six active Hypotheses per symbol by default, requests Experiments, interprets results, and recommends lifecycle transitions.

**ARC-026:** The Researcher MUST review existing research before creating new hypotheses.

**ARC-027:** The Researcher MUST NOT execute or fabricate experiment results.

**ARC-028:** Researcher recommendations MUST pass policy and promotion validation before state changes occur.

### 6.12 Experiment service

Executes structured, immutable Experiment Requests using approved data, code, benchmarks, costs, partitions, and evaluation protocols. It supports initial backtests, unseen-period validation, sensitivity analysis, cross-market testing, and revalidation.

**ARC-029:** Experiment execution MUST be isolated from AI narrative generation.

**ARC-030:** Every Experiment Result MUST include enough lineage to reproduce it.

**ARC-031:** Discovery and independent validation datasets MUST be distinguishable.

### 6.13 Promotion pipeline

Enforces the transition from hypothesis to initial test, independent validation, optional generalization tests, paper trading, validated opportunity, and live eligibility.

**ARC-032:** Promotion gates MUST be explicit, ordered, and independently auditable.

**ARC-033:** The AI Researcher MAY recommend promotion but MUST NOT bypass a failed gate.

**ARC-034:** A failed gate MUST produce a durable result and an explicit lifecycle outcome.

### 6.14 Paper-trading service

Runs candidate plans against live or delayed market conditions without real capital. It records intended decisions, fills, costs, latency, and outcomes using the same plan semantics expected in live operation.

**ARC-035:** Paper trading MUST not use information unavailable at the simulated decision time.

**ARC-036:** Paper and live records MUST remain explicitly distinguishable.

### 6.15 Trade Queue

Holds validated, time-bounded Trade Plans awaiting market conditions and final review. It is not a queue of raw AI suggestions.

**ARC-037:** Queue admission MUST require all configured promotion gates through paper trading.

**ARC-038:** Queue entries MUST define entry, exit, invalidation, expiry, risk, and supporting research.

**ARC-039:** Stale or invalid entries MUST be suspended or removed from active consideration without deleting history.

### 6.16 Monitoring and notification

The fast loop reviews queued opportunities before and during relevant market sessions, confirms assumptions, observes triggers, and sends concise, actionable reports.

**ARC-040:** Monitoring MUST use current evidence without conducting ungoverned intraday research.

**ARC-041:** Notifications MUST distinguish recommendations, paper actions, and live actions.

### 6.17 Optional execution adapter

Translates an authorized Trade Plan into broker or venue instructions. This adapter is disabled unless live execution policy, risk controls, credentials, reconciliation, and emergency controls are active.

**ARC-042:** Research validation MUST NOT itself grant live-order permission.

**ARC-043:** Execution MUST enforce pre-trade risk and idempotency before submission.

**ARC-044:** Submitted, acknowledged, filled, rejected, cancelled, and reconciled states MUST be recorded.

### 6.18 Reporting and observability

Produces daily and on-demand reports covering data health, research work, stage progression, Paper Trade performance, opportunity state, and authorized live activity.

**ARC-045:** Reports MUST expose hypotheses tested, failed, advanced, paper traded, and made live-eligible.

**ARC-046:** Performance reporting SHOULD include sample size, win rate, average profit, average loss, expectancy, costs, and drawdown.

## 7. Ownership and Dependency Rules

Permitted primary dependencies flow inward from orchestration to domain contracts and outward through adapters:

```text
UI / Scheduler / Reports
          |
     Application Services
          |
       Domain Model
          |
   Ports / Owned Contracts
          |
Provider, Storage, AI, Broker Adapters
```

**ARC-047:** Domain objects MUST NOT import provider SDKs, UI code, or storage implementations.

**ARC-048:** Application services MUST coordinate domain behavior without becoming generic data stores.

**ARC-049:** Adapters MUST translate external failures into owned error categories.

**ARC-050:** Circular subsystem dependencies MUST NOT be introduced.

## 8. Canonical Flows

### 8.1 Post-market research flow

1. Scheduler opens a Research Cycle for the effective market date.
2. Market data is incrementally refreshed and quality-checked.
3. Features and immutable Snapshots are produced.
4. The Journal is generated from stored research.
5. The AI Researcher reviews Journal plus Snapshot.
6. Structured Observations and Hypothesis changes are validated and appended.
7. Experiment Requests are queued and executed within budget.
8. Results are stored and presented in a regenerated Journal.
9. The Researcher recommends next actions or promotion.
10. Promotion policy applies allowed lifecycle changes.
11. A cycle report is produced.

### 8.2 Promotion flow

```text
Hypothesis
  -> Initial Backtest
  -> Independent Unseen Validation (six months by default)
  -> Cross-Market/Regime Challenge when applicable
  -> Paper Trade
  -> Validated Trade Plan
  -> Trade Queue
```

### 8.3 Market-session flow

1. Before open, queued plans are refreshed against current evidence.
2. Invalid or stale plans are suspended.
3. A pre-market report presents eligible plans and their conditions.
4. During the session, the monitor observes triggers and invalidations.
5. The system notifies the user or invokes authorized execution.
6. Outcomes are recorded for post-market research.

### 8.4 Restart and recovery flow

Sentinel reconstructs current state from permanent stores, idempotency keys, and lifecycle events. The AI Researcher does not rely on process memory.

**ARC-051:** A restart MUST NOT erase research or duplicate completed lifecycle transitions.

**ARC-052:** Incomplete work MUST be resumed, retried, or marked failed through explicit recovery policy.

## 9. Cross-Cutting Requirements

### 9.1 Identity and audit

**ARC-053:** Every material command and state transition MUST identify its human or machine actor.

### 9.2 Security

**ARC-054:** Secrets MUST be stored outside source code and research records.

**ARC-055:** Data, AI, paper, and live permissions MUST be independently controllable.

### 9.3 Reliability

**ARC-056:** External calls MUST have bounded retries, timeouts, and idempotency where applicable.

### 9.4 Observability

**ARC-057:** Operational health MUST be distinguishable from research success.

### 9.5 Versioning

**ARC-058:** Domain schemas, policies, prompts, features, experiments, and adapters MUST support version identification.

## 10. Deployment Model

The logical architecture supports an initial single-process modular application and later decomposition. A likely progression is:

- Windows development with VS Code and documentation-driven implementation;
- Ubuntu lab environment for testing, simulation, and long-running paper operation;
- dedicated production Linux environment for controlled 24/7 services.

This progression is not a mandate. Correct ownership and contracts matter more than process count.

**ARC-059:** Distribution MUST NOT be introduced merely to appear scalable.

**ARC-060:** A modular monolith is the preferred initial deployment unless measured needs justify separation.

## 11. Future Extensions

Future architecture may include multiple Researcher and Critic agents, news and fundamental evidence, feature-request workflows, portfolio construction, distributed experiment workers, event streaming, additional asset classes, and bounded AI-directed live execution.

## 12. Out of Scope

This document does not define complete object schemas, exact promotion thresholds, broker selection, database technology, feature formulas, or prompt wording. Those are specified elsewhere or remain configuration decisions.
