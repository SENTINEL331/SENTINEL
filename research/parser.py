import json
from hashlib import sha256

from datetime import datetime, timezone

from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
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


def _parse_optional_datetime(value):
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")

        return value

    if not isinstance(value, str):
        raise ValueError("timestamps must be ISO 8601 strings")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("timestamps must be ISO 8601 timestamps") from exc

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


def _normalize_experiment_request_payload(response):
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("experiment request response must be valid JSON") from exc

    if not isinstance(response, dict):
        raise ValueError("experiment request response must be a dict or JSON object")

    if "experiment_requests" not in response:
        raise ValueError(
            "experiment request response must include an 'experiment_requests' field"
        )

    experiment_requests = response["experiment_requests"]

    if not isinstance(experiment_requests, list):
        raise ValueError("'experiment_requests' must be a list")

    return experiment_requests


def parse_experiment_requests(
    symbol,
    response,
):
    """
    Convert validated experiment request data into ExperimentRequest objects.
    """

    items = _normalize_experiment_request_payload(response)

    experiment_requests = []

    seen_request_ids = set()

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"experiment_requests[{index}] must be an object")

        experiment_request_id = item.get("experiment_request_id")

        hypothesis_id = item.get("hypothesis_id")
        if not hypothesis_id:
            raise ValueError(f"experiment_requests[{index}].hypothesis_id is required")

        hypothesis_version_id = item.get("hypothesis_version_id")
        if not hypothesis_version_id:
            raise ValueError(
                f"experiment_requests[{index}].hypothesis_version_id is required"
            )

        item_symbol = item.get("symbol", symbol)
        if not item_symbol:
            raise ValueError(f"experiment_requests[{index}].symbol is required")

        title = item.get("title")
        if not title:
            raise ValueError(f"experiment_requests[{index}].title is required")

        objective = item.get("objective")
        if not objective:
            raise ValueError(f"experiment_requests[{index}].objective is required")

        test_type_value = item.get("test_type")
        if not test_type_value:
            raise ValueError(f"experiment_requests[{index}].test_type is required")

        try:
            test_type = ExperimentTestType(test_type_value)
        except ValueError as exc:
            raise ValueError(
                "experiment_requests[{}].test_type must be one of {}".format(
                    index,
                    [test_type_item.value for test_type_item in ExperimentTestType],
                )
            ) from exc

        entry_conditions = item.get("entry_conditions")
        if not entry_conditions:
            raise ValueError(
                f"experiment_requests[{index}].entry_conditions is required"
            )

        machine_readable_entry_conditions = item.get(
            "machine_readable_entry_conditions",
            (),
        )
        forward_horizon = item.get("forward_horizon")

        if "machine_readable_entry_conditions" in item:
            if not isinstance(machine_readable_entry_conditions, list):
                raise ValueError(
                    f"experiment_requests[{index}].machine_readable_entry_conditions must be a list"
                )

            if not machine_readable_entry_conditions:
                raise ValueError(
                    f"experiment_requests[{index}].machine_readable_entry_conditions must not be empty"
                )

        if "forward_horizon" in item:
            if isinstance(forward_horizon, bool) or not isinstance(forward_horizon, int):
                raise ValueError(
                    f"experiment_requests[{index}].forward_horizon must be an integer"
                )

            if forward_horizon <= 0:
                raise ValueError(
                    f"experiment_requests[{index}].forward_horizon must be positive"
                )

        exit_conditions = item.get("exit_conditions")
        if not exit_conditions:
            raise ValueError(
                f"experiment_requests[{index}].exit_conditions is required"
            )

        time_horizon = item.get("time_horizon")
        if not time_horizon:
            raise ValueError(f"experiment_requests[{index}].time_horizon is required")

        if not experiment_request_id:
            digest = sha256(
                "|".join(
                    [
                        hypothesis_id,
                        hypothesis_version_id,
                        item_symbol,
                        title,
                        objective,
                        test_type_value,
                        entry_conditions,
                        json.dumps(machine_readable_entry_conditions, sort_keys=True),
                        exit_conditions,
                        time_horizon,
                        str(forward_horizon),
                    ]
                ).encode("utf-8")
            ).hexdigest()[:12]
            experiment_request_id = f"expreq-{item_symbol}-{digest}"

        if experiment_request_id in seen_request_ids:
            experiment_request_id = f"{experiment_request_id}-{index}"

        seen_request_ids.add(experiment_request_id)

        status_value = item.get("status", ExperimentRequestStatus.PROPOSED.value)

        try:
            status = ExperimentRequestStatus(status_value)
        except ValueError as exc:
            raise ValueError(
                "experiment_requests[{}].status must be one of {}".format(
                    index,
                    [status_item.value for status_item in ExperimentRequestStatus],
                )
            ) from exc

        source_observation_ids = item.get("source_observation_ids", [])
        if not isinstance(source_observation_ids, list):
            raise ValueError(
                f"experiment_requests[{index}].source_observation_ids must be a list"
            )

        created_at = _parse_optional_datetime(
            item.get("created_at", item.get("created"))
        )
        updated_at = _parse_optional_datetime(
            item.get("updated_at", item.get("updated"))
        )

        if created_at is None and updated_at is None:
            created_at = datetime.now(timezone.utc)
            updated_at = created_at
        elif created_at is None:
            created_at = updated_at
        elif updated_at is None:
            updated_at = created_at

        if updated_at < created_at:
            raise ValueError(
                f"experiment_requests[{index}].updated_at must not be earlier than created_at"
            )

        try:
            experiment_requests.append(
                ExperimentRequest(
                    experiment_request_id=experiment_request_id,
                    hypothesis_id=hypothesis_id,
                    hypothesis_version_id=hypothesis_version_id,
                    symbol=item_symbol,
                    title=title,
                    objective=objective,
                    test_type=test_type,
                    entry_conditions=entry_conditions,
                    machine_readable_entry_conditions=tuple(
                        machine_readable_entry_conditions
                    ),
                    exit_conditions=exit_conditions,
                    time_horizon=time_horizon,
                    forward_horizon=forward_horizon,
                    status=status,
                    source_observation_ids=tuple(source_observation_ids),
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
        except ValueError as exc:
            if str(exc).startswith("machine_readable_entry_conditions") or str(exc).startswith(
                "forward_horizon"
            ):
                raise ValueError(f"experiment_requests[{index}].{exc}") from exc

            raise

    return experiment_requests


def _normalize_hypothesis_review_payload(response):
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("hypothesis review response must be valid JSON") from exc

    if not isinstance(response, dict):
        raise ValueError("hypothesis review response must be a dict or JSON object")

    if "hypothesis_reviews" not in response:
        raise ValueError(
            "hypothesis review response must include a 'hypothesis_reviews' field"
        )

    hypothesis_reviews = response["hypothesis_reviews"]

    if not isinstance(hypothesis_reviews, list):
        raise ValueError("'hypothesis_reviews' must be a list")

    return hypothesis_reviews


def parse_hypothesis_reviews(symbol, response):
    """Convert validated hypothesis review data into HypothesisReview objects."""

    items = _normalize_hypothesis_review_payload(response)

    hypothesis_reviews = []
    seen_review_ids = set()

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"hypothesis_reviews[{index}] must be an object")

        hypothesis_id = item.get("hypothesis_id")
        if not hypothesis_id:
            raise ValueError(f"hypothesis_reviews[{index}].hypothesis_id is required")

        item_symbol = item.get("symbol", symbol)
        if not item_symbol:
            raise ValueError(f"hypothesis_reviews[{index}].symbol is required")

        recommendation_value = item.get("recommendation")
        if not recommendation_value:
            raise ValueError(f"hypothesis_reviews[{index}].recommendation is required")

        try:
            recommendation = HypothesisReviewRecommendation(recommendation_value)
        except ValueError as exc:
            raise ValueError(
                "hypothesis_reviews[{}].recommendation must be one of {}".format(
                    index,
                    [option.value for option in HypothesisReviewRecommendation],
                )
            ) from exc

        rationale = item.get("rationale")
        if not rationale:
            raise ValueError(f"hypothesis_reviews[{index}].rationale is required")

        confidence = item.get("confidence")
        if confidence is None:
            raise ValueError(f"hypothesis_reviews[{index}].confidence is required")

        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError(f"hypothesis_reviews[{index}].confidence must be numeric")

        review_id = item.get("review_id")
        if not review_id:
            digest = sha256(
                "|".join(
                    [
                        hypothesis_id,
                        item_symbol,
                        recommendation.value,
                        rationale,
                        str(confidence),
                    ]
                ).encode("utf-8")
            ).hexdigest()[:12]
            review_id = f"hyprev-{item_symbol}-{digest}"

        if review_id in seen_review_ids:
            review_id = f"{review_id}-{index}"

        seen_review_ids.add(review_id)

        created_at = _parse_optional_datetime(item.get("created_at", item.get("created")))
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        hypothesis_reviews.append(
            HypothesisReview(
                review_id=review_id,
                hypothesis_id=hypothesis_id,
                symbol=item_symbol,
                recommendation=recommendation,
                rationale=rationale,
                confidence=float(confidence),
                created_at=created_at,
            )
        )

    return hypothesis_reviews