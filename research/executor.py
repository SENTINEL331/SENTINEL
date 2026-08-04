"""Skeleton experiment execution boundary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from market.historical_data_loader import HistoricalDataLoader
from research.basic_backtest_runner import (
    BasicBacktestRunner,
    _parse_time_horizon,
)
from research.experiment import ExperimentRequest
from research.experiment_result import (
    ExperimentResult,
    ExperimentResultStatus,
)
from dataclasses import replace


class ExperimentExecutor:
    """Execution boundary for experiment requests.

    This executor runs basic deterministic backtests when the request is supported.
    """

    def __init__(
        self,
        basic_backtest_runner: BasicBacktestRunner | None = None,
        historical_data_loader: HistoricalDataLoader | None = None,
    ) -> None:
        self._basic_backtest_runner = basic_backtest_runner or BasicBacktestRunner()
        self._historical_data_loader = historical_data_loader or HistoricalDataLoader()

    def _build_base_result(self, request: ExperimentRequest) -> ExperimentResult:
        now = datetime.now(timezone.utc)

        return ExperimentResult(
            experiment_result_id=f"expr-{uuid4().hex[:12]}",
            experiment_request_id=request.experiment_request_id,
            hypothesis_id=request.hypothesis_id,
            symbol=request.symbol,
            test_type=request.test_type,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

    def _build_not_implemented_result(
        self,
        request: ExperimentRequest,
        reason: str,
        summary: str,
    ) -> ExperimentResult:
        now = datetime.now(timezone.utc)

        return ExperimentResult(
            experiment_result_id=f"expr-{uuid4().hex[:12]}",
            experiment_request_id=request.experiment_request_id,
            hypothesis_id=request.hypothesis_id,
            symbol=request.symbol,
            test_type=request.test_type,
            status=ExperimentResultStatus.NOT_IMPLEMENTED,
            started_at=now,
            completed_at=now,
            summary=summary,
            failure_reason=reason,
            created_at=now,
            updated_at=now,
        )

    def _build_failed_result(
        self,
        request: ExperimentRequest,
        summary: str,
        reason: str,
    ) -> ExperimentResult:
        now = datetime.now(timezone.utc)

        return ExperimentResult(
            experiment_result_id=f"expr-{uuid4().hex[:12]}",
            experiment_request_id=request.experiment_request_id,
            hypothesis_id=request.hypothesis_id,
            symbol=request.symbol,
            test_type=request.test_type,
            status=ExperimentResultStatus.FAILED,
            started_at=now,
            completed_at=now,
            summary=summary,
            failure_reason=reason,
            created_at=now,
            updated_at=now,
        )

    def _format_backtest_execution_error(self, exc: Exception) -> tuple[str, str]:
        error_detail = f"basic_backtest_runner failed: {exc.__class__.__name__}: {exc}"
        return (
            f"Basic backtest execution failed in basic_backtest_runner: {exc.__class__.__name__}: {exc}",
            error_detail,
        )

    def _request_support_error(self, request: ExperimentRequest) -> str | None:
        if request.machine_readable_entry_conditions:
            if request.forward_horizon is None:
                return "forward_horizon is required when machine_readable_entry_conditions are provided"

            return None

        try:
            _parse_time_horizon(request.time_horizon)
        except ValueError as exc:
            return str(exc)

        return "machine_readable_entry_conditions are required for deterministic execution"

    def _to_runner_compatible_request(self, request: ExperimentRequest) -> ExperimentRequest:
        if not request.machine_readable_entry_conditions or request.forward_horizon is None:
            return request

        return replace(
            request,
            entry_conditions=json.dumps(list(request.machine_readable_entry_conditions)),
            time_horizon=f"{request.forward_horizon}D",
        )

        return None

    def execute(self, request: ExperimentRequest, feature_data: pd.DataFrame | None = None) -> ExperimentResult:
        """Execute a supported deterministic backtest or return a clear placeholder."""

        support_error = self._request_support_error(request)
        if support_error is not None:
            return self._build_not_implemented_result(
                request,
                reason="unsupported_experiment_request",
                summary=(
                    "Experiment execution is not implemented for this request: "
                    f"{support_error}"
                ),
            )

        try:
            historical_data = (
                feature_data
                if feature_data is not None
                else self._historical_data_loader.load(request.symbol)
            )
        except FileNotFoundError:
            return self._build_not_implemented_result(
                request,
                reason="historical_data_unavailable",
                summary=(
                    "Experiment execution is not implemented because historical data "
                    f"is unavailable for symbol {request.symbol}."
                ),
            )

        if not isinstance(historical_data, pd.DataFrame):
            return self._build_failed_result(
                request,
                summary="Basic backtest execution failed: historical data loader returned invalid data.",
                reason="basic_backtest_execution_failed",
            )

        if historical_data.empty:
            return self._build_not_implemented_result(
                request,
                reason="historical_data_unavailable",
                summary=(
                    "Experiment execution is not implemented because historical data "
                    f"is unavailable for symbol {request.symbol}."
                ),
            )

        try:
            return self._basic_backtest_runner.run(
                self._to_runner_compatible_request(request),
                historical_data,
            )
        except Exception as exc:
            summary, reason = self._format_backtest_execution_error(exc)
            return self._build_failed_result(
                request,
                summary=summary,
                reason=reason,
            )