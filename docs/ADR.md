# Sentinel Architecture Decision Record

| Field | Value |
|---|---|
| Document ID | `SENTINEL-ADR` |
| Status | Living decision record |
| Authority | Records why the normative specifications take their current form |

## 1. Purpose and Format

This file records accepted architectural decisions so future contributors understand not only what Sentinel requires, but why. Normative behavior lives in the numbered specifications; this record supplies rationale and consequences.

Each decision has an identifier, status, context, decision, rationale, and consequences. Changes supersede prior decisions rather than silently rewriting them.

## ADR-001 — Sentinel is an autonomous quantitative research platform

**Status:** Accepted

**Context:** The project began as an AI trading application but evolved toward a disciplined process for learning from markets.

**Decision:** Sentinel is a research operating system whose primary output is validated trading opportunities.

**Rationale:** Durable value comes from evidence, repeatable experiments, knowledge, and controlled promotion—not a direct `Data -> AI -> Trade` shortcut.

**Consequences:** Research integrity and memory are first-class. Trading is downstream of validation.

## ADR-002 — Documentation is the architectural source of truth

**Status:** Accepted

**Decision:** The `docs/` manual governs implementation. Code and coding agents implement it and do not invent product behavior.

**Consequences:** Requirements use stable identifiers. Material architectural changes update specifications and this record.

## ADR-003 — AI reasons; Sentinel records and executes

**Status:** Accepted

**Decision:** Stores own durable truth, the Research Journal owns current context, the AI Researcher owns reasoning, and Sentinel services own deterministic execution.

**Rationale:** This prevents AI assertions from becoming unverified facts and prevents deterministic code from acquiring undocumented market opinions.

## ADR-004 — Permanent Stores replace generic mutable ResearchMemory

**Status:** Accepted

**Context:** An early `ResearchMemory`/`ResearchRecord` design mixed domain concepts and context.

**Decision:** Use distinct permanent Stores for Observations, Hypotheses, Experiments, and Trades. Generate Journals from them.

**Consequences:** Process memory is not required for continuity. Domain history survives restart.

## ADR-005 — The Research Journal is generated context

**Status:** Accepted

**Decision:** A Journal is reconstructed per symbol and cycle from authoritative Stores; it is not independently edited or authoritative.

**Rationale:** This separates permanent truth from the contextual view needed by the AI Researcher.

## ADR-006 — History is immutable

**Status:** Accepted

**Decision:** Accepted Observations, completed Experiments, Trades, and lifecycle decisions are append-only. Corrections and evolution create linked records or versions.

**Consequences:** Failure and changed beliefs remain inspectable; hindsight cannot silently rewrite research.

## ADR-007 — Distinct first-class research objects

**Status:** Accepted

**Decision:** Snapshot, Observation, Journal, Hypothesis, Experiment, Trade Plan, Paper Trade, and Live Trade are distinct domain concepts.

**Rationale:** Each answers a different principal question and has different ownership and lifecycle.

## ADR-008 — The AI role is Researcher

**Status:** Accepted

**Decision:** The principal AI role is consistently named `Researcher`, not Trader, Assistant, or generic Agent.

**Consequences:** Its authority centers on scientific reasoning. AI providers and models remain replaceable.

## ADR-009 — Up to six active Hypotheses per symbol

**Status:** Accepted

**Decision:** The default active research capacity is six Hypotheses per watched symbol.

**Rationale:** Capacity encourages focus and comparison without forcing one explanation. Later discussion clarified that Sentinel maintains existing Hypotheses rather than generating six from scratch each day.

**Consequences:** Six is a maximum, not a quota. Inactive history is unlimited subject to retention policy.

## ADR-010 — Hypotheses evolve and are not deleted

**Status:** Accepted

**Decision:** Hypothesis identity persists through immutable versions. A Hypothesis may become inactive, contradicted, or superseded; ordinary failure never deletes it.

**Rationale:** Failed ideas and their evidence are research memory and may become relevant under new regimes.

## ADR-011 — The AI requests; Sentinel executes Experiments

**Status:** Accepted

**Decision:** The Researcher selects questions and submits structured Experiment Requests. Deterministic Sentinel services execute them and store Results.

**Consequences:** The AI cannot fabricate that it ran a backtest. Interpretation remains separate from result.

## ADR-012 — Escalating promotion pipeline

**Status:** Accepted

**Decision:** Candidate strategies progress through initial backtest, independent unseen validation, applicable generalization challenge, Paper Trading, validated opportunity, and optional live eligibility.

**Rationale:** Each stage reduces a different uncertainty and makes the test more operationally realistic.

## ADR-013 — Six-month unseen validation is the default

**Status:** Accepted

**Context:** The owner repeatedly required a successful initial test to be repeated on different data, commonly six months.

**Decision:** A distinct six-month unseen period is the default independent validation window, configurable when research design justifies another duration.

## ADR-014 — Research goals are configurable

**Status:** Accepted; supersedes a fixed-target concept

**Context:** A goal such as 3% in three days was considered too rigid.

**Decision:** Return target, holding period, validation thresholds, and data windows are versioned Research Objective or policy parameters.

**Consequences:** Sentinel discovers what works rather than forcing evidence into one target.

## ADR-015 — Low-to-moderate default risk and valid abstention

**Status:** Accepted

**Decision:** Sentinel defaults to low-to-moderate risk. “Do nothing” is valid when evidence is insufficient, but controls must not create a hidden permanent-abstention bias.

## ADR-016 — Trade Plans must be concrete

**Status:** Accepted

**Decision:** A validated opportunity states what to buy or sell and defines executable entry, exit, invalidation, expiry, and risk. Static prices are used when appropriate; otherwise rules must be equally unambiguous.

## ADR-017 — Separate slow and fast loops

**Status:** Accepted

**Decision:** Deliberate research runs primarily after market close. A separate fast loop reviews queued plans before and during sessions.

**Rationale:** Intraday urgency must not weaken scientific standards or let monitoring invent strategies.

## ADR-018 — Paper Trading is mandatory before live eligibility

**Status:** Accepted

**Decision:** A candidate must demonstrate operational performance in Paper/Demo Trading before it can become live-eligible.

**Consequences:** The user can see stage counts, win rate, average profit/loss, and operational failures before capital is at risk.

## ADR-019 — Live trading remains an optional future capability

**Status:** Accepted

**Context:** The owner explicitly did not want AI live trading ruled out.

**Decision:** Deployments may stop at notification, but the architecture preserves a route to bounded AI-directed live trading under separate risk, execution, reconciliation, compliance, and authority controls.

**Consequences:** Research validation does not itself grant live authority.

## ADR-020 — Start with a complete skeleton

**Status:** Accepted

**Decision:** v1 prioritizes the complete end-to-end lifecycle using a small core feature set before adding more symbols, measurements, providers, AI clients, scale, or optimization.

**Rationale:** A coherent vertical skeleton reduces repeated redesign and lets future capabilities plug into stable boundaries.

## ADR-021 — Initial modular monolith

**Status:** Accepted

**Decision:** Prefer a modular monolith for the initial implementation unless measured scale or reliability requirements justify distribution.

**Rationale:** Logical ownership does not require premature network boundaries.

## ADR-022 — Multi-asset architecture, equities first

**Status:** Accepted

**Decision:** Equities are the initial proving ground, but core contracts must not make Sentinel Forex-only or equities-only.

## ADR-023 — Watchlist remains Sentinel-owned

**Status:** Accepted

**Decision:** The configured Watchlist is authoritative. The AI may later recommend additions or removals but cannot silently change research scope.

## ADR-024 — Daily work must be visible

**Status:** Accepted

**Decision:** Research Cycle and pre-market reports expose work performed while the user was away, including stage counts, failures, promotions, Paper/live state, and meaningful performance statistics.

## 2. Future Decision Template

```markdown
## ADR-NNN — Title

**Status:** Proposed | Accepted | Superseded | Rejected

**Context:** Why a decision is needed.

**Decision:** The chosen architectural rule.

**Rationale:** Why this option was selected.

**Consequences:** Benefits, constraints, risks, and required follow-up.

**Supersedes / Superseded by:** Related decision identifiers.
```

