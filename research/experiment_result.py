"""Experiment Result domain model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from numbers import Real
from types import MappingProxyType
from typing import Mapping

from research.experiment import ExperimentTestType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _touch_timestamp(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        return _utc_now()

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")

    return timestamp


def _validate_numeric(field_name: str, value: Real | None) -> None:
    if value is None:
        return

    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be numeric")


class ExperimentResultStatus(str, Enum):
    """Lifecycle states for an experiment execution result."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    INVALIDATED_BY_PROTOCOL = "invalidated_by_protocol"


@dataclass(frozen=True, slots=True)
class ExperimentMetrics:
    """Structured numeric metrics recorded for an experiment result."""

    total_return: float | None = None
    win_rate: float | None = None
    max_drawdown: float | None = None
    trade_count: int | None = None
    average_return: float | None = None
    average_holding_period: float | None = None
    profit_factor: float | None = None
    annualized_return: float | None = None
    volatility: float | None = None
    sharpe_ratio: float | None = None
    expectancy: float | None = None
    extra_metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_numeric("total_return", self.total_return)
        _validate_numeric("win_rate", self.win_rate)
        _validate_numeric("max_drawdown", self.max_drawdown)
        _validate_numeric("average_return", self.average_return)
        _validate_numeric("average_holding_period", self.average_holding_period)
        _validate_numeric("profit_factor", self.profit_factor)
        _validate_numeric("annualized_return", self.annualized_return)
        _validate_numeric("volatility", self.volatility)
        _validate_numeric("sharpe_ratio", self.sharpe_ratio)
        _validate_numeric("expectancy", self.expectancy)

        if self.trade_count is not None and (
            isinstance(self.trade_count, bool) or not isinstance(self.trade_count, int)
        ):
            raise ValueError("trade_count must be an integer")

        normalized: dict[str, float] = {}
        for metric_name, metric_value in dict(self.extra_metrics).items():
            if not metric_name:
                raise ValueError("extra metric names must be non-empty")

            if isinstance(metric_value, bool) or not isinstance(metric_value, Real):
                raise ValueError(f"extra_metrics.{metric_name} must be numeric")

            normalized[metric_name] = float(metric_value)

        object.__setattr__(
            self,
            "extra_metrics",
            MappingProxyType(normalized),
        )


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Immutable result artifact for one experiment request execution."""

    experiment_result_id: str
    experiment_request_id: str
    hypothesis_id: str
    symbol: str
    test_type: ExperimentTestType
    status: ExperimentResultStatus = ExperimentResultStatus.RUNNING
    started_at: datetime = field(default_factory=_utc_now)
    completed_at: datetime | None = None
    metrics: ExperimentMetrics = field(default_factory=ExperimentMetrics)
    summary: str = ""
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        required_text_fields = {
            "experiment_result_id": self.experiment_result_id,
            "experiment_request_id": self.experiment_request_id,
            "hypothesis_id": self.hypothesis_id,
            "symbol": self.symbol,
        }

        for field_name, value in required_text_fields.items():
            if not value:
                raise ValueError(f"{field_name} is required")

        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")

        if self.completed_at is not None and (
            self.completed_at.tzinfo is None or self.completed_at.utcoffset() is None
        ):
            raise ValueError("completed_at must be timezone-aware")

        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")

        if self.status == ExperimentResultStatus.COMPLETED:
            if self.completed_at is None:
                raise ValueError("completed_at is required when status is completed")

        if self.status in {
            ExperimentResultStatus.FAILED,
            ExperimentResultStatus.CANCELLED,
            ExperimentResultStatus.TIMED_OUT,
            ExperimentResultStatus.INVALIDATED_BY_PROTOCOL,
        }:
            if not self.failure_reason:
                raise ValueError("failure_reason is required for non-completed terminal statuses")

            if self.completed_at is None:
                raise ValueError("completed_at is required for non-completed terminal statuses")

    @property
    def id(self) -> str:
        return self.experiment_result_id

    def mark_completed(
        self,
        summary: str,
        metrics: ExperimentMetrics,
        completed_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> ExperimentResult:
        completion_time = _touch_timestamp(completed_at)
        touched = _touch_timestamp(updated_at)

        if touched < completion_time:
            touched = completion_time

        return replace(
            self,
            status=ExperimentResultStatus.COMPLETED,
            completed_at=completion_time,
            metrics=metrics,
            summary=summary,
            failure_reason=None,
            updated_at=touched,
        )

    def mark_failed(
        self,
        failure_reason: str,
        completed_at: datetime | None = None,
        updated_at: datetime | None = None,
        status: ExperimentResultStatus = ExperimentResultStatus.FAILED,
    ) -> ExperimentResult:
        if status not in {
            ExperimentResultStatus.FAILED,
            ExperimentResultStatus.CANCELLED,
            ExperimentResultStatus.TIMED_OUT,
            ExperimentResultStatus.INVALIDATED_BY_PROTOCOL,
        }:
            raise ValueError("status must be a terminal failure status")

        if not failure_reason:
            raise ValueError("failure_reason is required")

        completion_time = _touch_timestamp(completed_at)
        touched = _touch_timestamp(updated_at)

        if touched < completion_time:
            touched = completion_time

        return replace(
            self,
            status=status,
            completed_at=completion_time,
            failure_reason=failure_reason,
            updated_at=touched,
        )