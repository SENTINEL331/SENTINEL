# Sentinel Software Architecture Manual

This directory is the architectural source of truth for Sentinel. Read the documents in numerical order; later specifications refine earlier ones and must not contradict them.

## Reading Order

1. [00-Vision.md](00-Vision.md) — why Sentinel exists and what success means.
2. [01-Philosophy.md](01-Philosophy.md) — principles governing every decision.
3. [02-Architecture.md](02-Architecture.md) — system boundaries, subsystems, and dependencies.
4. [03-Research-Process.md](03-Research-Process.md) — the scientific and promotion process.
5. [04-Domain-Model.md](04-Domain-Model.md) — first-class objects, ownership, and lifecycles.
6. [05-AI-Constitution.md](05-AI-Constitution.md) — permanent rules for AI behavior.
7. [06-Observation.md](06-Observation.md) — objective AI-authored evidence statements.
8. [07-Journal.md](07-Journal.md) — generated research context.
9. [08-Hypothesis.md](08-Hypothesis.md) — continuing falsifiable research propositions.
10. [09-Experiment.md](09-Experiment.md) — reproducible objective tests.
11. [10-Trade-Queue.md](10-Trade-Queue.md) — validated plans awaiting market conditions.
12. [11-Promotion-Pipeline.md](11-Promotion-Pipeline.md) — escalating evidence gates.
13. [12-Coding-Standards.md](12-Coding-Standards.md) — implementation rules for humans and coding agents.
14. [13-AI-Contract.md](13-AI-Contract.md) — structured Sentinel/AI integration boundary.
15. [14-Glossary.md](14-Glossary.md) — canonical terminology.
16. [15-System-Lifecycle.md](15-System-Lifecycle.md) — daily runtime and failure behavior.
17. [ADR.md](ADR.md) — rationale for accepted architectural decisions.

## Authority

The Vision and Philosophy govern intent. Architecture and Research Process govern system behavior. Detailed subsystem documents refine those requirements. The Glossary governs terminology. ADRs explain decisions but do not override normative requirements.

If code and documentation disagree, the code is non-conforming until the implementation or an approved documentation change resolves the conflict.

## Requirement Prefixes

| Prefix | Document |
|---|---|
| `VIS`, `OBJ`, `SCP`, `NG`, `PRN`, `SYS`, `RLC`, `SUC`, `FUT` | Vision |
| `PHI` | Philosophy |
| `ARC` | Architecture |
| `RSP` | Research Process |
| `DOM` | Domain Model |
| `AIC` | AI Constitution |
| `OBS` | Observation |
| `JRN` | Journal |
| `HYP` | Hypothesis |
| `EXP` | Experiment |
| `TRQ` | Trade Queue |
| `PRM` | Promotion Pipeline |
| `COD` | Coding Standards |
| `AICN` | AI Contract |
| `LFC` | System Lifecycle |

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

## Change Process

1. Identify affected requirements and domain terms.
2. Record a material architectural decision in `ADR.md`.
3. Update all affected specifications together.
4. Update schemas, code, prompts, tests, and migrations.
5. Verify cross-document consistency and requirement coverage.

