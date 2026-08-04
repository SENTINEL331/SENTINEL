"""Experiment Request domain model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any


_SUPPORTED_CONDITION_OPERATORS = frozenset({
	"<",
	"<=",
	">",
	">=",
	"==",
	"!=",
})


def _utc_now() -> datetime:
	return datetime.now(timezone.utc)


def _touch_timestamp(timestamp: datetime | None) -> datetime:
	if timestamp is None:
		return _utc_now()

	if timestamp.tzinfo is None or timestamp.utcoffset() is None:
		raise ValueError("timestamps must be timezone-aware")

	return timestamp


def _normalize_machine_readable_entry_conditions(
	machine_readable_entry_conditions: Sequence[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], ...]:
	if machine_readable_entry_conditions is None:
		return ()

	if isinstance(machine_readable_entry_conditions, (str, bytes)) or not isinstance(
		machine_readable_entry_conditions,
		Sequence,
	):
		raise ValueError("machine_readable_entry_conditions must be a sequence of condition mappings")

	if not machine_readable_entry_conditions:
		return ()

	normalized_conditions: list[dict[str, Any]] = []

	for index, condition in enumerate(machine_readable_entry_conditions):
		if not isinstance(condition, Mapping):
			raise ValueError(
				f"machine_readable_entry_conditions[{index}] must be a mapping"
			)

		field = condition.get("field")
		operator = condition.get("operator")

		if not field:
			raise ValueError(
				f"machine_readable_entry_conditions[{index}].field is required"
			)

		if not operator:
			raise ValueError(
				f"machine_readable_entry_conditions[{index}].operator is required"
			)

		if operator not in _SUPPORTED_CONDITION_OPERATORS:
			raise ValueError(
				f"machine_readable_entry_conditions[{index}].operator is unsupported"
			)

		has_value = "value" in condition
		has_other_field = "other_field" in condition

		if has_value == has_other_field:
			raise ValueError(
				"machine_readable_entry_conditions[{}] must include exactly one of "
				"'value' or 'other_field'".format(index)
			)

		normalized_condition = {
			"field": field,
			"operator": operator,
		}

		if has_value:
			if condition["value"] is None:
				raise ValueError(
					f"machine_readable_entry_conditions[{index}].value must not be null"
				)

			normalized_condition["value"] = condition["value"]
		else:
			other_field = condition.get("other_field")
			if not other_field:
				raise ValueError(
					f"machine_readable_entry_conditions[{index}].other_field is required"
				)

			normalized_condition["other_field"] = other_field

		normalized_conditions.append(normalized_condition)

	return tuple(normalized_conditions)


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


class ExperimentRequestExecutionState(str, Enum):
	"""Execution readiness state derived from lifecycle status and fields."""

	EXECUTABLE = "executable"
	NON_EXECUTABLE = "non_executable"
	OBSOLETE = "obsolete"


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
	forward_horizon: int | None = None
	machine_readable_entry_conditions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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

		object.__setattr__(
			self,
			"machine_readable_entry_conditions",
			_normalize_machine_readable_entry_conditions(
				self.machine_readable_entry_conditions
			),
		)

		if self.forward_horizon is not None:
			if isinstance(self.forward_horizon, bool) or not isinstance(
				self.forward_horizon,
				int,
			):
				raise ValueError("forward_horizon must be a positive integer when provided")

			if self.forward_horizon <= 0:
				raise ValueError("forward_horizon must be a positive integer when provided")

		has_machine_readable_conditions = bool(self.machine_readable_entry_conditions)
		has_forward_horizon = self.forward_horizon is not None

		if has_machine_readable_conditions and not has_forward_horizon:
			raise ValueError(
				"forward_horizon is required when machine_readable_entry_conditions are provided"
			)

		if has_forward_horizon and not has_machine_readable_conditions:
			raise ValueError(
				"machine_readable_entry_conditions are required when forward_horizon is provided"
			)

		if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
			raise ValueError("created_at must be timezone-aware")

		if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
			raise ValueError("updated_at must be timezone-aware")

		if self.updated_at < self.created_at:
			raise ValueError("updated_at must not be earlier than created_at")

	@property
	def id(self) -> str:
		return self.experiment_request_id

	@property
	def has_machine_readable_execution_fields(self) -> bool:
		return bool(self.machine_readable_entry_conditions) and self.forward_horizon is not None

	@property
	def execution_state(self) -> ExperimentRequestExecutionState:
		if self.status in {
			ExperimentRequestStatus.REJECTED,
			ExperimentRequestStatus.COMPLETED,
			ExperimentRequestStatus.FAILED,
			ExperimentRequestStatus.CANCELLED,
			ExperimentRequestStatus.TIMED_OUT,
		}:
			return ExperimentRequestExecutionState.OBSOLETE

		if self.status == ExperimentRequestStatus.RUNNING:
			return ExperimentRequestExecutionState.NON_EXECUTABLE

		if self.has_machine_readable_execution_fields:
			return ExperimentRequestExecutionState.EXECUTABLE

		return ExperimentRequestExecutionState.NON_EXECUTABLE

	@property
	def is_executable(self) -> bool:
		return self.execution_state == ExperimentRequestExecutionState.EXECUTABLE

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
