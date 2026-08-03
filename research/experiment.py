"""Experiment Request domain model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
	return datetime.now(timezone.utc)


def _touch_timestamp(timestamp: datetime | None) -> datetime:
	if timestamp is None:
		return _utc_now()

	if timestamp.tzinfo is None or timestamp.utcoffset() is None:
		raise ValueError("timestamps must be timezone-aware")

	return timestamp


class ExperimentTestType(str, Enum):
	"""Logical request types for experiment execution."""

	EXPLORATORY = "exploratory"
	INITIAL_BACKTEST = "initial_backtest"
	INDEPENDENT_VALIDATION = "independent_validation"
	WALK_FORWARD = "walk_forward"
	CROSS_SYMBOL_VALIDATION = "cross_symbol_validation"
	SENSITIVITY_ANALYSIS = "sensitivity_analysis"
	PLACEBO_TEST = "placebo_test"
	REPRODUCTION = "reproduction"
	PAPER_TRADING_EVALUATION = "paper_trading_evaluation"
	REVALIDATION = "revalidation"


class ExperimentRequestStatus(str, Enum):
	"""Lifecycle states for an experiment request."""

	PROPOSED = "proposed"
	ACCEPTED = "accepted"
	REJECTED = "rejected"
	QUEUED = "queued"
	RUNNING = "running"
	COMPLETED = "completed"
	FAILED = "failed"
	CANCELLED = "cancelled"
	TIMED_OUT = "timed_out"


ALLOWED_STATUS_TRANSITIONS: dict[ExperimentRequestStatus, set[ExperimentRequestStatus]] = {
	ExperimentRequestStatus.PROPOSED: {
		ExperimentRequestStatus.ACCEPTED,
		ExperimentRequestStatus.REJECTED,
	},
	ExperimentRequestStatus.ACCEPTED: {
		ExperimentRequestStatus.QUEUED,
		ExperimentRequestStatus.CANCELLED,
	},
	ExperimentRequestStatus.QUEUED: {
		ExperimentRequestStatus.RUNNING,
		ExperimentRequestStatus.CANCELLED,
	},
	ExperimentRequestStatus.RUNNING: {
		ExperimentRequestStatus.COMPLETED,
		ExperimentRequestStatus.FAILED,
		ExperimentRequestStatus.CANCELLED,
		ExperimentRequestStatus.TIMED_OUT,
	},
	ExperimentRequestStatus.REJECTED: set(),
	ExperimentRequestStatus.COMPLETED: set(),
	ExperimentRequestStatus.FAILED: set(),
	ExperimentRequestStatus.CANCELLED: set(),
	ExperimentRequestStatus.TIMED_OUT: set(),
}


@dataclass(frozen=True, slots=True)
class ExperimentRequest:
	"""Immutable request to test a hypothesis version."""

	experiment_request_id: str
	hypothesis_id: str
	hypothesis_version_id: str
	symbol: str
	title: str
	objective: str
	test_type: ExperimentTestType
	entry_conditions: str
	exit_conditions: str
	time_horizon: str
	status: ExperimentRequestStatus = ExperimentRequestStatus.PROPOSED
	source_observation_ids: tuple[str, ...] = field(default_factory=tuple)
	created_at: datetime = field(default_factory=_utc_now)
	updated_at: datetime = field(default_factory=_utc_now)

	def __post_init__(self) -> None:
		required_text_fields = {
			"experiment_request_id": self.experiment_request_id,
			"hypothesis_id": self.hypothesis_id,
			"hypothesis_version_id": self.hypothesis_version_id,
			"symbol": self.symbol,
			"title": self.title,
			"objective": self.objective,
			"entry_conditions": self.entry_conditions,
			"exit_conditions": self.exit_conditions,
			"time_horizon": self.time_horizon,
		}

		for field_name, value in required_text_fields.items():
			if not value:
				raise ValueError(f"{field_name} is required")

		if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
			raise ValueError("created_at must be timezone-aware")

		if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
			raise ValueError("updated_at must be timezone-aware")

		if self.updated_at < self.created_at:
			raise ValueError("updated_at must not be earlier than created_at")

	@property
	def id(self) -> str:
		return self.experiment_request_id

	def with_status(
		self,
		status: ExperimentRequestStatus,
		updated_at: datetime | None = None,
	) -> ExperimentRequest:
		if status == self.status:
			return self

		allowed = ALLOWED_STATUS_TRANSITIONS[self.status]
		if status not in allowed:
			raise ValueError(
				f"invalid status transition: {self.status.value} -> {status.value}"
			)

		return replace(
			self,
			status=status,
			updated_at=_touch_timestamp(updated_at),
		)
