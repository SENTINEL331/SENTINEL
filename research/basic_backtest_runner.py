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


def _raise_component_error(component_name: str, exc: Exception) -> None:
    raise ValueError(f"{component_name} failed: {exc}") from exc


def _format_match_date(index_value: Any) -> str:
    timestamp = pd.Timestamp(index_value)

    if (
        timestamp.hour == 0
        and timestamp.minute == 0
        and timestamp.second == 0
        and timestamp.microsecond == 0
        and timestamp.nanosecond == 0
    ):
        return timestamp.date().isoformat()

    return timestamp.isoformat()


def _build_numeric_diagnostics(
    *,
    rows_loaded: int,
    rows_after_cleaning: int,
    matching_setups: int,
    forward_returns_available: int,
    forward_horizon: int,
) -> dict[str, float]:
    forward_returns_missing = matching_setups - forward_returns_available
    return {
        "rows_loaded": float(rows_loaded),
        "rows_after_cleaning": float(rows_after_cleaning),
        "matching_setups": float(matching_setups),
        "forward_returns_available": float(forward_returns_available),
        "forward_returns_missing": float(forward_returns_missing),
        "forward_horizon": float(forward_horizon),
    }


class BasicBacktestRunner:
    """Execute a minimal deterministic backtest over historical feature data."""

    def run(
        self,
        request: ExperimentRequest,
        feature_data: pd.DataFrame,
    ) -> ExperimentResult:
        if not isinstance(feature_data, pd.DataFrame):
            raise ValueError("feature_data must be a pandas DataFrame")

        try:
            entry_conditions = _parse_entry_conditions(request.entry_conditions)
        except ValueError as exc:
            _raise_component_error("entry_condition_parser", exc)

        try:
            horizon = _parse_time_horizon(request.time_horizon)
        except ValueError as exc:
            _raise_component_error("time_horizon_parser", exc)

        rows_loaded = int(feature_data.attrs.get("rows_loaded", len(feature_data.index)))
        rows_after_cleaning = int(
            feature_data.attrs.get("rows_after_cleaning", len(feature_data.index))
        )

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

        try:
            matching_rows = scan_entry_setups(feature_data, entry_conditions)
        except ValueError as exc:
            _raise_component_error("setup_scanner", exc)

        matching_setups = len(matching_rows.index)
        first_match_date = None
        last_match_date = None
        if matching_setups > 0:
            first_match_date = _format_match_date(matching_rows.index.min())
            last_match_date = _format_match_date(matching_rows.index.max())

        base_extra_metrics = _build_numeric_diagnostics(
            rows_loaded=rows_loaded,
            rows_after_cleaning=rows_after_cleaning,
            matching_setups=matching_setups,
            forward_returns_available=0,
            forward_horizon=horizon,
        )
        base_diagnostics = {
            "first_match_date": first_match_date,
            "last_match_date": last_match_date,
        }

        if matching_rows.empty:
            return base_result.mark_completed(
                summary="Basic backtest completed with no matching setups.",
                metrics=ExperimentMetrics(
                    trade_count=0,
                    total_return=0.0,
                    extra_metrics=base_extra_metrics,
                ),
                diagnostics=base_diagnostics,
                completed_at=started_at,
                updated_at=started_at,
            )

        try:
            forward_return_results = calculate_forward_returns(
                feature_data,
                list(matching_rows.index),
                horizon,
            )
        except ValueError as exc:
            _raise_component_error("forward_return_calculator", exc)

        available_results = [item for item in forward_return_results if item.is_available]
        available_count = len(available_results)
        result_extra_metrics = _build_numeric_diagnostics(
            rows_loaded=rows_loaded,
            rows_after_cleaning=rows_after_cleaning,
            matching_setups=matching_setups,
            forward_returns_available=available_count,
            forward_horizon=horizon,
        )

        if not available_results:
            return base_result.mark_completed(
                summary=(
                    "Basic backtest completed with matching setups but no available "
                    "forward returns for the configured horizon."
                ),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    total_return=0.0,
                    extra_metrics=result_extra_metrics,
                ),
                diagnostics=base_diagnostics,
                completed_at=started_at,
                updated_at=started_at,
            )

        try:
            metrics_data = calculate_backtest_metrics(available_results)
        except ValueError as exc:
            _raise_component_error("backtest_metrics_calculator", exc)

        merged_extra_metrics = dict(metrics_data.get("extra_metrics", {}))
        merged_extra_metrics.update(result_extra_metrics)
        metrics_data["extra_metrics"] = merged_extra_metrics

        return base_result.mark_completed(
            summary=(
                "Basic backtest completed with "
                f"{len(matching_rows.index)} matching setups and "
                f"{metrics_data['trade_count']} available forward returns."
            ),
            metrics=ExperimentMetrics(**metrics_data),
            diagnostics=base_diagnostics,
            completed_at=started_at,
            updated_at=started_at,
        )