# Sentinel Research Process

| Field | Value |
|---|---|
| Document ID | `SENTINEL-03` |
| Status | Normative process specification |
| Version | 1.0 |
| Depends on | `00-Vision.md`, `01-Philosophy.md`, `02-Architecture.md` |

## 1. Purpose

This document defines the scientific process through which Sentinel converts market evidence into validated trading opportunities. It specifies research stages, responsibilities, gates, iteration rules, and the separation between deliberate research and market-session monitoring.

## 2. Research Mission

The AI Researcher's mission is to discover, test, improve, validate, and maintain trading hypotheses capable of producing consistent positive risk-adjusted returns. Sentinel supplies the laboratory: evidence, deterministic measurements, experiments, memory, policies, and operational controls.

The research objective is configurable. Sentinel is not bound to a fixed return such as 3% over three days. Each research program states its universe, horizon, risk posture, target measures, cost model, and promotion standard.

**RSP-001:** Every Research Cycle MUST operate under a versioned Research Objective.

**RSP-002:** A Research Objective MUST define success in risk-adjusted and implementation-aware terms.

## 3. Roles

### 3.1 Sentinel

Sentinel:

- owns the watchlist and research schedule;
- acquires and validates evidence;
- calculates deterministic features;
- constructs Snapshots and Journals;
- enforces schemas, capacity limits, policy, and resource budgets;
- executes Experiments requested through approved contracts;
- records all artifacts and transitions;
- operates paper trading and market monitoring;
- produces reports and, when authorized, executes orders.

Sentinel does not form undocumented opinions about market meaning.

### 3.2 AI Researcher

The AI Researcher:

- reviews the Journal and new Snapshot;
- authors evidence-linked Observations;
- maintains the continuing hypothesis portfolio;
- chooses questions worthy of investigation;
- creates structured Experiment Requests;
- interprets recorded results;
- seeks disproof and competing explanations;
- recommends promotion, revision, inactivity, or supersession;
- explains uncertainty and next actions.

The AI Researcher does not invent data, calculate authoritative experiment outcomes, modify history, bypass gates, or acquire live-trading authority from research confidence.

### 3.3 Policy and promotion engine

The policy engine checks whether objective gate conditions have been met. It may reject an AI recommendation that violates schema, evidence, capacity, risk, or promotion policy. It may not create research conclusions of its own.

### 3.4 Human operator

The human operator owns product direction and configured authority. Depending on deployment policy, the operator may review exceptions, approve live authority, pause the system, change the watchlist or objectives, and inspect or override permitted decisions. Overrides are recorded; they do not rewrite evidence.

## 4. Two Operating Loops

### 4.1 Slow Research Loop

Runs primarily after the relevant market closes:

```text
Refresh Evidence
      -> Generate Snapshot
      -> Build Journal
      -> Observe
      -> Maintain Hypotheses
      -> Request Experiments
      -> Execute Experiments
      -> Interpret Results
      -> Apply Promotion Gates
      -> Update Trade Queue
      -> Report
```

This loop may span multiple cycles. It values rigor over latency.

### 4.2 Fast Execution-Monitoring Loop

Runs before and during relevant market sessions:

```text
Review Queued Plans
      -> Refresh Current Conditions
      -> Confirm Validity
      -> Monitor Entry/Exit/Invalidation
      -> Notify or Execute if Authorized
      -> Record Outcomes
```

This loop acts only on previously validated plans. It does not create or promote new hypotheses under intraday pressure.

**RSP-003:** The two loops MUST have separate responsibilities, schedules, and policies.

**RSP-004:** Fast-loop observations MAY trigger a later research question but MUST NOT bypass slow-loop validation.

## 5. Research Cycle

### 5.1 Open the cycle

A Research Cycle identifies its effective market date, symbols, objective, configuration, available resource budget, code version, feature set, AI contract, and policy versions.

**RSP-005:** A cycle MUST be uniquely identified and auditable.

### 5.2 Acquire and qualify evidence

Sentinel incrementally refreshes the required data and verifies completeness, freshness, temporal ordering, schema, corporate actions, and point-in-time availability. A failed quality gate blocks affected downstream work.

**RSP-006:** Evidence quality status MUST accompany the evidence.

**RSP-007:** Missing or stale evidence MUST NOT be silently imputed by the AI Researcher.

### 5.3 Calculate features

The Feature Engine calculates the configured measurements with versioned formulas and parameters. The initial skeleton uses a deliberately small feature set. Research may later justify additions.

**RSP-008:** Feature additions MUST answer an identified research need or platform requirement.

### 5.4 Create a Snapshot

For every watched symbol eligible for research, Sentinel creates a point-in-time Snapshot. The Snapshot records evidence; it does not summarize what the evidence “means.”

**RSP-009:** A Snapshot MUST be immutable after creation.

### 5.5 Generate the Journal

Sentinel constructs the symbol's Journal from permanent stores and the current cycle context. The Journal typically includes mission, recent Observations, active Hypotheses, active and completed Experiments, Paper Trades, live state if any, open questions, and prior next actions.

**RSP-010:** The Journal MUST be generated, not manually maintained as a competing history.

**RSP-011:** Journal selection rules MUST prevent important failure evidence from disappearing merely because it is old.

### 5.6 Observe

The AI Researcher reads the Journal and new Snapshot and returns structured Observations. An Observation is an objective statement supported by cited evidence; it is not a strategy, prediction, or trade instruction.

**RSP-012:** Every Observation MUST cite the Snapshot or evidence from which it was derived.

**RSP-013:** Duplicate observations SHOULD be linked or suppressed rather than appended as artificial confirmation.

### 5.7 Maintain hypotheses

The Researcher reviews existing Hypotheses before proposing changes. It may strengthen or weaken confidence, refine a version, add supporting or opposing evidence, make a hypothesis inactive, supersede it, or create a new one if capacity exists.

The default maximum is six active Hypotheses per symbol. Sentinel need not fill all six positions. Hypotheses may compete, including mutually incompatible explanations.

**RSP-014:** Six active Hypotheses per symbol MUST be treated as the default capacity limit, not a generation target.

**RSP-015:** Hypothesis history MUST survive failure, inactivity, and supersession.

**RSP-016:** Confidence changes MUST reference evidence or Experiment Results.

### 5.8 Design an Experiment

The AI Researcher requests an Experiment to reduce uncertainty about one Hypothesis. A valid request defines:

- hypothesis and version under test;
- research question;
- eligible universe and period;
- input data and features;
- signal, entry, exit, and invalidation semantics as applicable;
- benchmark and null comparison;
- metrics and acceptance criteria;
- transaction costs and implementation assumptions;
- sample partition and point-in-time controls;
- robustness and sensitivity checks;
- known limitations.

Sentinel validates the request before allocating work.

**RSP-017:** The AI Researcher MUST request Experiments; it MUST NOT claim to have executed them.

**RSP-018:** A confirmatory Experiment SHOULD specify acceptance criteria before execution.

### 5.9 Execute and record

Sentinel runs the Experiment in a reproducible environment and records the complete result, including failures, warnings, diagnostics, cost assumptions, sensitivity, and uncertainty.

**RSP-019:** Experiment Results MUST be recorded even when code fails or the result is negative or inconclusive.

**RSP-020:** The result MUST distinguish statistical performance from implementability.

### 5.10 Challenge the result

Before promotion, Sentinel and the Researcher attempt to disprove the finding. Applicable challenges include:

- temporal leakage and look-ahead checks;
- survivorship and selection-bias checks;
- alternative parameterizations;
- subperiod and regime analysis;
- perturbation and sensitivity analysis;
- placebo or null tests;
- benchmark comparison;
- multiple-testing correction;
- realistic costs, slippage, liquidity, capacity, and latency;
- independent reproduction.

**RSP-021:** Challenge activity MUST be proportional to the intended capital impact and novelty.

### 5.11 Interpret

The regenerated Journal presents the immutable result to the AI Researcher. The Researcher explains whether and how the result changes the Hypothesis, what uncertainty remains, and what should happen next.

**RSP-022:** Interpretation MUST NOT modify the recorded Experiment Result.

## 6. Promotion Lifecycle

### 6.1 Stage 0 — Research candidate

An active, falsifiable Hypothesis with sufficient evidence to justify testing.

### 6.2 Stage 1 — Initial backtest

The candidate is evaluated over a configured discovery or initial evaluation period. The original project example uses approximately two years of historical data, but the window is not universal.

Pass permits independent validation; it does not validate the strategy.

### 6.3 Stage 2 — Independent unseen-period validation

The strategy is evaluated without retuning on information not used to create it. The established default is a distinct six-month period. A three-month or other window may be used only when justified and configured.

**RSP-023:** Independent validation MUST prevent information from the validation period influencing hypothesis formation or tuning.

### 6.4 Stage 3 — Generalization challenge

When the hypothesis claims broader applicability, it is tested across appropriate symbols, sectors, markets, periods, or regimes. A symbol-specific hypothesis may instead document why generalization is not claimed.

### 6.5 Stage 4 — Paper trading

Sentinel operates the candidate against unfolding market conditions without real capital. Paper trading tests the full operational plan, not only its mathematical signal.

Paper evaluation includes decision timing, fill assumptions, costs, missed entries, exits, invalidations, operational errors, win rate, average profit/loss, expectancy, drawdown, and sample sufficiency.

**RSP-024:** A minimum paper duration or sample requirement MUST be configured before live eligibility.

### 6.6 Stage 5 — Validated trading opportunity

A successful candidate becomes a Trade Plan eligible for the Trade Queue. It specifies what to buy or sell, entry, exit, sizing constraints, risk, expiry, invalidation, supporting evidence, and expected outcome distribution.

### 6.7 Stage 6 — Optional live eligibility

Only a separately authorized deployment may act with real capital. Eligibility does not equal automatic execution. Current conditions, portfolio constraints, risk, and execution policy remain decisive.

### 6.8 Continuous monitoring

Paper and live performance feed new evidence. Degradation can suspend opportunities, return a strategy to research, or supersede the active version. Historical records remain.

**RSP-025:** No promotion stage MAY erase results from earlier stages.

**RSP-026:** Failure at any stage MUST produce an explicit state and reason.

**RSP-027:** A strategy MUST NOT be promoted solely because another strategy performed worse.

## 7. State Outcomes

Research is not binary. Valid outcomes include:

- `active` — currently being investigated;
- `awaiting_experiment` — a valid request exists;
- `testing` — execution is in progress;
- `supported` — evidence increased confidence without completing promotion;
- `contradicted` — evidence materially opposes the claim;
- `inconclusive` — the test did not reduce uncertainty sufficiently;
- `inactive` — not currently consuming active research capacity;
- `superseded` — a later version or hypothesis replaces active use;
- `blocked` — data, tooling, policy, or resource limitations prevent progress;
- `promoted` — the artifact has entered the next governed stage.

“Deleted” is not a research outcome. The detailed lifecycle is defined in the relevant domain specifications.

## 8. Research Prioritization

The AI Researcher proposes priorities based on expected information gain, evidence quality, novelty, relevance to the objective, estimated cost, active capacity, and potential risk-adjusted value. Sentinel enforces budgets and fairness across watched symbols.

**RSP-028:** Priority MUST NOT be based on narrative excitement alone.

**RSP-029:** Repeatedly testing minor variations of one idea MUST be visible as a related research family for multiple-testing control.

## 9. Reporting

### 9.1 Cycle report

After a Research Cycle, Sentinel reports:

- symbols reviewed and blocked;
- Observations created or deduplicated;
- Hypotheses created, changed, supported, contradicted, inactive, or superseded;
- Experiments requested, executed, failed, and completed;
- candidates entering or failing each promotion stage;
- Paper Trades started, active, or completed;
- Trade Queue additions, suspensions, expiries, and withdrawals;
- data, policy, or operational exceptions;
- next scheduled work.

### 9.2 Pre-market report

Before a relevant session, Sentinel reports active queued plans, current validity, exact activation and invalidation conditions, material changes, and whether the deployment will notify, paper trade, or execute if triggered.

### 9.3 Performance report

Where samples permit, Sentinel reports counts, win rate, average profit, average loss, expectancy, drawdown, exposure, turnover, cost, and risk-adjusted measures separately for backtest, validation, paper, and live stages.

**RSP-030:** Reports MUST label sample, period, stage, and cost assumptions.

## 10. Autonomy and Escalation

Sentinel may autonomously execute ordinary in-policy research steps. It must escalate when required evidence is unavailable, an AI request violates policy, a schema or data contract changes, risk exceeds authority, a live action requires approval, or an incident affects trustworthy operation.

**RSP-031:** Autonomy MUST stop at the boundary of configured authority, not at an arbitrary discomfort threshold.

**RSP-032:** A blocked action MUST record the reason and the information or authority needed to proceed.

## 11. Future Extensions

Future research may include AI Critic and Reproducer roles, automatic feature requests, portfolio-level hypotheses, causal experiments, alternative data, research across multiple frequencies, and adaptive resource allocation. These extensions must preserve the same evidence, lineage, and promotion discipline.

## 12. Out of Scope

This document does not prescribe exact statistical tests, return thresholds, model selection, order types, capital allocation, or broker behavior. It defines the process within which those choices must be specified.