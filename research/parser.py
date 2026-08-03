import json
from hashlib import sha256

from datetime import datetime, timezone

from research.hypothesis import Hypothesis, HypothesisStatus
from research.observation import Observation


def _parse_datetime(value, field_name):
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

        return value

    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO 8601 timestamp") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def _normalize_hypothesis_payload(response):
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("hypothesis response must be valid JSON") from exc

    if not isinstance(response, dict):
        raise ValueError("hypothesis response must be a dict or JSON object")

    if "hypotheses" not in response:
        raise ValueError("hypothesis response must include a 'hypotheses' field")

    hypotheses = response["hypotheses"]

    if not isinstance(hypotheses, list):
        raise ValueError("'hypotheses' must be a list")

    return hypotheses


def parse_observations(
    snapshot,
    response,
    research_cycle_id="unknown-cycle",
    ai_call_id="unknown-ai-call",
    schema_version="1.0",
):
    """
    Convert an AI observation response into
    Observation objects.
    """

    data = json.loads(response)

    observations = []

    snapshot_ref = f"snapshot:{snapshot.symbol}:{snapshot.date}"

    effective_time = str(snapshot.date)

    created_at = datetime.now(timezone.utc).isoformat()

    for item in data["observations"]:

        statement = item["statement"]

        digest = sha256(
            f"{snapshot.symbol}|{effective_time}|{statement}".encode("utf-8")
        ).hexdigest()[:12]

        observation = Observation(

            observation_id=f"obs-{snapshot.symbol}-{digest}",

            symbol_id=snapshot.symbol,

            statement=statement,

            evidence_refs=[snapshot_ref],

            importance=item["importance"],

            effective_time=effective_time,

            created_at=created_at,

            research_cycle_id=research_cycle_id,

            ai_call_id=ai_call_id,

            schema_version=schema_version,

        )

        observations.append(observation)

    return observations


def parse_hypotheses(
    symbol,
    response,
    schema_version="1.0",
):
    """
    Convert validated AI hypothesis data into Hypothesis objects.
    """

    items = _normalize_hypothesis_payload(response)

    hypotheses = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"hypotheses[{index}] must be an object")

        hypothesis_id = item.get("hypothesis_id")
        if not hypothesis_id:
            raise ValueError(f"hypotheses[{index}].hypothesis_id is required")

        item_symbol = item.get("symbol", symbol)
        if not item_symbol:
            raise ValueError(f"hypotheses[{index}].symbol is required")

        title = item.get("title")
        if not title:
            raise ValueError(f"hypotheses[{index}].title is required")

        description = item.get("description")
        if not description:
            raise ValueError(f"hypotheses[{index}].description is required")

        status_value = item.get("status", HypothesisStatus.PROPOSED.value)

        try:
            status = HypothesisStatus(status_value)
        except ValueError as exc:
            raise ValueError(
                f"hypotheses[{index}].status must be one of {[state.value for state in HypothesisStatus]}"
            ) from exc

        confidence = item.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            raise ValueError(f"hypotheses[{index}].confidence must be numeric")

        source_observation_ids = item.get("source_observation_ids", [])
        if not isinstance(source_observation_ids, list):
            raise ValueError(
                f"hypotheses[{index}].source_observation_ids must be a list"
            )

        lineage_hypothesis_ids = item.get("lineage_hypothesis_ids", [])
        if not isinstance(lineage_hypothesis_ids, list):
            raise ValueError(
                f"hypotheses[{index}].lineage_hypothesis_ids must be a list"
            )

        experiment_refs = item.get("experiment_refs", [])
        if not isinstance(experiment_refs, list):
            raise ValueError(f"hypotheses[{index}].experiment_refs must be a list")

        created_at = _parse_datetime(
            item.get("created_at", item.get("created")),
            f"hypotheses[{index}].created_at",
        )
        updated_at = _parse_datetime(
            item.get("updated_at", item.get("updated")),
            f"hypotheses[{index}].updated_at",
        )

        if updated_at < created_at:
            raise ValueError(
                f"hypotheses[{index}].updated_at must not be earlier than created_at"
            )

        hypotheses.append(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                symbol=item_symbol,
                title=title,
                description=description,
                status=status,
                confidence=confidence,
                source_observation_ids=tuple(source_observation_ids),
                parent_hypothesis_id=item.get("parent_hypothesis_id"),
                lineage_hypothesis_ids=tuple(lineage_hypothesis_ids),
                experiment_refs=tuple(experiment_refs),
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    return hypotheses