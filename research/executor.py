"""Skeleton experiment execution boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from research.experiment import ExperimentRequest
from research.experiment_result import (
    ExperimentResult,
    ExperimentResultStatus,
)


class ExperimentExecutor:
    """Execution boundary for experiment requests.

    This skeleton intentionally does not execute backtests or trading logic yet.
    """

    def execute(self, request: ExperimentRequest) -> ExperimentResult:
        """Return a placeholder result until execution logic is implemented."""

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
            summary="Experiment execution is not implemented.",
            failure_reason="execution_not_implemented",
            created_at=now,
            updated_at=now,
        )