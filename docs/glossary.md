# Sentinel Glossary

| Field | Value |
|---|---|
| Document ID | `SENTINEL-14` |
| Status | Normative terminology specification |

## 1. Purpose

This glossary defines the language of Sentinel. Code, documentation, reports, prompts, schemas, and user interfaces must use these meanings consistently.

## 2. Terms

### Accepted artifact

An AI-proposed or system-created artifact that passed schema, reference, policy, and domain validation and entered an authoritative store.

### Active Hypothesis

A Hypothesis currently consuming research capacity for its symbol or scope. The default maximum is six per symbol.

### AI call

One versioned request/response interaction with an AI model under the AI Contract.

### AI Constitution

The highest-level behavioral rules applying to every AI role in Sentinel.

### AI Contract

The machine-readable boundary defining AI task inputs, outputs, authority, validation, audit, and failure semantics.

### AI Researcher / Researcher

Sentinel's AI research role. It authors Observations and Hypotheses, requests Experiments, interprets Results, and recommends lifecycle actions. It does not own authoritative evidence or deterministic execution.

### As-of time

The time boundary beyond which information must not be visible to a point-in-time operation.

### Audit Event

An immutable record of who or what attempted, approved, rejected, or performed a material action and under which policy.

### Backtest

An Experiment that applies a frozen strategy or rule to historical point-in-time data. An initial backtest is not independent validation.

### Capacity

The amount of capital or trading volume a strategy can plausibly support without invalidating its assumptions. “Hypothesis capacity” separately means the configured active-Hypothesis limit.

### Confidence

A defined assessment of current evidentiary strength. It is not certainty, predicted win rate, or a promotion stage.

### Current Understanding

An attributed synthesis in a Journal. It is context derived from records, not an authoritative fact store.

### Data availability time

When information became knowable to Sentinel, distinct from when the underlying event occurred.

### Deterministic service

A Sentinel component expected to produce defined results from defined inputs, such as feature calculation, gate evaluation, or Experiment execution.

### Evidence

Traceable information admissible for research, including market data, Feature Values, Snapshots, Experiment Results, and Trade outcomes.

### Experiment

An objective, reproducible test designed to reduce uncertainty about one Hypothesis Version.

### Experiment Request

A structured AI-authored request specifying what Sentinel should test and how.

### Experiment Result / Result

The immutable, Sentinel-produced output of an Experiment Run. Interpretation is stored separately.

### Fast loop / Execution-Monitoring Loop

The market-session process that reviews and monitors already validated Trade Plans. It does not conduct ungoverned research.

### Feature

A deterministic, versioned measurement derived from admissible data. A Feature is not an AI market opinion.

### Generalization Challenge

A promotion stage testing whether a claim holds across the additional instruments, sectors, markets, periods, or regimes it claims to cover.

### Hypothesis

A durable identity for a falsifiable proposed market relationship worthy of investigation.

### Hypothesis family

A group of related variants tracked together for comparison and multiple-testing control.

### Hypothesis Version

One immutable formulation of a Hypothesis's claim, scope, assumptions, evidence, and falsification conditions.

### Immutable

Not altered in place after acceptance or completion. Corrections and changes create new linked records or versions.

### Inactive Hypothesis

Preserved research not currently consuming active capacity. Inactive does not mean deleted or disproven.

### Independent unseen-period validation

Evaluation of a frozen candidate on data not used to form or tune it. Sentinel's established default period is six months.

### Instrument

Sentinel's canonical identity for a tradable or researchable asset, independent of provider ticker spelling.

### Interpretation

An AI-authored assessment of what immutable evidence or Results imply for a Hypothesis.

### Invalidation condition

A predefined fact or event that makes a claim or Trade Plan no longer applicable.

### Journal / Research Journal

A generated context view built from permanent stores for one research scope and cycle. It is not an independent source of truth.

### Lifecycle Event

An immutable record of a domain object's transition.

### Live-eligible

Having passed research and Paper gates and being eligible for a separate live-authorization decision. It does not mean an order is authorized.

### Live Trade

An append-only record of real-capital execution under explicit authority.

### Observation

An immutable, objective AI-authored statement supported by supplied evidence. It is not a prediction, Hypothesis, or Trade Plan.

### Opportunity

See Validated Trading Opportunity.

### Paper Trade / Demo Trade

Application of a Trade Plan to unfolding market conditions without real capital. “Paper” is the canonical term; “demo” is an accepted synonym in user-facing text.

### Point-in-time integrity

The property that a historical decision uses only information available at that simulated time.

### Promotion Decision

An immutable record of objective gate outcomes, AI recommendation, policy, final decision, and reason for a stage transition.

### Promotion Pipeline

The ordered gates from Research Candidate through backtest, independent validation, applicable generalization, Paper Trading, validated opportunity, and optional live eligibility.

### Research Cycle

One identified execution of the slow Research Loop under fixed versions and an effective market date.

### Research Objective

The versioned mission, universe, horizon, success measures, risk posture, and constraints governing research.

### Research Operating System

The conceptual identity of Sentinel as evidence, memory, experiments, governance, and lifecycle—not merely an AI trading bot.

### Risk-adjusted return

Return evaluated with relevant uncertainty and downside rather than raw profit alone.

### Slow loop / Research Loop

The deliberate process, primarily after market close, that observes, maintains Hypotheses, runs and interprets Experiments, promotes research, and updates the Trade Queue.

### Snapshot / Research Snapshot

An immutable point-in-time evidence package for one Instrument and research moment.

### Store

An authoritative persistence contract for a specific domain artifact. Physical storage technology is an implementation detail.

### Superseded

Preserved but no longer current because a later version or artifact took its active place.

### Trade Plan

A versioned, actionable expression of validated research specifying instrument, direction, activation, entry, exit, invalidation, expiry, risk, uncertainty, and lineage.

### Trade Queue

The governed collection of validated Trade Plans awaiting market conditions, final review, notification, Paper action, or authorized live execution.

### Validated knowledge

A scoped claim supported by completed, governed evidence gates. It remains conditional, versioned, and open to re-evaluation.

### Validated Trading Opportunity

A complete, current, evidence-backed Trade Plan that passed required research and Paper gates and is eligible for Trade Queue admission. It is not a guarantee and does not itself grant live authority.

### Watchlist

The Sentinel-owned, versioned set of Instruments eligible for scheduled research.

## 3. Prohibited Ambiguities

- Do not use `AI`, `Sentinel`, and `Researcher` as synonyms.
- Do not call an initial backtest “validation.”
- Do not call AI-generated prose “evidence” without an external evidence source.
- Do not use “retired” to mean deleted. Prefer `inactive` or `superseded` with history preserved.
- Do not call a queued plan an executed trade.
- Do not call live eligibility live authorization.
- Do not use `ResearchMemory` as a generic mutable object; permanent Stores plus generated Journals provide memory and context.

## 4. Change Control

New domain terms or changed meanings require review of schemas, code, prompts, reports, and affected specifications. Synonyms should identify one canonical term.

