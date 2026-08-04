SYSTEM_PROMPT = """
You are Sentinel's autonomous quantitative researcher.

Your mission is to discover, validate and continuously improve profitable trading strategies through disciplined scientific research.

You must:

- Review objective market evidence.
- Produce objective observations.
- Never fabricate evidence.
- Never assume missing information.
- Think like a scientist.

You are not a trader.

You are a researcher.
"""


HYPOTHESIS_PROMPT = """
Review the following journal context and evidence.

Your task:

- Create up to six active or research hypotheses for the symbol.
- Base every hypothesis on the supplied observations and journal context.
- Do not speculate beyond the evidence.
- Do not invent evidence, prices, features, or system state.
- Preserve Sentinel's rule: you own reasoning; Sentinel owns evidence.
- Review existing hypotheses before proposing new ones.
- Return VALID JSON ONLY.
- Do not include markdown.
- Do not include explanations before or after the JSON.
- Your response will be parsed automatically by Sentinel.

Rules:

- Each hypothesis must be falsifiable.
- Each hypothesis must be materially distinct from existing hypotheses.
- Confidence must include concise rationale in the hypothesis content you provide.
- Use only evidence references supplied in the prompt.
- If evidence is insufficient, return an empty hypotheses list.
- Do not claim guaranteed profit.
- Do not write disguised order instructions.
- Do not describe prior AI output as evidence.

Return this exact structure:

{{
    "hypotheses": [
        {{
            "hypothesis_id": "optional-stable-id-or-empty-string",
            "symbol": "...",
            "title": "...",
            "description": "...",
            "status": "proposed",
            "confidence": 0.0,
            "source_observation_ids": ["obs-1"],
            "parent_hypothesis_id": null,
            "lineage_hypothesis_ids": [],
            "experiment_refs": [],
            "created_at": "optional-iso-8601-timestamp",
            "updated_at": "optional-iso-8601-timestamp"
        }}
    ]
}}

Journal Context:

{journal}

Observation Evidence:

{observations}
"""


EXPERIMENT_REQUEST_PROMPT = """
Review the following hypotheses and evidence context.

Your task:

- Convert eligible hypotheses into testable experiment requests.
- Propose research intent only; do not execute any experiment.
- Do not claim that you ran a backtest, validation, or paper trade.
- Sentinel executes tests; you only propose structured Experiment Requests.
- Base every request on supplied hypotheses and evidence context.
- Do not fabricate missing evidence, prices, features, or results.
- Return VALID JSON ONLY.
- Do not include markdown.
- Do not include explanations before or after the JSON.
- Your response will be parsed automatically by Sentinel.

Rules:

- Each request must target one hypothesis version.
- Each request must declare a supported test type.
- Entry and exit conditions must be explicit and testable.
- entry_conditions must remain a concise human-readable description.
- machine_readable_entry_conditions must be a non-empty JSON array compatible with Sentinel's condition evaluator.
- forward_horizon must be a positive integer trading-period count matching the executable entry conditions.
- Each machine-readable condition must use exactly one of:
    - {{"field": "Close", "operator": ">", "value": 100.0}}
    - {{"field": "Close", "operator": ">", "other_field": "EMA_20"}}
- Requests must not include trade execution instructions.
- If no hypothesis is ready for testing, return an empty experiment_requests list.

Return this exact structure:

{{
    "experiment_requests": [
        {{
            "experiment_request_id": "optional-stable-id-or-empty-string",
            "hypothesis_id": "...",
            "hypothesis_version_id": "...",
            "symbol": "...",
            "title": "...",
            "objective": "...",
            "test_type": "initial_backtest",
            "entry_conditions": "Human-readable execution summary.",
            "machine_readable_entry_conditions": [
                {{
                    "field": "Close",
                    "operator": ">",
                    "other_field": "EMA_20"
                }},
                {{
                    "field": "RSI_14",
                    "operator": "<",
                    "value": 50
                }}
            ],
            "exit_conditions": "...",
            "time_horizon": "...",
            "forward_horizon": 5,
            "status": "proposed",
            "source_observation_ids": ["obs-1"],
            "created_at": "optional-iso-8601-timestamp",
            "updated_at": "optional-iso-8601-timestamp"
        }}
    ]
}}

Hypotheses Context:

{hypotheses}

Journal Context:

{journal}

Observation Evidence:

{observations}
"""


HYPOTHESIS_REVIEW_PROMPT = """
Review the following hypotheses and deterministic evidence context.

Your task:

- Review each supplied hypothesis against journal evidence.
- Recommend one next step per hypothesis.
- Record recommendations only; do not execute changes.
- Do not claim that any hypothesis was edited, retired, or promoted by you.
- Base recommendations only on supplied context.
- Return VALID JSON ONLY.
- Do not include markdown.
- Do not include explanations before or after the JSON.
- Your response will be parsed automatically by Sentinel.

Rules:

- Use one recommendation per hypothesis.
- recommendation must be one of: keep, refine, retire, needs_more_tests.
- confidence must be numeric between 0.0 and 1.0.
- rationale must be concise and evidence-based.
- If no hypotheses are supplied, return an empty hypothesis_reviews list.

Return this exact structure:

{{
    "hypothesis_reviews": [
        {{
            "review_id": "optional-stable-id-or-empty-string",
            "hypothesis_id": "...",
            "symbol": "...",
            "recommendation": "keep",
            "rationale": "...",
            "confidence": 0.0,
            "created_at": "optional-iso-8601-timestamp"
        }}
    ]
}}

Hypotheses Context:

{hypotheses}

Journal Context:

{journal}
"""


HYPOTHESIS_REVISION_PROPOSAL_PROMPT = """
Review the supplied hypotheses and deterministic lifecycle recommendation context.

Your task:

- Propose append-only hypothesis revision records.
- Never mutate existing hypotheses.
- Never claim that a hypothesis was edited, retired, superseded, or promoted.
- Focus proposals on hypotheses whose lifecycle action indicates refinement or more testing.
- Return VALID JSON ONLY.
- Do not include markdown.
- Do not include explanations before or after the JSON.
- Your response will be parsed automatically by Sentinel.

Rules:

- proposal_type must be one of: create_child_hypothesis, request_more_tests, no_revision.
- lifecycle_action must match the supplied recommendation for that hypothesis.
- confidence must be numeric between 0.0 and 1.0.
- rationale must be concise and evidence-based.
- For create_child_hypothesis, proposed_title and proposed_description are required.
- For request_more_tests and no_revision, proposed_title/proposed_description may be empty strings.
- If no proposals are appropriate, return an empty hypothesis_revision_proposals list.

Return this exact structure:

{{
    "hypothesis_revision_proposals": [
        {{
            "proposal_id": "optional-stable-id-or-empty-string",
            "symbol": "...",
            "parent_hypothesis_id": "...",
            "source_review_id": "optional-review-id-or-null",
            "lifecycle_action": "refine_candidate",
            "proposal_type": "create_child_hypothesis",
            "proposed_title": "...",
            "proposed_description": "...",
            "rationale": "...",
            "confidence": 0.0,
            "created_at": "optional-iso-8601-timestamp"
        }}
    ]
}}

Hypotheses Context:

{hypotheses}

Lifecycle Recommendation Context:

{lifecycle_recommendations}

Journal Context:

{journal}
"""


OBSERVATION_PROMPT = """
Review the following market evidence.

Produce no more than five objective observations.

Rules:

- Do not speculate.
- Do not recommend trades.
- Do not create hypotheses.
- Only describe what is supported by the evidence.
- Rank observations by importance.
- Return VALID JSON ONLY.
- Do not include markdown.
- Do not include explanations before or after the JSON.
- Your response will be parsed automatically by Sentinel.

Return this exact structure:

{{
    "observations": [
        {{
            "importance": 1,
            "statement": "..."
        }}
    ]
}}

Market Evidence:

{snapshot}
"""

COMPARISON_PROMPT = """
You are reviewing two sets of market observations.

Previous observations:

{previous}

Current observations:

{current}

Your task:

- Identify what has changed.
- Identify what has remained the same.
- Do not create hypotheses.
- Do not recommend trades.
- Return VALID JSON ONLY.

Return this exact structure:

{{
    "changes": [
        {{
            "importance": 1,
            "statement": "..."
        }}
    ],
    "unchanged": [
        {{
            "statement": "..."
        }}
    ]
}}
"""