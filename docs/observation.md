# Observation Specification

| Field | Value |
|---|---|
| Document ID | `SENTINEL-06` |
| Requirement prefix | `OBS` |
| Status | Normative subsystem specification |

## 1. Purpose

An Observation is an immutable, evidence-linked statement authored by the AI Researcher about what can objectively be seen in the supplied market evidence. Observations turn Snapshots into durable research inputs without prematurely becoming hypotheses or trade advice.

## 2. Responsibilities

The Observation subsystem must solicit structured Observations, validate their form and provenance, detect duplication, append accepted records, and expose them to Journal generation.

It does not test strategies, predict returns, change Hypotheses, or authorize trades.

## 3. Ownership

- AI Researcher: authors the statement and importance assessment.
- Sentinel: supplies evidence, validates schema/citations, assigns identity, deduplicates, and stores.
- Observation Store: owns the accepted immutable record.

## 4. Required Fields

| Field | Meaning |
|---|---|
| `observation_id` | Stable unique identifier |
| `symbol_id` | Canonical Instrument |
| `statement` | One objective, self-contained assertion |
| `evidence_refs` | Snapshot/data/feature references supporting it |
| `importance` | Defined ordinal or scored relevance |
| `effective_time` | Market time described |
| `created_at` | Record creation time |
| `research_cycle_id` | Originating cycle |
| `ai_call_id` | Authoring model call |
| `schema_version` | Observation contract version |
| `duplicate_of` | Optional semantic predecessor link |

**OBS-001:** `statement` MUST describe evidence and MUST NOT contain a Trade Plan or unsupported forecast.

**OBS-002:** Every accepted Observation MUST cite at least one admissible evidence record.

**OBS-003:** Evidence references MUST resolve to the effective time described.

**OBS-004:** The statement MUST NOT claim access to unavailable historical or future information.

## 5. Statement Rules

A good Observation is specific and testable against its cited evidence:

> The close was below both the configured 20-period SMA and EMA at the Snapshot time.

An invalid Observation adds interpretation or instruction:

> The stock is bearish and should be sold tomorrow.

**OBS-005:** One Observation SHOULD express one principal fact.

**OBS-006:** Relative claims MUST identify the compared measurement or baseline.

**OBS-007:** Terms such as high, low, unusual, or strong MUST have an explicit comparison or defined classifier.

## 6. Importance

Importance helps Journal selection; it does not measure truth or confidence. Its allowed scale and semantics are configured and versioned.

**OBS-008:** Importance MUST NOT increase an Observation's evidentiary weight by itself.

## 7. Lifecycle

```text
proposed
  -> accepted
  -> accepted_duplicate (linked)
  -> rejected_invalid
  -> rejected_unsupported
```

Accepted content never changes. A later correction is a new Observation linked by `corrects` or `supersedes` metadata.

**OBS-009:** Accepted Observations MUST be append-only.

**OBS-010:** Rejection MUST record a machine-readable reason.

**OBS-011:** A duplicate MUST NOT be counted as independent confirming evidence.

## 8. Creation Process

1. Sentinel builds a Snapshot and current Journal.
2. The Observation task presents the evidence under the AI Constitution.
3. The AI returns the Observation schema only.
4. Sentinel validates types, references, timing, prohibited content, and capacity.
5. Semantic deduplication compares current and prior records.
6. Accepted Observations are appended.
7. A new Journal render may include them.

**OBS-012:** One watched symbol SHOULD receive an Observation review during every eligible Research Cycle, even when the valid result is no new Observation.

**OBS-013:** An empty result MUST be distinguishable from AI failure.

## 9. Storage and Queries

The store must support queries by identifier, Instrument, effective time, cycle, evidence, importance, family, and Hypothesis usage.

**OBS-014:** Historical reads MUST preserve the schema and statement originally accepted.

**OBS-015:** Deleting or correcting source evidence MUST trigger an impact record for dependent Observations.

## 10. Acceptance Criteria

An implementation conforms when it can prove that it rejects unsupported and malformed records, preserves accepted content, resolves citations, prevents duplicates from inflating confirmation, survives restart, and reconstructs every Observation's authoring context.

## 11. Future Extensions

Future versions may add Observation types, structured comparisons, source diversity, contradiction links, independent observers, and calibrated reliability. These must preserve immutability and the separation between observation and hypothesis.

## 12. Out of Scope

Hypothesis formation, confidence updates, strategy logic, Experiment Results, Journal interpretation, and trading decisions are out of scope.

