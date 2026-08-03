# Sentinel Philosophy

| Field | Value |
|---|---|
| Document ID | `SENTINEL-01` |
| Status | Normative architecture specification |
| Version | 1.0 |
| Depends on | `00-Vision.md` |

## 1. Purpose

This document defines the beliefs that govern every Sentinel design and implementation decision. It translates the vision into durable decision rules for humans, AI systems, and software components. When multiple implementations satisfy a functional requirement, the implementation that best preserves these principles is preferred.

## 2. Responsibilities

The philosophy shall:

- define how Sentinel distinguishes facts, context, reasoning, and action;
- define the standard of evidence required before promotion;
- protect research history from hindsight and silent revision;
- constrain AI autonomy without reducing the AI Researcher to a passive narrator;
- keep the system understandable while it grows;
- provide a consistent basis for resolving architectural ambiguity.

It does not define object fields, storage technology, numerical thresholds, or deployment topology. Those belong to later specifications.

## 3. Governing Principles

### 3.1 Research before trading

Sentinel is an autonomous quantitative research platform. Trading is the downstream expression of validated research, not the starting point.

**PHI-001:** Every trading opportunity MUST be supported by a traceable research path.

**PHI-002:** No component MAY bypass the research lifecycle because an idea appears intuitively convincing or urgent.

### 3.2 Evidence over opinion

Market data, calculated measurements, experiment results, and trade outcomes are evidence. Interpretations of that evidence are research artifacts. Fluent language, model confidence, reputation, and agreement do not transform an interpretation into a fact.

**PHI-003:** Material claims MUST identify their supporting evidence.

**PHI-004:** Unsupported AI output MUST remain unvalidated regardless of apparent quality.

### 3.3 Scientific method

Sentinel observes, hypothesizes, tests, challenges, validates, and learns. A hypothesis is valuable because it can reduce uncertainty through testing, not because it tells a compelling story.

**PHI-005:** Hypotheses MUST be falsifiable and state failure conditions.

**PHI-006:** Sentinel MUST seek disconfirming evidence and plausible alternative explanations.

**PHI-007:** Confirmatory tests SHOULD define their evaluation criteria before results are inspected.

### 3.4 Immutable history

The AI Researcher never edits history. New evidence is appended; old evidence remains inspectable. Corrections supersede records rather than silently replacing them. Failed and inconclusive work is institutional memory.

**PHI-008:** Completed Observations, Experiments, Paper Trades, and Live Trades MUST be immutable.

**PHI-009:** A correction MUST reference the record it corrects and MUST NOT erase the original.

**PHI-010:** Failed hypotheses and experiments MUST remain discoverable so Sentinel can learn from them.

### 3.5 Ownership of truth, context, reasoning, and execution

Sentinel uses four explicit ownership boundaries:

| Concern | Owner | Meaning |
|---|---|---|
| Durable truth | Permanent stores | Versioned evidence and history |
| Current context | Research Journal | Generated view of relevant stored records |
| Reasoning | AI Researcher | Observations, questions, hypotheses, interpretations, and recommendations |
| Deterministic execution | Sentinel services | Features, backtests, validation runs, monitoring, and authorized orders |

The Journal is not an independent database. The AI is not an authority over historical results. Sentinel services do not invent market meaning.

**PHI-011:** Stores MUST own the authoritative persisted representation of evidence and lifecycle history.

**PHI-012:** The Research Journal MUST be generated from stores and MUST NOT become a second source of truth.

**PHI-013:** The AI Researcher MUST own research reasoning but MUST NOT manufacture authoritative measurements or experiment outcomes.

**PHI-014:** Sentinel MUST execute requested experiments deterministically and return results without interpreting them as a research conclusion.

### 3.6 Sentinel records; the AI reasons

Sentinel itself has no market opinion. It calculates, validates, records, schedules, and enforces policy. The AI Researcher interprets evidence, decides what merits investigation, requests experiments, and evaluates whether the accumulated case justifies promotion.

This does not make the AI unrestricted. The AI works within schemas, evidence rules, hypothesis capacity, promotion gates, resource budgets, and risk policy.

**PHI-015:** Deterministic components MUST NOT label market conditions bullish, bearish, attractive, or uninteresting unless applying a formally specified classification rule.

**PHI-016:** The AI Researcher MAY conclude that no action is justified and MAY recommend an opportunity when the evidence satisfies the configured standard.

### 3.7 Confidence is earned

Confidence is a state derived from the strength, independence, quantity, freshness, and consistency of evidence. It is not a stylistic choice and must not increase merely because a claim has been repeated.

**PHI-017:** Confidence changes MUST cite new evidence or a changed evaluation.

**PHI-018:** Confidence semantics MUST be calibrated and consistent across comparable artifacts.

### 3.8 Hypotheses evolve; history does not disappear

Sentinel maintains a continuing portfolio of research questions. The default capacity is six active hypotheses per symbol. Six is a ceiling, not a requirement to generate six ideas every day.

A hypothesis may be refined, contradicted, made inactive, or superseded. Its identity and history remain. “Retirement” must never mean deletion or loss of accumulated evidence.

**PHI-019:** The AI Researcher MUST review existing hypotheses before creating replacements.

**PHI-020:** Hypothesis evolution MUST be represented through versioned changes or events.

**PHI-021:** A new hypothesis MUST NOT be created merely to restate an existing hypothesis.

### 3.9 One object, one question

Each first-class object has one principal purpose:

| Object | Principal question |
|---|---|
| Snapshot | What did the market evidence look like at this time? |
| Observation | What objective statement is supported by that evidence? |
| Journal | What context does the Researcher need now? |
| Hypothesis | What proposed relationship deserves investigation? |
| Experiment | What happened when the hypothesis was tested? |
| Trade Plan | Under what conditions is action justified? |
| Trade | What happened when the plan met the market? |

**PHI-022:** A class or service SHOULD have one primary responsibility and one reason to change.

**PHI-023:** Generic records SHOULD NOT replace distinct domain objects when their ownership or lifecycle differs.

### 3.10 Reproducibility over convenience

Research must be reconstructable from point-in-time inputs, code, configuration, policies, prompts, models, and random seeds as applicable.

**PHI-024:** A material result that cannot be reproduced MUST NOT be promoted.

**PHI-025:** Historical experiments MUST use only information available at the simulated decision time.

### 3.11 Validation must become harder, not easier

Promotion is an escalating burden of proof:

```text
Initial Backtest
      -> Independent Unseen-Period Validation
      -> Cross-Market or Regime Validation where applicable
      -> Paper Trading
      -> Validated Opportunity
      -> Optional Authorized Live Trading
```

Passing one stage permits entry to the next; it does not prove universal validity.

**PHI-026:** Later validation stages MUST use evidence not consumed in forming or tuning the hypothesis wherever practicable.

**PHI-027:** Paper trading MUST precede eligibility for live trading.

### 3.12 Risk is part of the research result

Sentinel targets consistent, positive risk-adjusted outcomes under a low-to-moderate default risk posture. A profitable result that depends on unacceptable drawdown, leverage, liquidity, concentration, or tail exposure is not a successful result.

**PHI-028:** Opportunity evaluation MUST include downside, uncertainty, costs, and implementability.

**PHI-029:** “Do nothing” MUST remain a valid output, but safety controls MUST NOT be implemented as an undocumented bias that prevents all action.

### 3.13 Configuration over accidental doctrine

The original examples—two years of discovery data, six months of unseen validation, short holding periods, and specific return targets—are useful defaults or research designs, not universal truths. The six-active-hypothesis limit is the agreed default capacity and may only change through governance.

**PHI-030:** Return targets, holding periods, data windows, thresholds, and cost assumptions MUST be explicit and versioned.

**PHI-031:** Sentinel MUST NOT be defined as a “3% in 3 days” system.

### 3.14 Slow research, fast monitoring

The research loop and execution-monitoring loop have different purposes and tempos. After market close, Sentinel performs deliberate research. Around and during market hours, it monitors already validated plans and their conditions.

**PHI-032:** Intraday urgency MUST NOT weaken research standards.

**PHI-033:** The fast loop MUST NOT generate unvalidated strategies in response to market movement.

### 3.15 Simplicity first

Sentinel must complete a coherent end-to-end skeleton before expanding its breadth. Five reliable core measurements are more valuable than fifty poorly governed ones. One well-supported hypothesis is more valuable than ten weak ideas.

**PHI-034:** v1 work MUST prioritize a complete vertical research lifecycle over additional providers, symbols, features, models, or optimization.

**PHI-035:** Abstractions MUST be introduced to solve demonstrated responsibilities, not hypothetical complexity.

### 3.16 Replaceable intelligence

The AI Researcher is a role, not a particular model. Better models and multiple specialized researchers may be introduced without changing the research record or deterministic platform contracts.

**PHI-036:** Prompts, models, and AI providers MUST be versioned dependencies.

**PHI-037:** No AI provider MAY become the system of record.

### 3.17 Safe, accountable autonomy

Autonomy is the ability to continue useful research without constant direction. It is not permission to evade policy. Human operators must be able to understand what Sentinel did while they were away and intervene within a defined authority model.

**PHI-038:** Autonomous actions MUST be attributable, bounded, and reportable.

**PHI-039:** Live execution, when introduced, MUST require explicit authority distinct from research promotion.

## 4. Decision Tests

Before accepting a design, reviewers should ask:

1. Does it preserve evidence and history?
2. Is the owner of truth, context, reasoning, and execution unambiguous?
3. Can a result be reproduced and challenged?
4. Does it keep research separate from intraday monitoring?
5. Does it make an assumption configurable when evidence may change it?
6. Does it keep the v1 skeleton simple?
7. Can Copilot implement it without inventing behavior?
8. Could the user understand what occurred while away?
9. Does it permit safe abstention and justified action?
10. Does it preserve a governed route to optional live trading?

## 5. Future Extensions

Future versions may introduce research-agent teams, independent AI critics, causal analysis, portfolio-level research, automated feature requests, new asset classes, and bounded AI-directed live execution. Every extension remains subject to the same philosophy.

## 6. Out of Scope

This document does not select AI models, databases, brokers, data vendors, feature formulas, return thresholds, or programming frameworks. It does not authorize live capital.
