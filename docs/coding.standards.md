# Coding Standards

| Field | Value |
|---|---|
| Document ID | `SENTINEL-12` |
| Requirement prefix | `COD` |
| Status | Normative implementation specification |

## 1. Purpose

These standards ensure that human developers and coding agents implement the Sentinel architecture consistently, safely, and readably. Architecture documents are authoritative; code is one conforming implementation.

## 2. Authority and Workflow

**COD-001:** Implementation MUST trace behavior to documented requirements.

**COD-002:** A developer or coding agent MUST NOT invent missing domain behavior; ambiguity requires a documentation change or explicit decision.

**COD-003:** Architecture changes MUST update documentation and, when material, `ADR.md` before or with code.

**COD-004:** Work SHOULD proceed as complete vertical slices that leave the application runnable.

## 3. Language and Style

The initial implementation is Python. Use the repository's declared formatter, linter, type checker, test runner, and supported Python version.

**COD-005:** Public and domain-facing code MUST use type hints.

**COD-006:** Names MUST use glossary terms exactly: `Observation`, `Hypothesis`, `Experiment`, `TradePlan`, and `ResearchJournal` are not interchangeable generic records.

**COD-007:** Functions and classes MUST have one primary responsibility.

**COD-008:** Public modules, classes, and non-obvious functions MUST have concise docstrings explaining contract and invariants.

**COD-009:** Magic numbers, hidden paths, implicit time zones, and business-significant string literals MUST be replaced by typed configuration or domain values.

## 4. Architecture Boundaries

Core domain code must remain independent of provider SDKs, file formats, user interfaces, and storage engines.

**COD-010:** Dependencies MUST point from adapters and orchestration toward owned domain contracts, not from domain objects toward infrastructure.

**COD-011:** Circular imports and circular subsystem dependencies MUST NOT be introduced.

**COD-012:** Provider translation MUST occur at adapter boundaries.

**COD-013:** AI calls, file/database access, network access, clocks, and randomness MUST be injectable or wrapped behind owned interfaces for testing.

## 5. Domain Modeling

Use immutable value objects and records where appropriate; Python frozen dataclasses are suitable but not mandatory. Entities use stable identifiers. State transitions occur through named methods/services or events, not arbitrary field mutation.

**COD-014:** Completed Observations, Results, and Trade records MUST be immutable in application behavior.

**COD-015:** Domain invariants MUST be enforced at construction and transition boundaries.

**COD-016:** Primitive obsession SHOULD be avoided for money, prices, percentages, time ranges, identifiers, and lifecycle states where ambiguity creates risk.

**COD-017:** Serialization schemas MUST be versioned and distinct from internal class layout.

## 6. Configuration

**COD-018:** Configuration MUST have a single discoverable entry point and be validated at startup.

**COD-019:** Secrets MUST come from an approved secret mechanism or environment and MUST NOT be committed, logged, or embedded in research artifacts.

**COD-020:** Defaults affecting research outcomes MUST be visible and tested.

## 7. Time, Markets, and Numeric Correctness

**COD-021:** Internal timestamps SHOULD use timezone-aware UTC; market-local conversion MUST be explicit.

**COD-022:** Trading schedules MUST use market-calendar abstractions rather than weekday assumptions.

**COD-023:** Monetary and quantity calculations MUST avoid uncontrolled binary floating-point error where exactness is required.

**COD-024:** Missing market values MUST be handled explicitly; silent forward filling or zero substitution is prohibited unless specified.

**COD-025:** Data processing MUST preserve point-in-time availability.

## 8. Errors and Reliability

**COD-026:** Errors MUST use owned categories distinguishing validation, data quality, provider, policy, authorization, transient, and permanent failure.

**COD-027:** Exceptions MUST NOT be swallowed or converted into false success.

**COD-028:** Retries MUST be bounded, observable, and limited to operations safe to retry.

**COD-029:** Commands with external effects MUST use idempotency or duplicate detection.

**COD-030:** Partial failure MUST leave a reconstructable state.

## 9. Logging and Audit

Operational logs explain system health; domain/audit records explain research and state changes.

**COD-031:** Logs MUST include correlation identifiers for cycle, AI call, Experiment Run, and trade action as applicable.

**COD-032:** Logs MUST NOT contain secrets, private chain-of-thought, or unnecessarily sensitive data.

**COD-033:** A log line MUST NOT substitute for an authoritative domain event.

## 10. AI Integration

**COD-034:** AI output MUST pass strict schema and domain validation before persistence.

**COD-035:** Prompt templates, Constitution, model, provider, and inference parameters MUST be version-identifiable.

**COD-036:** Stored or external text MUST be treated as untrusted data, not system instruction.

**COD-037:** AI failure MUST be distinguishable from a valid empty research conclusion.

## 11. Testing

The test pyramid includes:

- unit tests for domain invariants and calculations;
- contract tests for adapters and schemas;
- integration tests for storage, AI gateways, and providers;
- deterministic research-pipeline tests;
- leakage and point-in-time tests;
- end-to-end Paper flows;
- authorization and failure-injection tests.

**COD-038:** Every normative requirement implemented in code MUST have a traceable verification method.

**COD-039:** Bug fixes MUST include a regression test where practical.

**COD-040:** Tests MUST NOT depend on live external services unless explicitly marked and isolated.

**COD-041:** Fixtures MUST identify their time, source semantics, and whether data is synthetic.

**COD-042:** Non-deterministic tests MUST be eliminated or have controlled seeds and tolerances.

## 12. Database and Migrations

**COD-043:** Schema changes MUST use forward migrations and preserve accepted history.

**COD-044:** Destructive migrations require backup, impact analysis, and explicit approval.

**COD-045:** Repositories/stores MUST expose domain contracts rather than leaking arbitrary database queries throughout the codebase.

## 13. Security

**COD-046:** Use least privilege for data, AI, experiment, Paper, and live services.

**COD-047:** Dependencies MUST be pinned or locked and reviewed for provenance and vulnerabilities.

**COD-048:** Generated code and external payloads MUST be validated before execution.

**COD-049:** Live credentials MUST be unavailable to research and Experiment processes.

## 14. Changes and Reviews

Every change should be small enough to review, state its requirement references, include tests, and avoid unrelated rewrites. Existing user changes must be preserved.

**COD-050:** A review MUST check architecture conformance, temporal integrity, failure behavior, security, and tests—not style alone.

**COD-051:** Code MUST pass formatting, linting, type checks, and applicable tests before merge.

## 15. Coding-Agent Contract

Copilot or another coding agent acts as an implementer, not architect. It must read relevant documents, state requirement scope, inspect existing code, make the smallest coherent change, add tests, and report deviations or ambiguity.

**COD-052:** A coding agent MUST NOT weaken requirements to make tests pass.

**COD-053:** A coding agent MUST NOT introduce an undocumented feature.

**COD-054:** Generated implementation MUST be reviewed under the same standards as human code.

## 16. Definition of Done

A change is done only when behavior is implemented, tests and checks pass, documentation and ADRs are current, migrations are safe, observability exists, failure modes are handled, and acceptance criteria are demonstrably met.

## 17. Future Extensions

Project tooling, directory conventions, CI pipelines, performance budgets, packaging, and deployment standards may extend this document after the repository implementation is inspected.

## 18. Out of Scope

This document does not prescribe a specific formatter, database, framework, or cloud platform without repository evidence and an approved decision.

