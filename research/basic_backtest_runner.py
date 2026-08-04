"""Basic deterministic backtest runner for ExperimentRequest objects."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import pandas as pd

from research.backtest_metrics_calculator import calculate_backtest_metrics
from research.experiment import ExperimentRequest
from research.experiment_result import ExperimentMetrics, ExperimentResult
from research.forward_return_calculator import calculate_forward_returns
from research.setup_scanner import scan_entry_setups


_TIME_HORIZON_PATTERN = re.compile(r"^\s*(\d+)\s*[Dd]?\s*$")


def _parse_entry_conditions(entry_conditions: Any) -> list[dict[str, Any]]:
    if not isinstance(entry_conditions, str):
        raise ValueError("experiment_request.entry_conditions must be a JSON string")

    try:
        parsed = json.loads(entry_conditions)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "experiment_request.entry_conditions must be valid JSON"
        ) from exc

    if not isinstance(parsed, list) or not parsed:
        raise ValueError(
            "experiment_request.entry_conditions must be a non-empty JSON list"
        )

    if not all(isinstance(item, dict) for item in parsed):
        raise ValueError(
            "experiment_request.entry_conditions must contain only condition mappings"
        )

    return parsed


def _parse_time_horizon(time_horizon: str) -> int:
    if not isinstance(time_horizon, str):
        raise ValueError("experiment_request.time_horizon must be a string")

    match = _TIME_HORIZON_PATTERN.match(time_horizon)
    if match is None:
        raise ValueError(
            "experiment_request.time_horizon must be a positive trading-period string like '5D'"
        )

    horizon = int(match.group(1))
    if horizon <= 0:
        raise ValueError(
            "experiment_request.time_horizon must be a positive trading-period string like '5D'"
        )

    return horizon


def _build_result_id(request: ExperimentRequest, horizon: int, row_count: int) -> str:
    digest = sha256(
        "|".join(
            [
                request.experiment_request_id,
                request.hypothesis_id,
                request.symbol,
                request.test_type.value,
                str(horizon),
                str(row_count),
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"expr-{request.symbol}-{digest}"


class BasicBacktestRunner:
    """Execute a minimal deterministic backtest over historical feature data."""

    def run(
        self,
        request: ExperimentRequest,
        feature_data: pd.DataFrame,
    ) -> ExperimentResult:
        if not isinstance(feature_data, pd.DataFrame):
            raise ValueError("feature_data must be a pandas DataFrame")

        entry_conditions = _parse_entry_conditions(request.entry_conditions)
        horizon = _parse_time_horizon(request.time_horizon)

        started_at = datetime.now(timezone.utc)
        base_result = ExperimentResult(
            experiment_result_id=_build_result_id(request, horizon, len(feature_data.index)),
            experiment_request_id=request.experiment_request_id,
            hypothesis_id=request.hypothesis_id,
            symbol=request.symbol,
            test_type=request.test_type,
            started_at=started_at,
            created_at=started_at,
            updated_at=started_at,
        )

        matching_rows = scan_entry_setups(feature_data, entry_conditions)

        if matching_rows.empty:
            return base_result.mark_completed(
                summary="Basic backtest completed with no matching setups.",
                metrics=ExperimentMetrics(
                    trade_count=0,
                    total_return=0.0,
                ),
                completed_at=started_at,
                updated_at=started_at,
            )

        forward_return_results = calculate_forward_returns(
            feature_data,
            list(matching_rows.index),
            horizon,
        )
        available_results = [item for item in forward_return_results if item.is_available]

        if not available_results:
            return base_result.mark_completed(
                summary=(
                    "Basic backtest completed with matching setups but no available "
                    "forward returns for the configured horizon."
                ),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    total_return=0.0,
                ),
                completed_at=started_at,
                updated_at=started_at,
            )

        metrics_data = calculate_backtest_metrics(available_results)

        return base_result.mark_completed(
            summary=(
                "Basic backtest completed with "
                f"{len(matching_rows.index)} matching setups and "
                f"{metrics_data['trade_count']} available forward returns."
            ),
            metrics=ExperimentMetrics(**metrics_data),
            completed_at=started_at,
            updated_at=started_at,
        )