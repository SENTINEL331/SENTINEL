"""Skeleton experiment execution boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from research.basic_backtest_runner import (
    BasicBacktestRunner,
    _parse_entry_conditions,
    _parse_time_horizon,
)
from research.experiment import ExperimentRequest
from research.experiment_result import (
    ExperimentResult,
    ExperimentResultStatus,
)


class ExperimentExecutor:
    """Execution boundary for experiment requests.

    This executor runs basic deterministic backtests when the request is supported.
    """

    def __init__(self, basic_backtest_runner: BasicBacktestRunner | None = None) -> None:
        self._basic_backtest_runner = basic_backtest_runner or BasicBacktestRunner()

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

    def _request_support_error(self, request: ExperimentRequest) -> str | None:
        try:
            _parse_entry_conditions(request.entry_conditions)
        except ValueError as exc:
            return str(exc)

        try:
            _parse_time_horizon(request.time_horizon)
        except ValueError as exc:
            return str(exc)

        return None

    def execute(self, request: ExperimentRequest, feature_data=None) -> ExperimentResult:
        """Execute a supported deterministic backtest or return a clear placeholder."""

        if feature_data is None:
            return self._build_not_implemented_result(
                request,
                reason="historical_feature_data_required",
                summary="Experiment execution is not implemented without historical feature data.",
            )

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
            return self._basic_backtest_runner.run(request, feature_data)
        except Exception as exc:
            return self._build_failed_result(
                request,
                summary=f"Basic backtest execution failed: {exc}",
                reason="basic_backtest_execution_failed",
            )