# Sentinel Vision

| Field | Value |
|---|---|
| Document ID | `SENTINEL-00` |
| Status | Foundational specification |
| Version | 1.0 |
| Authority | Architectural source of truth |
| Audience | System designers, researchers, developers, operators, reviewers, and AI agents |

## 1. Purpose

Sentinel is an autonomous quantitative research platform whose output is **validated trading opportunities**.

Sentinel exists to continuously improve its understanding of financial markets through disciplined, evidence-based research and to act only when that understanding has survived explicit validation. It converts market data and other admissible evidence into reproducible research artifacts, tested hypotheses, validated knowledge, and decision-ready trade opportunities containing concrete buy and sell conditions.

This document defines the enduring intent, boundaries, and governing principles of Sentinel. It is the first document in the Sentinel architecture set and is authoritative for all subsequent specifications and implementation decisions. Later documents may refine how the vision is realized, but they shall not weaken or contradict it. Where implementation and this document disagree, the implementation is non-conforming until either it is corrected or this document is deliberately revised.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** express normative requirements. Requirements in this document use stable identifiers so that later specifications, code, tests, and operational controls can trace back to the vision.

## 2. Vision

Sentinel will be a persistent research institution embodied in software: a system that observes markets, asks testable questions, conducts reproducible experiments, retains what it learns, challenges its own conclusions, and surfaces opportunities only when the evidence justifies them.

Sentinel is best understood as a **research operating system** and a live research scientist, not as a conventional trading bot. The AI Researcher supplies scientific reasoning; Sentinel supplies evidence, memory, deterministic computation, experiment execution, lifecycle control, and an auditable route from ideas to trades.

The platform is not defined by any particular asset class, model family, data vendor, broker, programming language, or trading style. Equities are the initial proving ground, but the architecture must not make Sentinel an equities-only or Forex-only system. Its defining capability is a governed transformation:

```text
Market and contextual data
            |
            v
     Traceable evidence
            |
            v
   AI observations
            |
            v
 AI-maintained hypotheses
            |
            v
Sentinel-run experiments
            |
            v
Independent validation
            |
            v
     Paper trading
            |
            v
Validated trading opportunities
            |
            v
Optional governed live trading
```

Every material conclusion must be traceable backward through this chain. No model score, narrative, agent opinion, or historical result is sufficient on its own. A Sentinel opportunity is the end product of a documented body of evidence, not merely a prediction.

**VIS-001:** Sentinel MUST behave as a research system first and an opportunity-generation system second.

**VIS-002:** Sentinel MUST preserve a traceable chain from every validated trading opportunity to its supporting knowledge, experiments, hypotheses, observations, evidence, and source data.

**VIS-003:** Sentinel MUST distinguish untested ideas, experimental findings, validated knowledge, and actionable opportunities as separate states with separate admission criteria.

**VIS-004:** Sentinel MUST prefer abstention to action when evidence, validation, freshness, operational readiness, or risk information is insufficient.

**VIS-005:** Sentinel MUST preserve a strict ownership boundary: stores own durable truth, the generated Research Journal owns current context, the AI Researcher owns reasoning and research ideas, and deterministic Sentinel services own measurement and experiment execution.

**VIS-006:** Sentinel MUST be designed so that live execution can be introduced as an optional, separately governed final stage; the architecture MUST NOT assume that live trading is mandatory or permanently impossible.

## 3. Objectives

### 3.1 Primary objectives

1. **Discover repeatable market structure.** Identify relationships, regimes, behaviors, and inefficiencies that may support a trading advantage after realistic costs and constraints.
2. **Produce validated opportunities.** Translate current market conditions and validated knowledge into structured, time-bounded, risk-aware candidate trades.
3. **Make research reproducible.** Record the data, assumptions, transformations, code or model versions, parameters, evaluation protocol, and results required to repeat every material experiment.
4. **Build cumulative knowledge.** Retain positive, negative, inconclusive, expired, and superseded findings so future research benefits from prior work and does not silently repeat it.
5. **Operate autonomously within governance.** Continuously observe, prioritize, investigate, test, monitor, and re-evaluate without requiring a human to direct every step, while respecting configured limits and approval boundaries.
6. **Resist false discovery.** Treat overfitting, leakage, selection bias, regime dependence, non-stationarity, unrealistic execution assumptions, and repeated testing as first-class threats.
7. **Remain explainable and auditable.** Make the origin, state, rationale, uncertainty, and ownership of each conclusion inspectable by authorized reviewers.
8. **Produce usable trade plans.** A successful research path must ultimately be capable of expressing what to buy or sell, the activation and entry price or rule, the exit price or rule, the capital and risk constraints, and the conditions under which no trade should occur.
9. **Report autonomous work.** Make overnight and intraday activity visible through concise reports covering hypotheses tested, failed, validated, advanced to the next stage, paper traded, and made eligible for live consideration, together with win rate and average profit/loss where meaningful.

### 3.2 Supporting objectives

**OBJ-001:** The platform MUST separate research-time evidence from evaluation evidence wherever the validation design requires an unbiased holdout.

**OBJ-002:** The platform MUST evaluate opportunities using risk-adjusted and implementation-aware measures, including relevant costs, liquidity, latency, capacity, and uncertainty.

**OBJ-003:** The platform MUST treat negative and inconclusive results as durable research outputs.

**OBJ-004:** The platform MUST detect when previously validated knowledge is stale, degraded, contradicted, or outside its known regime of applicability.

**OBJ-005:** The platform SHOULD support competing hypotheses and independent validation methods rather than converging prematurely on a single explanation.

**OBJ-006:** The platform SHOULD make autonomous decisions observable, reversible where practicable, and attributable to a versioned policy.

**OBJ-007:** Return targets, holding periods, validation thresholds, hypothesis capacity, and promotion criteria MUST be explicit configuration or governed policy rather than hard-coded product identity. In particular, Sentinel is not intrinsically a “3% in 3 days” system.

**OBJ-008:** Sentinel MUST operate within a low-to-moderate risk posture by default while retaining the ability to identify valid opportunities; risk controls must not be implemented as a hidden bias toward either perpetual trading or perpetual abstention.

## 4. Scope

### 4.1 In scope

Sentinel encompasses the capabilities required to turn admissible information into validated trading opportunities:

- acquisition and provenance tracking of market, fundamental, economic, alternative, and contextual data;
- data quality assessment, normalization, temporal alignment, and feature derivation;
- observation capture and research journaling;
- hypothesis formulation, prioritization, and lifecycle management;
- experiment design, execution, reproduction, comparison, and review;
- statistical, simulation-based, and model-based evaluation;
- controls for leakage, multiple testing, overfitting, and unrealistic assumptions;
- a versioned knowledge base containing claims, evidence, scope, confidence, limitations, and invalidation conditions;
- a maximum of six active research hypotheses per watched symbol by default, maintained over time rather than regenerated from scratch during every cycle;
- generation and ranking of structured trading opportunities from validated knowledge and current evidence;
- opportunity-level risk descriptions, entry conditions, exit and invalidation conditions, expected holding horizon, capacity assumptions, and expiry;
- continuous monitoring of evidence, experiments, knowledge, opportunity validity, and system health;
- audit trails, lineage, observability, access control, and governance interfaces;
- interfaces through which downstream systems or authorized humans may accept, reject, simulate, or execute an opportunity.
- paper or demo trading as a mandatory empirical promotion stage before a strategy can be considered for live use;
- market-calendar-aware pre-market review, in-session monitoring, post-market research, and user reporting;
- optional governed live trading and continuous live-strategy monitoring as a future-capable stage of the same promotion lifecycle.

The primary product output is a validated trading opportunity and its subsequent monitoring. Sentinel also owns the research lifecycle leading to that output, including backtesting, independent validation, and paper trading. Live trading is optional: a deployment may stop at notification or recommendation, while a future deployment may permit the AI Researcher to propose and Sentinel to execute live trades under a separate risk and execution specification.

### 4.2 Definition of a validated trading opportunity

A validated trading opportunity is a versioned, machine-readable and human-inspectable proposal that, at minimum:

- identifies the instrument or eligible universe;
- states the directional or relative-value thesis;
- cites the validated knowledge and current evidence that support it;
- defines activation, entry, exit, expiry, and invalidation conditions;
- provides explicit buy/sell prices when the strategy uses price levels, or equally unambiguous executable rules when static prices are inappropriate;
- reports expected return and relevant uncertainty rather than a point estimate alone;
- describes material market, model, liquidity, execution, concentration, and regime risks;
- incorporates realistic transaction costs and implementability constraints;
- declares the intended horizon, sizing inputs or sizing constraints, and capacity assumptions;
- records the data, research, model, policy, and configuration versions used;
- provides confidence and validation status using defined, calibrated semantics;
- can be independently reconstructed from retained artifacts.

An opportunity is validated only relative to explicit criteria. Validation is not a claim of certainty, profitability, or permanence.

**SCP-001:** Sentinel MUST NOT label an output as validated unless all mandatory validation gates defined by the research and promotion specifications have passed.

**SCP-002:** Opportunity publication MUST NOT erase uncertainty, dissenting evidence, known limitations, or failure conditions.

**SCP-003:** The platform MUST treat opportunity validity as time-dependent and MUST support expiry, withdrawal, suspension, and revalidation.

**SCP-004:** A hypothesis that passes discovery testing MUST be evaluated on an independent, unseen period. The established default is a distinct six-month period, while the exact duration MAY be configured when research evidence supports another choice.

**SCP-005:** A candidate that survives independent validation SHOULD be challenged across other appropriate symbols, sectors, markets, or regimes before paper trading when the hypothesis claims such generality.

**SCP-006:** No opportunity MAY become eligible for live execution without successful paper trading and an explicit live-execution authorization policy.

## 5. Non-Goals

The following are deliberately outside this vision's guarantee:

1. **Guaranteed profits.** Sentinel does not promise positive returns, eliminate loss, or make markets predictable.
2. **Unbounded autonomous trading.** The existence of an opportunity does not by itself authorize an order. Live execution is a legitimate future capability, but requires a separately specified policy, risk envelope, credentials, operational controls, and approval model.
3. **A single omniscient model.** Sentinel is not a monolithic predictor, chatbot, or large-language-model wrapper. Models are replaceable research instruments and must remain subject to evidence and governance.
4. **Advice without provenance.** Unsupported recommendations, opaque signals, and conclusions that cannot be reconstructed are not valid Sentinel outputs.
5. **Speed at any cost.** The platform does not sacrifice data integrity, experimental validity, risk controls, or auditability merely to reduce time to action.
6. **Retrofitting a story to a signal.** Explanations generated after seeing results do not substitute for hypotheses, controls, or prospective validation.
7. **Universal coverage from inception.** Sentinel need not support every asset class, venue, frequency, strategy, or jurisdiction in its initial releases.
8. **Replacing accountable humans.** The AI Researcher may eventually be permitted to make and execute live-trading decisions, but autonomy does not remove legal, fiduciary, operational, or governance accountability.
9. **Production implementation detail.** This vision does not prescribe technologies, schemas, services, deployment topology, vendors, or algorithms except where necessary to establish architectural constraints.

**NG-001:** No component may infer permission to execute live trades solely from an opportunity's validated status.

**NG-002:** Generative fluency, model confidence, or agent consensus MUST NOT be treated as empirical validation.

## 6. Core Principles

### 6.1 Evidence before assertion

All consequential claims begin as provisional. Evidence must be attributable, timestamped, quality-assessed, and appropriate to the claim. The system must expose missing, conflicting, or weak evidence rather than conceal it behind a summary.

### 6.2 Research before action

Sentinel must not collapse discovery, validation, and opportunity generation into one opaque prediction step. Promotion between lifecycle stages requires explicit criteria and preserved artifacts.

### 6.3 Falsifiability

A useful hypothesis states what observations would support it and what would refute it. Knowledge and opportunities must carry invalidation conditions. Unfalsifiable narratives may be stored as context but cannot independently justify promotion.

### 6.4 Reproducibility and lineage

Material results must be repeatable from immutable or version-addressable inputs. Transformations, environments, parameters, randomness, code, prompts, models, and policies must be recorded to the degree necessary to explain variation.

### 6.5 Temporal integrity

Sentinel must reason as if standing at the historical decision time. Point-in-time availability, revisions, publication delays, survivorship, corporate actions, and market calendars must be handled explicitly. Future information must never leak into past decisions.

### 6.6 Validation proportional to risk

Evidence thresholds must rise with uncertainty, novelty, downside, capital impact, irreversibility, and operational complexity. Validation should include appropriate out-of-sample, walk-forward, sensitivity, robustness, and stress analysis; no single technique is universally sufficient.

### 6.7 Realistic implementability

A statistically attractive pattern is not a trading opportunity unless it remains meaningful under plausible fees, spread, slippage, latency, liquidity, borrow, funding, capacity, and market-impact assumptions.

### 6.8 Separation of concerns

Data, evidence, research, knowledge, opportunity generation, portfolio decisions, risk authorization, and execution are distinct responsibilities. Their interfaces must be explicit so that confidence in one layer cannot silently grant authority to another.

The operational form of this principle is:

> **Stores own truth. The Research Journal owns context. The AI Researcher owns reasoning. Sentinel owns deterministic execution.**

Market data, calculated features, snapshots, experiment results, paper trades, live trades, and history are Sentinel-owned evidence. Observations, questions, confidence assessments, and hypotheses are AI-authored research artifacts. AI authorship does not make an artifact validated truth.

### 6.9 Uncertainty is a first-class output

Sentinel must represent uncertainty, ambiguity, model disagreement, data limitations, and regime dependence. It must not reduce complex evidence to a confidence label without defined semantics and supporting measurements.

### 6.10 Memory without dogma

The platform must retain what it learns, including failures, while allowing all knowledge to be challenged. Validated knowledge is versioned and scoped, never eternal truth.

The AI Researcher never edits history. Observations, completed experiments, and completed trades are append-only records. Hypotheses evolve through versioned events and relationships; they are never deleted merely because they fail. A hypothesis may become inactive, rejected, contradicted, or superseded, but its history remains available to prevent repeated failed research and to support later reinterpretation.

### 6.11 Safe autonomy

Autonomous processes operate within explicit permissions, budgets, rate limits, data entitlements, and escalation rules. Failures must default to a safe state. Humans must be able to inspect, pause, constrain, and override the platform according to defined authority.

### 6.12 Auditability and accountability

Every material state transition and autonomous decision must identify what changed, why, when, under which policy, and by which human or machine actor. Audit records must be durable and tamper-evident to a level appropriate to the deployment.

### 6.13 Security and compliance by design

Data rights, privacy, market rules, access controls, secrets, model supply chains, and jurisdictional constraints must be incorporated into architecture and research workflows, not added after deployment.

### 6.14 Modularity and replaceability

Data providers, models, evaluators, agents, and execution destinations must be replaceable behind stable contracts. No vendor or model is itself a source of truth.

**PRN-001:** When speed, novelty, or convenience conflicts with research integrity, risk control, or traceability, Sentinel MUST preserve integrity, control, and traceability.

**PRN-002:** Automated agents MUST operate under the same evidentiary and promotion rules as human researchers.

**PRN-003:** Every promoted claim MUST retain material contrary evidence and known limitations.

**PRN-004:** Each first-class object MUST answer one principal question: a Snapshot describes what the market looks like; an Observation states what objective fact is supported; a Journal presents what is currently understood; a Hypothesis states what deserves investigation; an Experiment records what happened when it was tested; and a Trade records what happened in the market.

**PRN-005:** Sentinel MUST build the complete v1 skeleton before optimizing breadth. Additional features, symbols, AI clients, providers, and advanced measurements belong after the end-to-end lifecycle is coherent.

## 7. System Overview

Sentinel is logically organized into cooperating capability domains. These are architectural responsibilities, not a prescribed deployment topology.

### 7.1 Evidence plane

The evidence plane acquires, validates, versions, time-aligns, and serves source data and derived evidence. It owns provenance and point-in-time semantics. It reports quality and entitlement status alongside values.

### 7.2 Research plane

The research plane converts evidence and observations into hypotheses and experiments. It manages research questions, preconditions, evaluation protocols, competing explanations, experiment execution, and reproducible result packages.

The **AI Researcher** reviews evidence, authors observations, creates and improves hypotheses, chooses what deserves investigation, requests experiments, interprets results, and recommends promotion or deactivation. It does not directly calculate authoritative market features or manufacture experiment outcomes.

By default, the AI Researcher maintains up to six active hypotheses for each watched symbol. Six is a capacity limit, not a daily generation quota. Existing hypotheses are reviewed, strengthened, weakened, refined, contradicted, or superseded as new evidence arrives. A new hypothesis is created only when capacity exists or governed prioritization makes room for it.

The **experiment service** receives structured requests and performs deterministic backtests, validation runs, and other approved experiments. The AI Researcher decides what question to ask; Sentinel executes the test and records the result.

### 7.3 Knowledge plane

The knowledge plane stores promoted claims together with scope, strength, supporting and opposing evidence, dependencies, applicable regimes, limitations, expiry or review dates, and invalidation tests. It represents the platform's current, contestable understanding.

The **Research Journal** is not an independent truth store. It is generated for a symbol and research cycle from permanent stores. It is the canonical context supplied to the AI Researcher and may contain the symbol, date, mission, recent observations, active hypotheses, active experiments, completed results, open questions, current understanding, and next research actions. Because it is regenerated, its contents remain traceable to durable records.

### 7.4 Opportunity plane

The opportunity plane combines validated knowledge with current evidence to generate, validate, rank, publish, monitor, suspend, and expire structured opportunities. It cannot bypass research or knowledge promotion gates.

The **Trade Queue** contains validated trade plans waiting for their specified market conditions. During market hours, the fast monitoring loop confirms that queued plans remain valid, observes their triggers, and notifies the user or submits an authorized action. It does not conduct open-ended research.

### 7.5 Governance and control plane

The governance and control plane defines identities, permissions, policies, validation gates, resource budgets, model and data approvals, audit records, human review points, and emergency controls. It governs both human and autonomous actors.

### 7.6 Observability plane

The observability plane measures data health, research throughput, experiment reproducibility, knowledge freshness, opportunity performance, model drift, policy compliance, and platform reliability. Operational health and research validity are separate concerns and both must be visible.

### 7.7 External boundary

Portfolio construction, capital allocation, pre-trade risk authorization, order management, brokerage, exchange connectivity, reconciliation, and post-trade accounting may consume Sentinel outputs through governed interfaces. Later architecture documents may incorporate these capabilities into an optional live-trading deployment, but must preserve their distinct authorities.

**SYS-001:** Each capability domain MUST expose versioned contracts and explicit ownership of state transitions.

**SYS-002:** No external consumer MAY reinterpret a provisional research result as a validated opportunity without completing the defined promotion process.

**SYS-003:** Failures in data quality, lineage, validation, policy compliance, or monitoring MUST be able to block or withdraw an opportunity independently of model output.

## 8. Research Lifecycle

The canonical Sentinel research lifecycle is continuous, stateful, and non-linear. Findings may move forward, return for revision, branch into competing hypotheses, or be rejected.

### 8.1 Observe

Sentinel monitors admissible evidence for anomalies, changes, recurring structures, knowledge conflicts, performance degradation, and unanswered questions. An observation records what was seen without prematurely claiming why it occurred.

### 8.2 Formulate

Promising observations become falsifiable hypotheses. Each hypothesis declares the proposed mechanism or predictive relationship, eligible universe, horizon, assumptions, expected effect, competing explanations, evaluation method, and failure conditions. The AI Researcher manages a continuing portfolio of no more than six active hypotheses per symbol by default; it does not discard their histories or replace the complete set every day.

### 8.3 Design

An experiment plan selects point-in-time data, controls, benchmarks, metrics, cost assumptions, sample partitions, robustness checks, and acceptance criteria appropriate to the hypothesis. Exploratory and confirmatory work must be distinguished.

### 8.4 Execute

Experiments run in a controlled and reproducible environment. Results include failures, diagnostics, sensitivity, uncertainty, and deviations from the plan—not only headline performance.

### 8.5 Challenge

Sentinel attempts to disprove the apparent result through leakage checks, alternative specifications, perturbation, placebo tests, regime analysis, walk-forward evaluation, independent reproduction, and other appropriate adversarial tests.

The canonical promotion sequence is:

```text
Initial backtest
      |
      v
Independent unseen-period validation (six months by default)
      |
      v
Cross-symbol, sector, market, or regime validation where applicable
      |
      v
Paper/demo trading
      |
      v
Validated trading opportunity
      |
      v
Optional authorized live trading
      |
      v
Continuous monitoring and re-evaluation
```

Failure does not delete the hypothesis. It records evidence, changes lifecycle state, and returns the research question for refinement, supersession, or later reconsideration.

### 8.6 Validate and promote

A result may become validated knowledge only after satisfying defined evidence and review gates. Promotion records the claim's scope, strength, limitations, dependencies, and invalidation conditions. Rejection and inconclusive outcomes are also recorded.

### 8.7 Synthesize an opportunity

When current evidence matches the conditions of applicable validated knowledge, Sentinel may construct a candidate opportunity. It then tests freshness, implementability, risk completeness, portfolio-facing constraints, and policy compliance before publication as validated.

### 8.8 Monitor and learn

Published opportunities, including those not executed, are monitored against their expected conditions and outcomes. New evidence can confirm, weaken, suspend, expire, or invalidate both the opportunity and its supporting knowledge. Outcomes feed new observations; they do not silently rewrite past research.

### 8.9 Daily operating rhythm

Sentinel contains two deliberately separate loops:

1. The **slow research loop** runs primarily after market close. It updates data, creates observations, maintains hypotheses, runs or reviews experiments, validates findings, and updates the Trade Queue.
2. The **fast execution-monitoring loop** runs around and during market hours. It reviews queued plans before the market opens, confirms that their assumptions still hold, watches activation and invalidation conditions, notifies the user, and executes only when separately authorized.

The fast loop must not invent research under intraday time pressure. The slow loop must not behave as though a successful historical experiment is an immediate live-trading instruction.

```text
Observe -> Formulate -> Design -> Execute -> Challenge
   ^                                          |
   |                                          v
Learn <- Monitor <- Opportunity <- Promote/Reject
                    |                 |
                    +---- withdraw ---+
```

**RLC-001:** Every lifecycle transition MUST be explicit, attributable, timestamped, policy-checked, and auditable.

**RLC-002:** Promotion criteria MUST be specified before confirmatory evaluation wherever practicable.

**RLC-003:** Failure at a later stage MUST NOT be hidden; it MUST update the status of affected opportunities and trigger review of dependent knowledge.

**RLC-004:** The lifecycle MUST support rejection, revision, suspension, expiry, supersession, and re-entry rather than only forward progression.

**RLC-005:** Sentinel MUST produce a pre-market or morning report and a research-cycle summary that expose work completed while the user was away, including stage counts and meaningful performance statistics.

**RLC-006:** Market open, close, holidays, time zones, and data publication timing MUST be explicit inputs to scheduling and opportunity validity.

## 9. Success Criteria

Sentinel succeeds when it creates a trustworthy, improving research process—not merely when a backtest or isolated trade is profitable. Success must be evaluated across the following dimensions.

### 9.1 Research integrity

- Material conclusions are reproducible from retained, versioned artifacts.
- Point-in-time and leakage controls are demonstrably effective.
- Positive, negative, and inconclusive experiments are preserved.
- Independent reruns reach materially consistent conclusions within defined tolerance.
- Promotion rules are enforced uniformly across humans, models, and agents.

### 9.2 Opportunity quality

- Every published opportunity meets the required schema and validation gates.
- Realized and paper outcomes are evaluated net of realistic implementation costs.
- Expected probabilities and confidence measures are calibrated over relevant cohorts.
- Opportunities state their applicable regime, horizon, risks, and invalidation conditions.
- Stale or contradicted opportunities are detected and withdrawn within defined service objectives.

### 9.3 Knowledge quality

- Claims are traceable to evidence and experiments.
- Dependencies and contradictory evidence are visible.
- Knowledge freshness and review status are measurable.
- Superseded or invalidated knowledge remains historically inspectable and cannot silently support new opportunities.

### 9.4 Autonomy and governance

- The platform can conduct bounded research cycles without continuous human direction.
- Autonomous actions remain within permissions, resource budgets, and policy.
- Humans can inspect and intervene without bypassing audit controls.
- Exceptions, overrides, and blocked actions are recorded and reviewed.
- The system can legitimately conclude “do nothing” while remaining capable of surfacing and progressing opportunities when evidence satisfies the configured standard.

### 9.5 Operational fitness

- Data and system health are measured separately from research conclusions.
- Recovery preserves lineage and avoids duplicate or inconsistent state transitions.
- Security, entitlement, privacy, and compliance controls are testable.
- Component replacement does not compromise historical reproducibility.

### 9.6 Outcome evaluation

Financial outcomes matter, but they must be interpreted carefully. Sentinel should ultimately demonstrate that its validated opportunities exhibit useful risk-adjusted performance after realistic costs across appropriate out-of-sample and live-observation periods. Evaluation must also consider drawdown, tail behavior, turnover, capacity, stability, opportunity frequency, and correlation with existing exposures.

Reports should distinguish at least: hypotheses considered, tested, failed, advanced through independent validation, promoted to paper trading, made eligible for live trading, and currently active. Where sample size permits, they should report win rate, average profit, average loss, expectancy, drawdown, and other configured risk-adjusted measures.

No single metric is the definition of success. Exact metrics, thresholds, observation windows, and promotion gates belong in later research, risk, and operational specifications.

**SUC-001:** Backtest performance alone MUST NOT satisfy the success criteria for Sentinel or for an opportunity-generating method.

**SUC-002:** Platform evaluation MUST include both process measures and outcome measures.

**SUC-003:** Metrics MUST be interpreted within declared samples, regimes, costs, and uncertainty; they MUST NOT be presented as timeless guarantees.

## 10. Future Vision

Sentinel should evolve from a governed research platform into a durable, multi-agent market-learning institution. Its long-term direction includes:

- continuous research across multiple asset classes, horizons, venues, and information domains;
- specialized research agents that propose, critique, reproduce, and monitor work under shared governance;
- causal, statistical, simulation, and machine-learning methods used as complementary tools;
- a knowledge graph capable of expressing claims, evidence, dependencies, contradictions, regimes, and decay;
- automated red-team research that actively searches for leakage, fragility, hidden exposure, and invalid assumptions;
- calibrated portfolio-facing opportunity sets rather than isolated signals;
- simulation and shadow operation as standard stages before any broader authority is granted;
- federated or isolated research environments for restricted data and jurisdiction-specific controls;
- controlled live execution only if a separate architecture establishes capital authority, risk management, kill switches, reconciliation, incident response, and regulatory compliance;
- eventual AI-directed live trading, when explicitly authorized, using the same evidence, validation, audit, and monitoring discipline proven in paper trading;
- learning from the outcomes of both acted-on and unacted-on opportunities while avoiding hindsight contamination;
- an institutional memory that can explain not only what Sentinel believes, but how, when, and why that belief changed.

The future platform may become highly autonomous. Its evidentiary standard must become stronger—not weaker—as autonomy, capital impact, and complexity increase.

**FUT-001:** Expansion of capability MUST preserve the lifecycle, traceability, and governance principles defined here.

**FUT-002:** Live execution authority, when introduced, MUST be explicitly granted by a separate approved specification and MUST remain separable from research validation. The specification MAY authorize the AI Researcher to make live decisions within a bounded mandate.

**FUT-003:** Sentinel's long-term optimization target MUST include robustness, learning quality, and controlled risk—not raw return alone.

## 11. Architectural Authority and Change Control

This document governs all subsequent Sentinel architecture documents. Those documents are expected to define philosophy, system architecture, research process, domain model, AI behavior, evidence and journal models, hypothesis and experiment lifecycles, opportunity queues, promotion gates, coding standards, interfaces, security, operations, and terminology.

Every subsequent specification MUST:

1. identify the vision requirements it realizes;
2. preserve the distinction between research artifacts, validated knowledge, and validated trading opportunities;
3. preserve the boundary between opportunity publication and trade authorization;
4. define conflicts or deliberate deviations explicitly rather than by implication;
5. remain testable through requirements, acceptance criteria, or measurable controls.

Changes to this document require deliberate architectural review because they alter the meaning of the entire system. A change record must state the motivation, affected requirements, migration implications, risks, and documents that require reconciliation.

## 12. Foundational Statement

> Sentinel exists to continuously improve its understanding of financial markets through disciplined, evidence-based research, and to act only when that understanding has been validated.

Its primary output is a validated trading opportunity: a low-to-moderate-risk, evidence-backed plan that states what to buy or sell, when to enter, when to exit, how the idea was tested, and when not to trade. Paper trading proves the operational path; optional live trading is the governed future end of that path.

This statement is the governing test for the architecture. A feature, model, agent, workflow, or integration belongs in Sentinel only if it advances that purpose without compromising the principles in this document.
