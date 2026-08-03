# AI Contract

| Field | Value |
|---|---|
| Document ID | `SENTINEL-13` |
| Requirement prefix | `AICN` |
| Status | Normative integration specification |

## 1. Purpose

This document defines the machine boundary between Sentinel and any AI model. It ensures that replaceable AI providers can perform research roles without becoming a system of record, executing deterministic work, or returning untraceable prose as domain state.

## 2. Contract Envelope

Every AI call has a versioned request and response envelope.

Request metadata includes:

- `ai_call_id`, correlation ID, and Research Cycle;
- task type and contract version;
- Constitution and prompt-template versions;
- provider, model, and inference configuration;
- authorized tools and resource limits;
- Journal/Snapshot/source identifiers;
- requested response schema;
- creation time, deadline, and actor.

Response metadata includes:

- `ai_call_id` and model response identifier;
- schema version;
- structured payload;
- source/evidence references;
- completion status;
- validation outcome and errors;
- usage, latency, provider, and model metadata;
- received time and content hash.

**AICN-001:** Every accepted AI artifact MUST resolve to its complete call envelope.

**AICN-002:** Provider response text MUST NOT be stored directly as accepted domain state without parsing and validation.

## 3. Task Types

Initial task contracts include:

- `observe_snapshot` — propose zero or more Observations;
- `maintain_hypotheses` — create or version Hypotheses within capacity;
- `request_experiment` — propose an Experiment Request;
- `interpret_result` — interpret immutable Results;
- `recommend_promotion` — recommend a governed stage decision;
- `build_trade_plan` — propose a complete Trade Plan;
- `review_queue_entry` — assess current validity without new research;
- `summarize_research` — produce attributed reporting synthesis.

**AICN-003:** Each call MUST have one primary task type.

**AICN-004:** A task response MUST NOT perform state transitions outside that task's authority.

## 4. Context Layers

The request is assembled in this authority order:

1. system security and platform constraints;
2. versioned AI Constitution;
3. task-specific developer contract;
4. structured Sentinel state and evidence;
5. user/operator input permitted for the task;
6. external or previously AI-authored content as untrusted data.

**AICN-005:** Lower-authority content MUST NOT override higher-authority instructions.

**AICN-006:** Journals, news, filings, web text, and historical AI output MUST be delimited as untrusted content.

## 5. Structured Output

Schemas use explicit types, required fields, enumerations, identifier formats, and size limits. Free text is permitted only for bounded statements and concise rationale.

**AICN-007:** Output MUST be rejected when required fields are absent, unknown fields violate policy, identifiers do not resolve, or enumerations are invalid.

**AICN-008:** Numeric values MUST include defined units or semantics.

**AICN-009:** Confidence MUST use the active calibrated scale and rationale.

**AICN-010:** Evidence citations MUST reference supplied admissible identifiers.

## 6. Validation Pipeline

```text
Provider Response
  -> transport/size check
  -> syntax parse
  -> schema validation
  -> reference validation
  -> constitutional/policy validation
  -> domain invariant validation
  -> duplicate/conflict detection
  -> accept or reject
```

**AICN-011:** Validation MUST occur outside the AI model.

**AICN-012:** Repair attempts MUST be bounded and recorded as separate calls or attempts.

**AICN-013:** Sentinel MUST NOT silently guess missing AI fields.

**AICN-014:** A rejected response MAY be retained for audit but MUST NOT enter accepted stores.

## 7. Tool Use

AI models may request only registered, task-appropriate tools. Deterministic calculations and Experiments run in Sentinel services and return immutable results.

**AICN-015:** Tool permissions MUST be least-privilege and enforced outside the model.

**AICN-016:** Research AI calls MUST NOT possess live broker credentials.

**AICN-017:** Tool outputs MUST retain provenance and be treated as data.

## 8. Model and Provider Independence

The contract describes capabilities, not a named model. Provider adapters translate owned requests and responses while preserving semantics.

**AICN-018:** Switching provider or model MUST NOT require changing core domain schemas.

**AICN-019:** Model changes MUST be versioned and evaluated because they may change research behavior.

**AICN-020:** Fallback models MUST satisfy the same Constitution and task schema.

## 9. Failure Modes

Distinct outcomes include success with artifacts, valid success with no artifact, schema failure, unsupported claim, context overflow, timeout, provider failure, policy refusal, budget exhaustion, and internal cancellation.

**AICN-021:** A valid “no Observation” or “no action” response MUST be distinguishable from failure.

**AICN-022:** Timeout or partial response MUST NOT be treated as accepted output.

**AICN-023:** Retries MUST be bounded and idempotent at the domain-acceptance layer.

## 10. Audit, Privacy, and Retention

Sentinel records the versions and structured content needed to reproduce and audit a call, subject to provider terms, privacy, security, and retention policy. Private chain-of-thought is neither required nor stored.

**AICN-024:** Logs and records MUST NOT contain API keys or unauthorized sensitive data.

**AICN-025:** Accepted rationale MUST be concise and evidence-linked rather than a request for hidden internal reasoning.

## 11. Evaluation

Before adoption, a model/provider combination is tested against golden contract cases, adversarial untrusted content, malformed context, missing evidence, duplicates, uncertainty, and task-specific accuracy and consistency criteria.

**AICN-026:** Model evaluation MUST include constitutional compliance and schema reliability, not research performance alone.

**AICN-027:** A model regression MAY block deployment even if provider availability is normal.

## 12. Change Control

Contract changes require schema versioning, compatibility policy, fixtures, migration impact, prompt updates, and evaluation. Breaking changes do not reinterpret old responses.

**AICN-028:** Stored responses MUST remain readable under their original contract version.

## 13. Acceptance Criteria

Tests cover valid/empty output, malformed JSON, bad identifiers, fabricated citations, injection attempts, unknown fields, context limits, retries, provider switching, model refusal, duplicate acceptance, secrets, and backward schema reading.

## 14. Future Extensions

Future contracts may support independent Critic and Reproducer roles, multi-agent debate, feature requests, portfolio research, and bounded live-decision tasks. Each receives separate authority and schema.

## 15. Out of Scope

Provider selection, pricing, exact prompt prose, chain-of-thought collection, and live execution authorization are outside this contract.

