# Research Journal Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-07` |
| Requirement prefix | `JRN` |
| Status | Normative subsystem specification |

## 1. Purpose

The Research Journal is the canonical context interface between Sentinel's permanent stores and the AI Researcher. It answers: “What does the Researcher need to understand for this symbol and cycle?”

The Journal is generated. It is not a manually edited notebook and is not a source-of-truth database.

## 2. Responsibilities

The Journal builder must:

- reconstruct context from authoritative stores;
- preserve links to every included artifact;
- select relevant recent and historically important material;
- expose active research, contrary evidence, failures, and open work;
- fit the active AI Contract's context limits without silently distorting state;
- produce a human-readable and machine-usable rendering.

## 3. Ownership

- Stores own research truth and history.
- Sentinel owns Journal construction and selection policy.
- The AI Researcher consumes the Journal and may propose new artifacts.
- No actor edits a Journal to change domain state.

**JRN-001:** A Journal MUST be reproducible from referenced stores, configuration, and builder version.

**JRN-002:** A Journal render MUST NOT become the only copy of research information.

## 4. Required Sections

Every symbol Journal must support these sections, showing `None` or an equivalent explicit empty state where applicable:

1. Identity: symbol, effective market date, render time, cycle, and versions.
2. Mission: active Research Objective and constraints.
3. Current Evidence: current Snapshot reference and quality warnings.
4. Current Understanding: attributed synthesis, clearly distinguished from evidence.
5. Recent and Important Observations.
6. Active Hypotheses, capacity usage, confidence, and competing relationships.
7. Active and Recently Completed Experiments.
8. Independent Validation and Promotion Status.
9. Paper Trades and optional live monitoring state.
10. Contradictions, failures, and unresolved limitations.
11. Open Questions.
12. Pending and Recommended Next Actions.

**JRN-003:** Every included item MUST retain its stable identifier.

**JRN-004:** The Journal MUST label derived synthesis separately from immutable records.

## 5. Generation

```text
Cycle + Objective + Snapshot
          |
Permanent Domain Stores
          |
Selection and relevance policy
          |
Ordering and context-budget policy
          |
Structured Journal Model
          |
Human / AI rendering
```

**JRN-005:** One Journal MUST be generated for each watched symbol during each eligible Research Cycle.

**JRN-006:** A symbol with no prior research MUST still receive a valid Journal with explicit empty sections.

**JRN-007:** A render MUST record source high-water marks or equivalent version boundaries.

## 6. Selection Policy

The Journal cannot always include the complete history. Selection balances recency, importance, lifecycle relevance, contradiction, unresolved work, and dependency on active Hypotheses.

Mandatory inclusion includes:

- all active Hypotheses and their current versions;
- active Experiments and pending requests;
- active Paper Trades, Trade Plans, and Queue Entries;
- unresolved data-quality or policy warnings;
- material evidence contradicting active research;
- promotion gate status and recent failures;
- records explicitly required by the current task.

**JRN-008:** Context limits MUST NOT silently remove a material contradiction or failure.

**JRN-009:** Omitted history MUST remain discoverable through a referenced summary or retrieval mechanism.

**JRN-010:** Repeated duplicate Observations SHOULD be compressed without being presented as multiple independent confirmations.

## 7. Current Understanding

“Current Understanding” is a synthesis derived from prior accepted research. It may be produced by a deterministic renderer from stored Interpretations or by an AI task under contract. It is context, not evidence.

**JRN-011:** A synthesis MUST identify its source artifacts and authoring method.

**JRN-012:** A synthesis MUST NOT overwrite the underlying records when it changes.

## 8. Integrity and Security

Stored text is data, not instruction. Journal construction must prevent earlier AI-authored content, external news, or provider metadata from altering the active Constitution or task contract.

**JRN-013:** Journal content MUST be delimited and treated as untrusted context by the AI gateway.

**JRN-014:** Secrets, credentials, and unauthorized personal data MUST NOT appear in a Journal.

**JRN-015:** Rendering failures MUST block the affected AI task rather than send ambiguous partial context.

## 9. Caching and Persistence

A rendered Journal may be cached for audit or performance. The cache is a derived artifact identified by a content hash, builder version, source boundaries, and expiration policy.

**JRN-016:** Rebuilding with identical source versions and builder configuration SHOULD produce semantically identical output.

**JRN-017:** Direct edits to cached renders MUST have no effect on domain state.

## 10. Human Presentation

The human rendering should be readable as a scientist's notebook: explicit headings, concise evidence, lifecycle state, and next work. It should not dump raw data unnecessarily or conceal source identifiers needed for audit.

## 11. Acceptance Criteria

Conformance requires tests demonstrating empty-symbol rendering, restart reconstruction, mandatory contradiction inclusion, stable source links, context-budget behavior, prompt-injection isolation, cache non-authority, and deterministic ordering.

## 12. Future Extensions

Future versions may provide portfolio Journals, agent-specific views, interactive evidence retrieval, temporal comparisons, and independent critique sections. These remain generated projections.

## 13. Out of Scope

The Journal does not own Observation creation, Hypothesis lifecycle, Experiment execution, promotion, paper trading, or live execution.

